#!/usr/bin/env python3
"""
Servo ID identification helper (MQTT).

Moves servo IDs one by one so you can see what each channel controls.

Topic: <hardware.servos.mqtt.topic_base>/set
Payload: "<servo_id>,<angle>"

Example:
  python scripts/identify_servos.py
  python scripts/identify_servos.py --ids 0,1,2,3 --center 90 --delta 25
"""

import os
import sys
import argparse
import time
from typing import List

# Allow running as a script: `python scripts/identify_servos.py`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def parse_ids(s: str) -> List[int]:
    out: List[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="/home/pi/Projects/RobotEva/config.yaml")
    ap.add_argument("--ids", default="0,1,2,3,4", help="Comma-separated servo ids to test")
    ap.add_argument("--center", type=float, default=90.0)
    ap.add_argument("--delta", type=float, default=25.0, help="How far from center to move")
    ap.add_argument("--hold", type=float, default=0.9, help="Seconds to hold each position")
    ap.add_argument("--pause", type=float, default=0.7, help="Seconds between servos")
    args = ap.parse_args()

    from robot_eva.core.config import Config

    cfg = Config(args.config)
    mqtt_cfg = cfg.get("hardware.servos.mqtt", {}) or {}
    host = mqtt_cfg.get("host", "localhost")
    port = int(mqtt_cfg.get("port", 1883))
    username = (mqtt_cfg.get("username") or "").strip()
    password = (mqtt_cfg.get("password") or "").strip()
    client_id = (mqtt_cfg.get("client_id") or "eva-servo-identify").strip()
    topic_base = (mqtt_cfg.get("topic_base") or "robot_eva/servos").strip()
    topic = f"{topic_base}/set"

    ids = parse_ids(args.ids)
    if not ids:
        raise SystemExit("No servo ids provided.")

    try:
        import paho.mqtt.client as mqtt
    except Exception as e:
        raise SystemExit(f"paho-mqtt not available: {e}")

    client = mqtt.Client(client_id=client_id)
    if username:
        client.username_pw_set(username, password or None)

    print(f"[identify] broker={host}:{port} topic={topic}")
    print("[identify] Watch the robot and write down what moves for each servo_id.")
    print("[identify] Safety: power servos from external 5V/6V + common ground.")
    print("")

    client.connect(host, port, keepalive=30)
    client.loop_start()
    try:
        for sid in ids:
            print(f"[identify] servo_id={sid} -> center ({args.center})")
            client.publish(topic, f"{sid},{args.center:.1f}")
            time.sleep(args.hold)

            a1 = args.center - args.delta
            a2 = args.center + args.delta
            print(f"[identify] servo_id={sid} -> {a1:.1f}")
            client.publish(topic, f"{sid},{a1:.1f}")
            time.sleep(args.hold)

            print(f"[identify] servo_id={sid} -> {a2:.1f}")
            client.publish(topic, f"{sid},{a2:.1f}")
            time.sleep(args.hold)

            print(f"[identify] servo_id={sid} -> center ({args.center})")
            client.publish(topic, f"{sid},{args.center:.1f}")
            time.sleep(args.hold)

            print("")
            time.sleep(args.pause)
    finally:
        try:
            client.loop_stop()
        except Exception:
            pass
        try:
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()


