"""
Eilik-like face renderer.

Рендерим только: глаза + рот.
Выход: PIL.Image RGB, всегда центрировано.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from PIL import Image, ImageDraw


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

    # Colors (as requested: yellow-orange eyes)
    eye_color = (255, 170, 0)  # yellow-orange
    mouth_color = (255, 255, 255)

    elements = _get_elements(frame_data)
    # фильтруем строго то, что рисуем
    elements = [e for e in elements if e.get("type") in ("eye_left", "eye_right", "mouth")]

    # Фолбэк: крупные глаза+рот, если анимация пустая/не содержит нужного
    if not elements:
        elements = [
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "radius": 40, "start": 20, "end": 160},
        ]

    # Draw order: eyes then mouth (mouth can overlap)
    for e in elements:
        t = e.get("type")
        x = cx + int(float(e.get("x", 0)) * s)
        y = cy + int(float(e.get("y", 0)) * s)

        if t in ("eye_left", "eye_right"):
            shape = e.get("shape", "ellipse")

            # Eye white
            if shape == "circle":
                r = int(float(e.get("radius", 18)) * s)
                # Render as rounded square "glow" (like the picture)
                rr = max(2, int(r * 0.45))
                draw.rounded_rectangle((x - r, y - r, x + r, y + r), radius=rr, fill=eye_color)

            elif shape == "line":
                width = int(float(e.get("width", 60)) * s)
                lw = max(2, int(6 * s))
                draw.line((x - width // 2, y, x + width // 2, y), fill=eye_color, width=lw)

            else:  # ellipse default (Eilik-like)
                ew = int(float(e.get("width", 70)) * s)
                eh = int(float(e.get("height", 55)) * s)
                # Rounded square eyes (like the picture)
                rrad = max(2, int(min(ew, eh) * 0.25))
                draw.rounded_rectangle(
                    (x - ew // 2, y - eh // 2, x + ew // 2, y + eh // 2),
                    radius=rrad,
                    fill=eye_color,
                )

        elif t == "mouth":
            shape = e.get("shape", "arc")
            color = mouth_color

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

    return img


