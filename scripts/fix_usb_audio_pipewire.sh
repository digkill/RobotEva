#!/usr/bin/env bash
set -euo pipefail

# Forces PipeWire/WirePlumber to route audio to the USB sound card ANALOG output.
# Useful when WirePlumber auto-selects IEC958/S/PDIF route and you get "no sound".
#
# Requirements: wpctl, pw-dump, python3
#
# Usage:
#   ./scripts/fix_usb_audio_pipewire.sh

if ! command -v wpctl >/dev/null 2>&1; then
  echo "ERROR: wpctl not found. Install wireplumber tools (wpctl)." >&2
  exit 1
fi

if ! command -v pw-dump >/dev/null 2>&1; then
  echo "ERROR: pw-dump not found. Install pipewire tools (pw-dump)." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found." >&2
  exit 1
fi

python3 -c '
import json, subprocess, sys

def sh(*args):
    return subprocess.check_output(list(args), text=True)

def run(*args):
    subprocess.run(list(args), check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def dump():
    return json.loads(sh("pw-dump"))

objs = dump()

# Find USB audio device by description (you can tweak this if you have multiple USB cards)
dev = None
for o in objs:
    if o.get("type") != "PipeWire:Interface:Device":
        continue
    props = (o.get("info") or {}).get("props") or {}
    desc = str(props.get("device.description") or "")
    if "USB Audio Device" in desc:
        dev = o
        break

if not dev:
    print("ERROR: PipeWire device with description containing \"USB Audio Device\" not found.", file=sys.stderr)
    sys.exit(2)

dev_id = dev["id"]

# Prefer Analog Stereo Output (EnumProfile index 2 on this card)
run("wpctl", "set-profile", str(dev_id), "2")

# Re-dump after profile change, find the analog sink node id
objs = dump()
sink = None
for o in objs:
    if o.get("type") != "PipeWire:Interface:Node":
        continue
    props = (o.get("info") or {}).get("props") or {}
    if props.get("media.class") != "Audio/Sink":
        continue
    nd = str(props.get("node.description") or "")
    if "USB Audio Device" in nd and "Analog Stereo" in nd:
        sink = o
        break

if not sink:
    print("ERROR: USB Analog Stereo sink node not found after profile switch.", file=sys.stderr)
    sys.exit(3)

sink_id = sink["id"]

# Make it the default sink
run("wpctl", "set-default", str(sink_id))

# Force analog speaker route (EnumRoute index 1 on this card)
run("wpctl", "set-route", str(sink_id), "1")

# Ensure not muted + max volume on default sink
run("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0")
run("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "1.0")

print(f"OK: device_id={dev_id} sink_id={sink_id} -> analog-stereo + analog-output-speaker, volume=1.0")
print("Tip: test with: aplay -D pulse /usr/share/sounds/alsa/Front_Center.wav")
'


