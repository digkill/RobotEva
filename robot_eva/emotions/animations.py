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
    "confused": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
            {"type": "mouth", "x": 0, "y": 60, "shape": "line", "width": 30},
        ]
    },
}


# Частота моргания: делаем в ~3 раза реже (≈ раз в 2.4 сек при 12.5 FPS).
BLINK_PERIOD_FRAMES = 30
BLINK_DURATION_FRAMES = 2


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

    do_blink = (int(absolute_frame_idx) % BLINK_PERIOD_FRAMES) < BLINK_DURATION_FRAMES

    for element in elements:
        animated_element = element.copy()
        et = element.get("type")

        if et in ["eye_left", "eye_right"]:
            # pupil tiny drift
            animated_element["pupil_dx"] = math.sin(progress * 2 * math.pi) * 4
            animated_element["pupil_dy"] = math.cos(progress * 2 * math.pi) * 2

            # blink: squeeze to a line for a couple of frames (если это не sleepy-форма)
            if do_blink and element.get("shape") != "line":
                animated_element["shape"] = "line"
                animated_element["width"] = element.get("width", 70)

        elif et == "mouth":
            # subtle mouth wobble
            animated_element["y"] = element.get("y", 55) + math.sin(progress * 2 * math.pi) * 2

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

