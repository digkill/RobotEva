"""
Eilik-like face renderer.

Рендерим только: глаза + рот.
Выход: PIL.Image RGB, всегда центрировано.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont


def _get_elements(frame_data: Dict) -> List[Dict]:
    if not frame_data:
        return []
    els = frame_data.get("elements")
    return els if isinstance(els, list) else []


def render_face_frame(frame_data: Dict, size: Tuple[int, int]) -> Image.Image:
    """
    Render Eilik-like eyes & mouth onto a black background.
    Elements expected (relative coords around center):
    - eye_left / eye_right: {x,y, shape: circle|ellipse|line, radius or width/height}
    - mouth: {x,y, shape: arc|line|ellipse, radius or width/height, start/end}
    """
    w, h = int(size[0]), int(size[1])
    img = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = w // 2, h // 2
    base = min(w, h)
    # База координат “под Eilik”: 200 условных единиц по меньшей стороне
    s = base / 200.0

    # Default colors (can be overridden per-element with "color")
    eye_color_default = (255, 170, 0)  # yellow-orange
    mouth_color_default = (255, 255, 255)

    # Optional global offsets injected by DisplayManager (in animation units before scaling).
    offsets = frame_data.get("_face_offsets", {}) if isinstance(frame_data, dict) else {}
    try:
        eye_y_offset = float(offsets.get("eye_y", 0.0)) if isinstance(offsets, dict) else 0.0
    except Exception:
        eye_y_offset = 0.0
    try:
        mouth_y_offset = float(offsets.get("mouth_y", 0.0)) if isinstance(offsets, dict) else 0.0
    except Exception:
        mouth_y_offset = 0.0

    elements = _get_elements(frame_data)
    # фильтруем строго то, что рисуем
    elements = [e for e in elements if e.get("type") in ("eye_left", "eye_right", "mouth", "text")]

    # Фолбэк: крупные глаза+рот, если анимация пустая/не содержит нужного
    if not elements:
        elements = [
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "radius": 40, "start": 20, "end": 160},
        ]

    # Prepare font (for text overlays like "ZzZ")
    def _get_font(px: int):
        px = max(8, int(px))
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", px)
        except Exception:
            try:
                return ImageFont.load_default()
            except Exception:
                return None

    # Draw order: eyes then mouth then text overlays
    for e in elements:
        t = e.get("type")
        x = cx + int(float(e.get("x", 0)) * s)
        y_rel = float(e.get("y", 0))
        if t in ("eye_left", "eye_right"):
            y_rel += eye_y_offset
        elif t == "mouth":
            y_rel += mouth_y_offset
        y = cy + int(y_rel * s)

        if t in ("eye_left", "eye_right"):
            shape = e.get("shape", "ellipse")
            color = tuple(e.get("color", eye_color_default))

            # Eye white
            if shape == "circle":
                r = int(float(e.get("radius", 18)) * s)
                # Render as rounded square "glow" (like the picture)
                rr = max(2, int(r * 0.45))
                draw.rounded_rectangle((x - r, y - r, x + r, y + r), radius=rr, fill=color)

            elif shape == "line":
                width = int(float(e.get("width", 60)) * s)
                lw = max(2, int(6 * s))
                draw.line((x - width // 2, y, x + width // 2, y), fill=color, width=lw)

            else:  # ellipse default (Eilik-like)
                ew = int(float(e.get("width", 70)) * s)
                eh = int(float(e.get("height", 55)) * s)
                # Rounded square eyes (like the picture)
                rrad = max(2, int(min(ew, eh) * 0.25))
                draw.rounded_rectangle(
                    (x - ew // 2, y - eh // 2, x + ew // 2, y + eh // 2),
                    radius=rrad,
                    fill=color,
                )

        elif t == "mouth":
            shape = e.get("shape", "arc")
            color = tuple(e.get("color", mouth_color_default))

            if shape == "line":
                width = int(float(e.get("width", 90)) * s)
                lw = max(2, int(10 * s))
                draw.line((x - width // 2, y, x + width // 2, y), fill=color, width=lw)

            elif shape == "ellipse":
                mw = int(float(e.get("width", 60)) * s)
                mh = int(float(e.get("height", 40)) * s)
                lw = max(2, int(10 * s))
                draw.ellipse((x - mw // 2, y - mh // 2, x + mw // 2, y + mh // 2), outline=color, width=lw)

            else:  # arc
                r = int(float(e.get("radius", 40)) * s)
                lw = max(2, int(12 * s))
                start = float(e.get("start", 200))
                end = float(e.get("end", 340))
                draw.arc((x - r, y - r, x + r, y + r), start=start, end=end, fill=color, width=lw)

        elif t == "text":
            txt = str(e.get("text", "") or "").strip()
            if not txt:
                continue
            # default: soft white/blue
            color = tuple(e.get("color", (220, 220, 255)))
            try:
                size_px = float(e.get("size", 24))
            except Exception:
                size_px = 24.0
            font = _get_font(int(size_px * s))
            if font is None:
                continue

            # Anchor can be: "mm" (center), "lt" (left-top) etc; default center.
            anchor = str(e.get("anchor", "mm") or "mm")
            try:
                draw.text((x, y), txt, fill=color, font=font, anchor=anchor)
            except TypeError:
                # Pillow older without anchor support
                draw.text((x, y), txt, fill=color, font=font)

    return img


