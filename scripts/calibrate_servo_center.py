#!/usr/bin/env python3
"""
Calibrate a servo "straight ahead" center by stepping angles.

This does NOT auto-edit YAML. You pick the best angle and then set it as:
  gpio_mapping.yaml -> servos.<name>.default_angle

Example (neck yaw on your build is servo_id=0):
  python scripts/calibrate_servo_center.py --id 0 --start 50 --end 130 --step 5
"""

import os
import sys
import argparse
import time


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="/home/pi/Projects/RobotEva/config.yaml")
    ap.add_argument("--id", type=int, required=True, help="servo_id to calibrate (MQTT)")
    ap.add_argument("--start", type=float, default=60)
    ap.add_argument("--end", type=float, default=120)
    ap.add_argument("--step", type=float, default=5)
    ap.add_argument("--hold", type=float, default=0.9)
    args = ap.parse_args()

    from robot_eva.core.config import Config

    cfg = Config(args.config)
    mqtt_cfg = cfg.get("hardware.servos.mqtt", {}) or {}
    host = mqtt_cfg.get("host", "localhost")
    port = int(mqtt_cfg.get("port", 1883))
    username = (mqtt_cfg.get("username") or "").strip()
    password = (mqtt_cfg.get("password") or "").strip()
    client_id = (mqtt_cfg.get("client_id") or "eva-servo-calibrate").strip()
    topic_base = (mqtt_cfg.get("topic_base") or "robot_eva/servos").strip()
    topic = f"{topic_base}/set"

    import paho.mqtt.client as mqtt

    client = mqtt.Client(client_id=client_id)
    if username:
        client.username_pw_set(username, password or None)
    client.connect(host, port, keepalive=30)
    client.loop_start()

    print(f"[calibrate] broker={host}:{port} topic={topic}")
    print(f"[calibrate] servo_id={args.id} range {args.start}..{args.end} step={args.step}")
    print("[calibrate] Watch the neck yaw and decide which angle looks STRAIGHT.")
    print("")

    try:
        a = args.start
        while a <= args.end + 1e-9:
            print(f"[calibrate] servo_id={args.id} -> {a:.1f}")
            client.publish(topic, f"{args.id},{a:.1f}")
            time.sleep(args.hold)
            a += args.step
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



