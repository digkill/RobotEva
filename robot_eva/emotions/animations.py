"""
Анимации для дисплея робота (в стиле Eilik)
"""
from typing import List, Dict
import math


# Определение анимаций для разных эмоций
# Координаты относительно центра (0, 0) для масштабирования
ANIMATIONS = {
    "neutral": {
        "frames": 20,
        "loop": True,
        "elements": [
            # Eilik-like: большие глаза + рот
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            # По умолчанию — улыбка
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 40},
        ]
    },
    "happy": {
        "frames": 15,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 40},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 40},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 40},
        ]
    },
    "sad": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -10, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -10, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 65, "shape": "arc", "start": 200, "end": 340, "radius": 40},
        ]
    },
    "excited": {
        "frames": 10,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -25, "shape": "ellipse", "width": 80, "height": 60},
            {"type": "eye_right", "x": 46, "y": -25, "shape": "ellipse", "width": 80, "height": 60},
            {"type": "mouth", "x": 0, "y": 55, "shape": "ellipse", "width": 55, "height": 40},
        ]
    },
    "surprised": {
        "frames": 8,
        "loop": False,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -25, "shape": "ellipse", "width": 80, "height": 65},
            {"type": "eye_right", "x": 46, "y": -25, "shape": "ellipse", "width": 80, "height": 65},
            {"type": "mouth", "x": 0, "y": 55, "shape": "ellipse", "width": 50, "height": 55},
        ]
    },
    "thinking": {
        "frames": 30,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -41, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 41, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 40},
        ]
    },
    "listening": {
        "frames": 25,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -15, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -15, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 55},
        ]
    },
    "sleepy": {
        "frames": 40,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -10, "shape": "line", "width": 70},
            {"type": "eye_right", "x": 46, "y": -10, "shape": "line", "width": 70},
            {"type": "mouth", "x": 0, "y": 65, "shape": "line", "width": 50},
        ]
    },
    "sleep": {
        "frames": 60,
        "loop": True,
        "elements": [
            # closed eyes + calm mouth
            {"type": "eye_left", "x": -46, "y": -10, "shape": "line", "width": 70},
            {"type": "eye_right", "x": 46, "y": -10, "shape": "line", "width": 70},
            # Snore mouth (will "breathe" in get_animation_frame)
            {"type": "mouth", "x": 0, "y": 68, "shape": "ellipse", "width": 34, "height": 10},
            # "ZzZ" overlay (top-right-ish)
            {"type": "text", "text": "ZzZ", "x": 70, "y": -85, "size": 26, "anchor": "mm", "color": (210, 210, 255)},
            # small drifting z near mouth (snore)
            {"type": "text", "text": "z", "x": 35, "y": 40, "size": 18, "anchor": "mm", "color": (180, 180, 230)},
        ],
    },
    "wink": {
        "frames": 18,
        "loop": False,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -20, "shape": "line", "width": 70},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 42},
        ],
    },
    "play": {
        "frames": 22,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -22, "shape": "ellipse", "width": 78, "height": 50},
            {"type": "eye_right", "x": 46, "y": -18, "shape": "ellipse", "width": 68, "height": 58},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 45},
            {"type": "text", "text": "!", "x": 75, "y": -70, "size": 34, "anchor": "mm", "color": (255, 255, 255)},
        ],
    },
    "game": {
        "frames": 24,
        "loop": True,
        "elements": [
            # slightly “focused” eyes
            {"type": "eye_left", "x": -46, "y": -22, "shape": "ellipse", "width": 70, "height": 42},
            {"type": "eye_right", "x": 46, "y": -22, "shape": "ellipse", "width": 70, "height": 42},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 35},
            {"type": "text", "text": "GO", "x": 70, "y": -78, "size": 24, "anchor": "mm", "color": (220, 255, 220)},
        ],
    },
    "love": {
        "frames": 20,
        "loop": True,
        "elements": [
            # Red eyes + heart pupils (text overlays) with pulse
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 74, "height": 46, "color": (255, 60, 80)},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 74, "height": 46, "color": (255, 60, 80)},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 45},
            # Heart pupils inside the eyes
            {"type": "text", "text": "♥", "x": -46, "y": -20, "size": 34, "anchor": "mm", "color": (255, 30, 70)},
            {"type": "text", "text": "♥", "x": 46, "y": -20, "size": 34, "anchor": "mm", "color": (255, 30, 70)},
            # Floating hearts around
            {"type": "text", "text": "♥", "x": -78, "y": -82, "size": 22, "anchor": "mm", "color": (255, 120, 160)},
            {"type": "text", "text": "♥", "x": 78, "y": -78, "size": 20, "anchor": "mm", "color": (255, 140, 180)},
        ],
    },
    "angry": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -22, "shape": "ellipse", "width": 72, "height": 36},
            {"type": "eye_right", "x": 46, "y": -22, "shape": "ellipse", "width": 72, "height": 36},
            {"type": "mouth", "x": 0, "y": 63, "shape": "arc", "start": 200, "end": 340, "radius": 38},
            {"type": "text", "text": "!!", "x": 72, "y": -70, "size": 24, "anchor": "mm", "color": (255, 255, 255)},
        ],
    },
    "confused": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 30},
        ]
    },
    "ahegao": {
        "frames": 22,
        "loop": True,
        "elements": [
            # Pink-ish eyes with X pupils
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 74, "height": 50, "color": (255, 120, 180)},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 74, "height": 50, "color": (255, 120, 180)},
            {"type": "text", "text": "X", "x": -46, "y": -20, "size": 38, "anchor": "mm", "color": (255, 255, 255)},
            {"type": "text", "text": "X", "x": 46, "y": -20, "size": 38, "anchor": "mm", "color": (255, 255, 255)},
            # Open mouth + tongue hint
            {"type": "mouth", "x": 0, "y": 62, "shape": "ellipse", "width": 62, "height": 46},
            {"type": "text", "text": ":P", "x": 0, "y": 70, "size": 26, "anchor": "mm", "color": (255, 120, 160)},
            # Blush
            {"type": "text", "text": "///", "x": -88, "y": 0, "size": 22, "anchor": "mm", "color": (255, 120, 160)},
            {"type": "text", "text": "///", "x": 88, "y": 0, "size": 22, "anchor": "mm", "color": (255, 120, 160)},
        ],
    },
    # ====== TOUCH ANIMATIONS (забавные анимации при касании экрана) ======
    "dizzy": {
        "frames": 20,
        "loop": False,
        "elements": [
            # Кружащиеся глаза (звёздочки)
            {"type": "text", "text": "@", "x": -46, "y": -20, "size": 50, "anchor": "mm", "color": (255, 255, 255)},
            {"type": "text", "text": "@", "x": 46, "y": -20, "size": 50, "anchor": "mm", "color": (255, 255, 255)},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 50},
        ],
    },
    "stars": {
        "frames": 15,
        "loop": False,
        "elements": [
            # Звёздочки в глазах
            {"type": "text", "text": "★", "x": -46, "y": -20, "size": 60, "anchor": "mm", "color": (255, 255, 0)},
            {"type": "text", "text": "★", "x": 46, "y": -20, "size": 60, "anchor": "mm", "color": (255, 255, 0)},
            {"type": "mouth", "x": 0, "y": 55, "shape": "ellipse", "width": 60, "height": 40},
        ],
    },
    "hearts": {
        "frames": 18,
        "loop": False,
        "elements": [
            # Сердечки в глазах
            {"type": "text", "text": "♥", "x": -46, "y": -20, "size": 55, "anchor": "mm", "color": (255, 100, 150)},
            {"type": "text", "text": "♥", "x": 46, "y": -20, "size": 55, "anchor": "mm", "color": (255, 100, 150)},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 45},
        ],
    },
    "silly": {
        "frames": 25,
        "loop": False,
        "elements": [
            # Один глаз закрыт, другой большой, язык наружу
            {"type": "eye_left", "x": -46, "y": -20, "shape": "line", "width": 70},  # Закрыт
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 80, "height": 70},  # Большой
            {"type": "text", "text": ":P", "x": 0, "y": 70, "size": 40, "anchor": "mm", "color": (255, 150, 150)},
        ],
    },
    "crazy": {
        "frames": 20,
        "loop": False,
        "elements": [
            # Спирали в глазах
            {"type": "text", "text": "◉", "x": -46, "y": -20, "size": 60, "anchor": "mm", "color": (255, 255, 255)},
            {"type": "text", "text": "◉", "x": 46, "y": -20, "size": 60, "anchor": "mm", "color": (255, 255, 255)},
            {"type": "mouth", "x": 0, "y": 60, "shape": "arc", "start": 20, "end": 160, "radius": 50},
        ],
    },
    "sparkle": {
        "frames": 12,
        "loop": False,
        "elements": [
            # Сверкающие глаза
            {"type": "text", "text": "✨", "x": -46, "y": -20, "size": 55, "anchor": "mm", "color": (255, 255, 200)},
            {"type": "text", "text": "✨", "x": 46, "y": -20, "size": 55, "anchor": "mm", "color": (255, 255, 200)},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 40},
            {"type": "text", "text": "✨", "x": -80, "y": -40, "size": 30, "anchor": "mm", "color": (255, 255, 200)},
            {"type": "text", "text": "✨", "x": 80, "y": -40, "size": 30, "anchor": "mm", "color": (255, 255, 200)},
        ],
    },
    "laugh": {
        "frames": 18,
        "loop": False,
        "elements": [
            # Закрытые глаза от смеха
            {"type": "eye_left", "x": -46, "y": -15, "shape": "arc", "start": 200, "end": 340, "radius": 35},
            {"type": "eye_right", "x": 46, "y": -15, "shape": "arc", "start": 200, "end": 340, "radius": 35},
            {"type": "mouth", "x": 0, "y": 55, "shape": "ellipse", "width": 70, "height": 50},
            {"type": "text", "text": "HA", "x": -70, "y": 0, "size": 20, "anchor": "mm", "color": (255, 255, 255)},
            {"type": "text", "text": "HA", "x": 70, "y": 0, "size": 20, "anchor": "mm", "color": (255, 255, 255)},
        ],
    },
    "blush": {
        "frames": 22,
        "loop": False,
        "elements": [
            # Застенчивый румянец
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 60, "height": 50},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 60, "height": 50},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 40},
            {"type": "text", "text": "//", "x": -75, "y": 10, "size": 35, "anchor": "mm", "color": (255, 150, 150)},
            {"type": "text", "text": "//", "x": 75, "y": 10, "size": 35, "anchor": "mm", "color": (255, 150, 150)},
        ],
    },
    "surprise_big": {
        "frames": 10,
        "loop": False,
        "elements": [
            # ОГРОМНЫЕ глаза
            {"type": "eye_left", "x": -46, "y": -30, "shape": "ellipse", "width": 90, "height": 80},
            {"type": "eye_right", "x": 46, "y": -30, "shape": "ellipse", "width": 90, "height": 80},
            {"type": "mouth", "x": 0, "y": 60, "shape": "ellipse", "width": 60, "height": 65},
            {"type": "text", "text": "!", "x": 0, "y": -80, "size": 40, "anchor": "mm", "color": (255, 255, 255)},
        ],
    },
    "money": {
        "frames": 20,
        "loop": False,
        "elements": [
            # Денежные знаки в глазах
            {"type": "text", "text": "$", "x": -46, "y": -20, "size": 60, "anchor": "mm", "color": (100, 255, 100)},
            {"type": "text", "text": "$", "x": 46, "y": -20, "size": 60, "anchor": "mm", "color": (100, 255, 100)},
            {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 50},
        ],
    },
}



