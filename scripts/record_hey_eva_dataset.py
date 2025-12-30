"""
Record dataset for custom wake word "Hey Eva".

Creates:
  data/wakeword/hey_eva/positive/*.wav  (say: "Hey Eva")
  data/wakeword/hey_eva/negative/*.wav  (random speech/noise, NOT "Hey Eva")

WAV format required by training script:
  - mono
  - 16kHz
  - 16-bit PCM
"""

from __future__ import annotations

import argparse
import os
import time
import wave

from pvrecorder import PvRecorder


def write_wav(path: str, pcm: list[int], sample_rate: int = 16000) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(int(x).to_bytes(2, "little", signed=True) for x in pcm))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/wakeword/hey_eva", help="output dataset root")
    ap.add_argument("--mode", choices=["positive", "negative"], required=True)
    ap.add_argument("--count", type=int, default=50)
    ap.add_argument("--seconds", type=float, default=1.2)
    ap.add_argument("--sample-rate", type=int, default=16000)
    args = ap.parse_args()

    frame_length = int(args.sample_rate * args.seconds)

    recorder = PvRecorder(device_index=-1, frame_length=frame_length)
    recorder.start()
    try:
        for i in range(args.count):
            print()
            if args.mode == "positive":
                print(f"[{i+1}/{args.count}] SAY: 'Hey Eva' ...")
            else:
                print(f"[{i+1}/{args.count}] NEGATIVE: random speech/noise (NOT 'Hey Eva') ...")

            time.sleep(0.2)
            pcm = recorder.read()
            ts = int(time.time() * 1000)
            out_dir = os.path.join(args.out, args.mode)
            out_path = os.path.join(out_dir, f"{args.mode}_{ts}.wav")
            write_wav(out_path, pcm, sample_rate=args.sample_rate)
            print("saved:", out_path)
            time.sleep(0.3)
    finally:
        recorder.stop()
        recorder.delete()


if __name__ == "__main__":
    main()



