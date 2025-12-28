"""
Wake word detection.

Backends:
- OpenWakeWord - offline, no keys (may download models on first run)
"""
import logging
import os
import pickle
from pvrecorder import PvRecorder
import asyncio
import time
from typing import Optional


class WakeWordDetector:
    """Wake word detector (OpenWakeWord only)."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.recorder: Optional[PvRecorder] = None

        # openwakeword
        self.oww_model = None
        self.oww_preprocessor = None
        self.hey_eva_clf = None
        self._consecutive_hits = 0

        self.oww_mode = str(config.get("ai.wake_word.openwakeword.mode", "custom")).strip().lower()
        self.oww_threshold = float(config.get("ai.wake_word.openwakeword.threshold", 0.6))
        self.oww_consecutive_frames = int(config.get("ai.wake_word.openwakeword.consecutive_frames", 3))
        self.oww_debounce_seconds = float(config.get("ai.wake_word.openwakeword.debounce_seconds", 1.2))
        self.oww_frame_length = int(config.get("ai.wake_word.openwakeword.frame_length", 1280))
        self.oww_models = config.get("ai.wake_word.openwakeword.models", ["hey_jarvis"]) or ["hey_jarvis"]
        self.hey_eva_classifier_path = str(
            config.get("ai.wake_word.openwakeword.classifier_path", "/home/pi/Projects/RobotEva/models/openwakeword/hey_eva_classifier.pkl")
        )
        self._last_trigger_ts = 0.0

        self.is_detecting = False
    
    async def initialize(self):
        """Initialize OpenWakeWord backend."""
        await self._initialize_openwakeword()
    
    async def _initialize_openwakeword(self):
        # Lazy import (heavy deps)
        try:
            import numpy as np  # noqa: F401
            import openwakeword
            from openwakeword import Model
            from openwakeword.utils import AudioFeatures
        except Exception as e:
            self.logger.warning(f"OpenWakeWord backend недоступен (нет зависимостей): {e}")
            self.oww_model = None
            self.recorder = None
            return

        try:
            # Map known model names to URLs and download them to local cache (wheel doesn't bundle resources).
            models_map = getattr(openwakeword, "MODELS", {}) or {}
            feature_map = getattr(openwakeword, "FEATURE_MODELS", {}) or {}

            cache_dir = self.config.get("ai.wake_word.openwakeword.cache_dir", "/home/pi/Projects/RobotEva/models/openwakeword")
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except Exception:
                pass

            def _download(url: str, dest: str):
                if os.path.exists(dest):
                    return
                import requests
                r = requests.get(url, stream=True, timeout=60)
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)

            # Ensure required feature models exist for ONNX framework
            # (openwakeword wheel doesn't ship resources/models/*)
            mels_onnx = os.path.join(cache_dir, "melspectrogram.onnx")
            emb_onnx = os.path.join(cache_dir, "embedding_model.onnx")
            try:
                for key, target in (("melspectrogram", mels_onnx), ("embedding", emb_onnx)):
                    info = feature_map.get(key) or {}
                    url = (info.get("download_url") or "").replace(".tflite", ".onnx")
                    if url:
                        _download(url, target)
            except Exception as e:
                raise RuntimeError(f"OpenWakeWord: failed to download feature models: {e}") from e

            # Create a shared feature preprocessor (used by both modes)
            self.oww_preprocessor = AudioFeatures(
                inference_framework="onnx",
                melspec_model_path=mels_onnx,
                embedding_model_path=emb_onnx,
                sr=16000,
            )

            model_paths = []
            for name in self.oww_models:
                # Explicit path
                if isinstance(name, str) and os.path.exists(name):
                    model_paths.append(name)
                    continue

                if isinstance(name, str) and name in models_map:
                    url = models_map[name].get("download_url")
                    if not url:
                        raise RuntimeError(f"OpenWakeWord: no download_url for model '{name}'")
                    # Use ONNX framework on Pi (tflite-runtime wheel not available for Python 3.13)
                    # Release assets provide both .tflite and .onnx.
                    url = url.replace(".tflite", ".onnx")
                    filename = os.path.basename(url)
                    dest = os.path.join(cache_dir, filename)
                    if not os.path.exists(dest):
                        _download(url, dest)
                    model_paths.append(dest)
                    continue

                raise RuntimeError(f"OpenWakeWord: unknown model '{name}'. Use a known name like 'hey_jarvis' or give a path.")

            if self.oww_mode == "custom":
                # Custom "Hey Eva" classifier over AudioFeatures embeddings
                if not os.path.exists(self.hey_eva_classifier_path):
                    self.logger.warning(
                        f'Hey Eva classifier not found: {self.hey_eva_classifier_path}. '
                        'Пока используем pretrained режим (say: "hey jarvis").'
                    )
                    self.oww_mode = "pretrained"
                else:
                    self.hey_eva_clf = pickle.load(open(self.hey_eva_classifier_path, "rb"))

            if self.oww_mode == "pretrained":
                # Pretrained openwakeword model(s) (ONNX)
                self.oww_model = Model(
                    wakeword_models=model_paths,
                    inference_framework="onnx",
                    # Override feature model paths to our cache dir
                    melspec_model_path=mels_onnx,
                    embedding_model_path=emb_onnx,
                    vad_threshold=0,
                )

            # PvRecorder is a solid 16kHz mono source; openwakeword likes multiples of 1280 samples (80ms)
            self.recorder = PvRecorder(device_index=-1, frame_length=self.oww_frame_length)
            self.logger.info("Wake word: OpenWakeWord backend активирован")
        except Exception as e:
            self.logger.warning(f"OpenWakeWord backend не запустился: {e}")
            self.oww_model = None
            self.oww_preprocessor = None
            self.hey_eva_clf = None
            self.recorder = None

    async def detect(self) -> bool:
        """
        Проверка наличия wake word
        
        Returns:
            True если wake word обнаружен
        """
        return await self._detect_openwakeword()

    async def _detect_openwakeword(self) -> bool:
        if not self.recorder:
            return False

        try:
            if not self.recorder.is_recording:
                self.recorder.start()

            pcm = self.recorder.read()  # list[int] int16
            import numpy as np

            x = np.asarray(pcm, dtype=np.int16)
            now = time.time()

            # Custom "Hey Eva" mode: use embeddings classifier
            if self.oww_mode == "custom":
                if not self.oww_preprocessor or not self.hey_eva_clf:
                    return False

                # Update streaming features
                _ = self.oww_preprocessor(x)
                feats = self.oww_preprocessor.get_features(n_feature_frames=16)  # (1,16,D)
                X = feats.reshape((1, -1))
                try:
                    score = float(self.hey_eva_clf.predict_proba(X)[0][-1])
                except Exception:
                    score = 0.0

                if score >= self.oww_threshold:
                    self._consecutive_hits += 1
                else:
                    self._consecutive_hits = 0

                if self._consecutive_hits >= max(1, self.oww_consecutive_frames) and (now - self._last_trigger_ts) >= self.oww_debounce_seconds:
                    self._last_trigger_ts = now
                    self._consecutive_hits = 0
                    self.logger.info(f'Wake word обнаружен: "Hey Eva" score={score:.2f}')
                    return True

                return False

            # Pretrained mode: use openwakeword models
            if not self.oww_model:
                return False

            preds = self.oww_model.predict(x)
            best_score = 0.0
            best_name = None
            if isinstance(preds, dict):
                for k, v in preds.items():
                    try:
                        vv = float(v)
                    except Exception:
                        continue
                    if vv > best_score:
                        best_score = vv
                        best_name = k

            if best_score >= self.oww_threshold and (now - self._last_trigger_ts) >= self.oww_debounce_seconds:
                self._last_trigger_ts = now
                self.logger.info(f"Wake word обнаружен (OpenWakeWord): {best_name} score={best_score:.2f}")
                return True

            return False
        except Exception as e:
            self.logger.warning(f"Ошибка OpenWakeWord detect: {e}")
            return False
    
    async def start_listening(self):
        """Начало непрерывного прослушивания"""
        self.is_detecting = True
        if self.recorder and not self.recorder.is_recording:
            self.recorder.start()
    
    async def stop_listening(self):
        """Остановка прослушивания"""
        self.is_detecting = False
        if self.recorder and self.recorder.is_recording:
            self.recorder.stop()
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.recorder:
            if self.recorder.is_recording:
                self.recorder.stop()
            self.recorder.delete()
        self.recorder = None

        # openwakeword model has no explicit close
        self.oww_model = None
        self.oww_preprocessor = None
        self.hey_eva_clf = None
        
        self.logger.info("Wake word детектор остановлен")

