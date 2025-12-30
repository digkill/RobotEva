"""
Train custom "Hey Eva" wake word classifier using OpenWakeWord AudioFeatures embeddings.

Input:
  data/wakeword/hey_eva/positive/*.wav
  data/wakeword/hey_eva/negative/*.wav

Output:
  models/openwakeword/hey_eva_classifier.pkl
"""

from __future__ import annotations

import argparse
import glob
import os
import pickle

import numpy as np
import scipy.io.wavfile
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import openwakeword
from openwakeword.utils import AudioFeatures


def ensure_feature_models(cache_dir: str) -> tuple[str, str]:
    os.makedirs(cache_dir, exist_ok=True)
    feature_map = getattr(openwakeword, "FEATURE_MODELS", {}) or {}

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

    mels_onnx = os.path.join(cache_dir, "melspectrogram.onnx")
    emb_onnx = os.path.join(cache_dir, "embedding_model.onnx")

    for key, target in (("melspectrogram", mels_onnx), ("embedding", emb_onnx)):
        info = feature_map.get(key) or {}
        url = (info.get("download_url") or "").replace(".tflite", ".onnx")
        if url:
            _download(url, target)

    return mels_onnx, emb_onnx


def extract_features(pre: AudioFeatures, wav_path: str, n_frames: int = 16) -> np.ndarray:
    sr, dat = scipy.io.wavfile.read(wav_path)
    if sr != 16000:
        raise ValueError(f"{wav_path}: expected 16kHz, got {sr}")
    if dat.ndim != 1:
        dat = dat[:, 0]
    dat = dat.astype(np.int16)

    pre.reset()
    pre(dat)
    feats = pre.get_features(n_feature_frames=n_frames)  # (1,n_frames,D)
    return feats.reshape((-1,)).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/wakeword/hey_eva", help="dataset root")
    ap.add_argument("--out", default="models/openwakeword/hey_eva_classifier.pkl")
    ap.add_argument("--cache", default="models/openwakeword")
    ap.add_argument("--n-frames", type=int, default=16)
    args = ap.parse_args()

    pos = sorted(glob.glob(os.path.join(args.data, "positive", "*.wav")))
    neg = sorted(glob.glob(os.path.join(args.data, "negative", "*.wav")))
    if len(pos) < 10 or len(neg) < 10:
        raise SystemExit(f"Need at least 10 positive and 10 negative wavs. Got pos={len(pos)} neg={len(neg)}")

    mels_onnx, emb_onnx = ensure_feature_models(args.cache)
    pre = AudioFeatures(
        inference_framework="onnx",
        melspec_model_path=mels_onnx,
        embedding_model_path=emb_onnx,
        sr=16000,
    )

    X = []
    y = []
    for p in pos:
        X.append(extract_features(pre, p, n_frames=args.n_frames))
        y.append(1)
    for p in neg:
        X.append(extract_features(pre, p, n_frames=args.n_frames))
        y.append(0)

    X = np.stack(X, axis=0)
    y = np.asarray(y)

    clf = make_pipeline(
        StandardScaler(with_mean=True, with_std=True),
        LogisticRegression(max_iter=2000),
    )
    clf.fit(X, y)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as f:
        pickle.dump(clf, f)

    print("saved classifier:", args.out)


if __name__ == "__main__":
    main()