def get_animation_frame(emotion: str, absolute_frame_idx: int) -> Dict:
    """
    Получить один кадр анимации.

    Важно: моргание считается по absolute_frame_idx, чтобы не зависеть от длины цикла
    и быть стабильным “в 3 раза реже”.
    """
    animation = ANIMATIONS.get(emotion.lower(), ANIMATIONS["neutral"])
    num_frames = int(animation.get("frames", 1)) or 1
    elements = animation.get("elements") or []

    local_idx = int(absolute_frame_idx) % num_frames
    progress = local_idx / num_frames if num_frames > 0 else 0

    frame = {"frame": local_idx, "elements": []}

    for element in elements:
        animated_element = element.copy()
        et = element.get("type")

        if et in ["eye_left", "eye_right"]:
            # pupil tiny drift
            animated_element["pupil_dx"] = math.sin(progress * 2 * math.pi) * 4
            animated_element["pupil_dy"] = math.cos(progress * 2 * math.pi) * 2

        elif et == "mouth":
            # subtle mouth wobble
            animated_element["y"] = element.get("y", 55) + math.sin(progress * 2 * math.pi) * 2
            # Special: snore/breathing effect for sleep
            if emotion.lower() == "sleep" and element.get("shape") == "ellipse":
                base_h = float(element.get("height", 10))
                # open/close between ~6..(base_h+10)
                breathe = (math.sin(progress * 2 * math.pi) + 1.0) / 2.0  # 0..1
                animated_element["height"] = 6 + breathe * (base_h + 10)
            # Special: ahegao mouth pulse
            if emotion.lower() == "ahegao" and element.get("shape") == "ellipse":
                try:
                    base_h = float(element.get("height", 46))
                except Exception:
                    base_h = 46.0
                pulse = (math.sin(progress * 2 * math.pi) + 1.0) / 2.0
                animated_element["height"] = base_h + pulse * 10.0

        elif et == "text":
            # subtle floating for overlays
            amp = 3
            if emotion.lower() == "sleep":
                # make "ZzZ"/"z" drift a bit more while sleeping
                amp = 5
            animated_element["y"] = element.get("y", 0) + math.sin(progress * 2 * math.pi) * amp

            # Special: pulse hearts in LOVE emotion
            if emotion.lower() == "love":
                txt = str(element.get("text", "") or "")
                if "♥" in txt or "<3" in txt:
                    try:
                        base_size = float(element.get("size", 24))
                    except Exception:
                        base_size = 24.0
                    pulse = (math.sin(progress * 2 * math.pi) + 1.0) / 2.0  # 0..1
                    animated_element["size"] = base_size + (pulse * 6.0)

        frame["elements"].append(animated_element)

    return frame


def get_animation_frames(emotion: str) -> List[Dict]:
    """
    Получение кадров анимации для эмоции
    
    Args:
        emotion: Название эмоции
        
    Returns:
        Список кадров анимации
    """
    animation = ANIMATIONS.get(emotion.lower(), ANIMATIONS["neutral"])
    num_frames = int(animation.get("frames", 1)) or 1
    return [get_animation_frame(emotion, i) for i in range(num_frames)]


def get_animation_info(emotion: str) -> Dict:
    """Получение информации об анимации"""
    return ANIMATIONS.get(emotion.lower(), ANIMATIONS["neutral"])

