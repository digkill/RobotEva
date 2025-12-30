"""
Управление аудио (USB микрофон и динамики)
"""
import logging
import asyncio
import pyaudio
import wave
import io
import os
import tempfile
import subprocess
from typing import Optional, Tuple


class AudioManager:
    """Менеджер аудио ввода/вывода"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Настройки аудио
        # NOTE: input/output devices may have different native sample rates.
        # We keep `sample_rate` for input path, and derive output rate separately.
        self.sample_rate = config.get("hardware.audio.sample_rate", 16000)
        self.chunk_size = config.get("hardware.audio.chunk_size", 1024)
        self.channels = config.get("hardware.audio.channels", 1)
        self.format = pyaudio.paInt16

        self.output_sample_rate = None
        # If true: don't keep input device open permanently (prevents conflicts with PvRecorder/OpenWakeWord).
        self.lazy_input = bool(config.get("hardware.audio.lazy_input", False))
        # If true: don't keep output device open permanently (prevents "device busy" and makes restarts safer).
        self.lazy_output = bool(config.get("hardware.audio.lazy_output", False))
        
        # Настройки устройств
        # Can be int index or a device name substring (e.g. "pulse")
        self.input_device_index = config.get("hardware.audio.input_device", None)
        self.output_device_index = config.get("hardware.audio.output_device", None)
        # If true and output is PipeWire/Pulse ("pulse"), prefer aplay -D pulse for better resampling quality.
        self.prefer_aplay_on_pulse = bool(config.get("hardware.audio.prefer_aplay_on_pulse", True))
        self._output_device_name = None
        
        self.audio = None
        self.input_stream = None
        self.output_stream = None
        self._closed = False
    
    async def initialize(self):
        """Инициализация аудио системы"""
        try:
            self.audio = pyaudio.PyAudio()

            # Resolve output_device if it's a string (e.g. "pulse")
            if isinstance(self.output_device_index, str) and self.output_device_index.strip():
                want = self.output_device_index.strip().lower()
                resolved = None
                for i in range(self.audio.get_device_count()):
                    info = self.audio.get_device_info_by_index(i)
                    name = str(info.get("name", "") or "")
                    if int(info.get("maxOutputChannels", 0)) > 0 and want in name.lower():
                        resolved = int(info.get("index", i))
                        self._output_device_name = name
                        self.logger.info(f"Output device resolved by name '{want}': {name} (index {resolved})")
                        break
                self.output_device_index = resolved

            # Resolve input_device if it's a string (e.g. "webcamera")
            if isinstance(self.input_device_index, str) and self.input_device_index.strip():
                want = self.input_device_index.strip().lower()
                resolved = None
                for i in range(self.audio.get_device_count()):
                    info = self.audio.get_device_info_by_index(i)
                    name = str(info.get("name", "") or "")
                    if int(info.get("maxInputChannels", 0)) > 0 and want in name.lower():
                        resolved = int(info.get("index", i))
                        self.logger.info(f"Input device resolved by name '{want}': {name} (index {resolved})")
                        break
                self.input_device_index = resolved
            
            # Поиск USB устройств если не указаны
            if self.input_device_index is None:
                self.input_device_index = self._find_usb_microphone()
            
            if self.output_device_index is None:
                self.output_device_index = self._find_usb_speaker()

            # Логируем default output (если есть)
            try:
                default_out = self.audio.get_default_output_device_info()
                self.logger.info(
                    f"Default output device: {default_out.get('name')} (index {default_out.get('index')})"
                )
            except Exception:
                pass
            
            # Получение поддерживаемых частот дискретизации устройства
            if self.input_device_index is not None:
                device_info = self.audio.get_device_info_by_index(self.input_device_index)
                default_sample_rate = int(device_info.get('defaultSampleRate', self.sample_rate))
                # Используем поддерживаемую частоту
                if default_sample_rate != self.sample_rate:
                    self.logger.info(f"Использование частоты дискретизации устройства: {default_sample_rate} Hz вместо {self.sample_rate} Hz")
                    self.sample_rate = default_sample_rate

            # Determine default output sample rate (do NOT reuse input sample rate blindly)
            try:
                out_info = None
                if self.output_device_index is not None:
                    out_info = self.audio.get_device_info_by_index(self.output_device_index)
                else:
                    out_info = self.audio.get_default_output_device_info()
                if out_info:
                    self.output_sample_rate = int(out_info.get("defaultSampleRate", self.sample_rate))
            except Exception:
                self.output_sample_rate = self.sample_rate
            
            # Input stream: either keep it open, or open only for recording (lazy_input).
            if self.lazy_input:
                self.input_stream = None
                self.logger.info("Audio input: lazy_input enabled (will open mic only during record)")
            else:
                # Открытие входного потока с обработкой ошибок sample rate
                try:
                    self.input_stream = self.audio.open(
                        format=self.format,
                        channels=self.channels,
                        rate=self.sample_rate,
                        input=True,
                        input_device_index=self.input_device_index,
                        frames_per_buffer=self.chunk_size
                    )
                except Exception as e:
                    # Попробуем стандартную частоту
                    self.logger.warning(f"Ошибка открытия входного потока с частотой {self.sample_rate} Hz: {e}")
                    self.sample_rate = 44100  # Стандартная частота
                    self.logger.info(f"Попытка с частотой {self.sample_rate} Hz")
                    self.input_stream = self.audio.open(
                        format=self.format,
                        channels=self.channels,
                        rate=self.sample_rate,
                        input=True,
                        input_device_index=self.input_device_index,
                        frames_per_buffer=self.chunk_size
                    )
            
            if self.lazy_output:
                self.output_stream = None
                self.logger.info("Audio output: lazy_output enabled (will open output only during playback)")
            else:
                try:
                    self.output_stream = self.audio.open(
                        format=self.format,
                        channels=self.channels,
                        rate=int(self.output_sample_rate or self.sample_rate),
                        output=True,
                        output_device_index=self.output_device_index,
                        frames_per_buffer=self.chunk_size
                    )
                except Exception as e:
                    self.logger.warning(f"Ошибка открытия выходного потока: {e}")
                    self.output_stream = None
                    self.logger.warning("Аудио выход не инициализирован (playback будет через fallback, если доступен)")
            
            self.logger.info(
                f"Аудио система инициализирована (вход: {self.input_device_index}, выход: {self.output_device_index}, "
                f"lazy_input={self.lazy_input}, lazy_output={self.lazy_output})"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации аудио: {e}")
            raise
    
    def _find_usb_microphone(self) -> Optional[int]:
        """Поиск USB микрофона"""
        # Prefer webcam mics if present ("WebCamera", "UVC", etc.), otherwise fall back to any USB mic.
        preferred_keywords = ("webcamera", "web cam", "webcam", "uvc", "camera")
        usb_candidates = []
        preferred_candidates = []

        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            name = str(info.get("name", "") or "")
            lname = name.lower()
            if info.get("maxInputChannels", 0) > 0 and ("usb" in lname):
                usb_candidates.append((i, name))
                if any(k in lname for k in preferred_keywords):
                    preferred_candidates.append((i, name))

        chosen = None
        if preferred_candidates:
            chosen = preferred_candidates[0]
        elif usb_candidates:
            chosen = usb_candidates[0]

        if chosen:
            i, name = chosen
            self.logger.info(f"Найден USB микрофон: {name} (индекс {i})")
            return i
        return None
    
    def _find_usb_speaker(self) -> Optional[int]:
        """Поиск USB динамика"""
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0 and 'usb' in info['name'].lower():
                self.logger.info(f"Найден USB динамик: {info['name']} (индекс {i})")
                return i
        return None
    
    async def record_audio(self, duration: float = 5.0) -> bytes:
        """
        Запись аудио
        
        Args:
            duration: Длительность записи в секундах
            
        Returns:
            Аудио данные в формате WAV
        """
        if not self.audio:
            raise RuntimeError("Аудио система не инициализирована")

        # If we don't keep input open, open a temporary stream for the duration of recording.
        temp_stream = None
        stream = self.input_stream
        if stream is None:
            try:
                stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.chunk_size
                )
                temp_stream = stream
            except Exception as e:
                self.logger.warning(f"Ошибка открытия входного потока (rate={self.sample_rate}): {e}")
                # Fallback to common rate
                fallback_rate = 44100
                self.logger.info(f"Попытка с частотой {fallback_rate} Hz")
                stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=fallback_rate,
                    input=True,
                    input_device_index=self.input_device_index,
                    frames_per_buffer=self.chunk_size
                )
                temp_stream = stream
                self.sample_rate = fallback_rate
        
        frames = []
        num_chunks = int(self.sample_rate / self.chunk_size * duration)
        
        try:
            for _ in range(num_chunks):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)
                await asyncio.sleep(0)  # Дать возможность другим задачам выполниться
        finally:
            if temp_stream is not None:
                try:
                    temp_stream.stop_stream()
                    temp_stream.close()
                except Exception:
                    pass
        
        # Сохранение в WAV формат
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        return wav_buffer.getvalue()
    
    async def play_audio(self, audio_data: bytes):
        if self._closed or not self.audio:
            return
        """
        Воспроизведение аудио
        
        Args:
            audio_data: Аудио данные в формате WAV
        """
        # If we keep output open, use it. If lazy_output is enabled, open a temporary stream per playback.
        # If we cannot open output at all, fall back to aplay.
        
        try:
            # If output is PipeWire/Pulse, prefer `aplay -D pulse` to avoid low-quality resampling artifacts.
            # PortAudio + audioop.ratecv can sound "cartoonish/robotic" when converting 24kHz -> 48kHz.
            if self.prefer_aplay_on_pulse:
                try:
                    out_name = (self._output_device_name or "").lower()
                    out_cfg = str(self.config.get("hardware.audio.output_device", "") or "").strip().lower()
                    if out_cfg == "pulse" or "pulse" in out_name:
                        await self._play_audio_aplay(audio_data)
                        return
                except Exception:
                    # If detection fails, continue with PyAudio path.
                    pass

            # Чтение WAV данных и проигрывание с корректными параметрами (иначе будет ускорение/замедление)
            wav_buffer = io.BytesIO(audio_data)
            with wave.open(wav_buffer, 'rb') as wf:
                wf_rate = int(wf.getframerate())
                wf_channels = int(wf.getnchannels())
                wf_width = int(wf.getsampwidth())

                # If current output stream params don't match WAV, reopen a temp stream.
                # (OpenAI TTS WAV is typically 24kHz; our output device may default to 44.1kHz.)
                fmt = self.audio.get_format_from_width(wf_width)

                # Negotiate a supported (rate, channels) pair together.
                # Many USB cards want 48kHz stereo; OpenAI TTS is often 24kHz mono.
                out_rate = wf_rate
                out_channels = wf_channels
                try:
                    rate_try = [wf_rate]
                    for r in (48000, 44100, 32000, 24000, 22050, 16000):
                        if r not in rate_try:
                            rate_try.append(r)
                    # Prefer stereo output to avoid ALSA/PortAudio rejecting mono on some devices.
                    ch_try = [2, 1]

                    found = False
                    for r in rate_try:
                        for ch in ch_try:
                            try:
                                ok = self.audio.is_format_supported(
                                    int(r),
                                    output_device=self.output_device_index,
                                    output_channels=int(ch),
                                    output_format=fmt,
                                )
                                if ok:
                                    out_rate = int(r)
                                    out_channels = int(ch)
                                    found = True
                                    break
                            except Exception:
                                continue
                        if found:
                            break
                except Exception:
                    out_rate = wf_rate
                    out_channels = wf_channels

                use_temp_stream = False
                try:
                    cur_rate = int(self.output_sample_rate or self.sample_rate)
                    cur_ch = int(self.channels)
                    cur_fmt = self.format
                    # Compare to negotiated output params (not raw WAV params).
                    if self.output_stream is None or cur_rate != out_rate or cur_ch != out_channels or cur_fmt != fmt:
                        use_temp_stream = True
                except Exception:
                    use_temp_stream = True

                stream = self.output_stream
                temp_stream = None
                if use_temp_stream:
                    try:
                        temp_stream = self.audio.open(
                            format=fmt,
                            channels=out_channels,
                            rate=out_rate,
                            output=True,
                            output_device_index=self.output_device_index,
                            frames_per_buffer=self.chunk_size
                        )
                    except Exception:
                        # Last-chance retry with very common safe params for USB DACs.
                        # (48kHz stereo)
                        temp_stream = self.audio.open(
                            format=fmt,
                            channels=2,
                            rate=48000,
                            output=True,
                            output_device_index=self.output_device_index,
                            frames_per_buffer=self.chunk_size
                        )
                        out_channels = 2
                        out_rate = 48000
                    stream = temp_stream
                if stream is None:
                    # Should not happen, but just in case.
                    await self._play_audio_aplay(audio_data)
                    return

                try:
                    ratecv_state = None
                    chunk = wf.readframes(self.chunk_size)
                    while chunk:
                        try:
                            import audioop
                            # Channel conversion first
                            if out_channels != wf_channels:
                                if wf_channels == 1 and out_channels == 2:
                                    chunk = audioop.tostereo(chunk, wf_width, 1, 1)
                                elif wf_channels == 2 and out_channels == 1:
                                    chunk = audioop.tomono(chunk, wf_width, 0.5, 0.5)
                            # Then resample if needed (ratecv needs correct channel count)
                            if out_rate != wf_rate:
                                chunk, ratecv_state = audioop.ratecv(
                                    chunk, wf_width, out_channels, wf_rate, out_rate, ratecv_state
                                )
                        except Exception:
                            # If conversion fails, let PortAudio try anyway.
                            pass
                        stream.write(chunk)
                        chunk = wf.readframes(self.chunk_size)
                        await asyncio.sleep(0)
                finally:
                    if temp_stream is not None:
                        try:
                            temp_stream.stop_stream()
                            temp_stream.close()
                        except Exception:
                            pass
        except Exception as e:
            self.logger.warning(f"Ошибка воспроизведения через PyAudio: {e}. Пробуем aplay fallback.")
            await self._play_audio_aplay(audio_data)

    async def _play_audio_aplay(self, audio_data: bytes):
        """Fallback playback via `aplay` (WAV only)."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                tmp_path = f.name
                f.write(audio_data)

            # Non-blocking wait is not needed here; greeting should be synchronous.
            # -q: quiet
            aplay_dev = str(self.config.get("hardware.audio.aplay_device", "") or "").strip()
            cmd = ["aplay", "-q"]
            if aplay_dev:
                cmd += ["-D", aplay_dev]
            cmd.append(tmp_path)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except FileNotFoundError:
            self.logger.warning("aplay не найден (sudo apt install alsa-utils). Аудио не будет проиграно.")
        except Exception as e:
            self.logger.warning(f"Ошибка воспроизведения через aplay: {e}")
        finally:
            try:
                if "tmp_path" in locals() and tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass
    
    async def play_file(self, file_path: str):
        """Воспроизведение аудио файла"""
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        await self.play_audio(audio_data)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        self._closed = True
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        if self.audio:
            self.audio.terminate()
            self.audio = None
        
        self.logger.info("Аудио система остановлена")

