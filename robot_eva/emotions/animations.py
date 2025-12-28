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
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": 0, "y": 0, "radius": 30},
            {"type": "eye_left", "x": -10, "y": -5, "radius": 5},
            {"type": "eye_right", "x": 10, "y": -5, "radius": 5},
        ]
    },
    "happy": {
        "frames": 15,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": 0, "y": 0, "radius": 30},
            {"type": "eye_left", "x": -10, "y": -5, "radius": 5, "shape": "ellipse", "width": 8, "height": 4},
            {"type": "eye_right", "x": 10, "y": -5, "radius": 5, "shape": "ellipse", "width": 8, "height": 4},
            {"type": "mouth", "x": 0, "y": 10, "shape": "arc", "start": 0, "end": 180, "radius": 15},
        ]
    },
    "sad": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": 0, "y": 5, "radius": 30},  # Опущенная голова
            {"type": "eye_left", "x": -10, "y": 0, "radius": 5},
            {"type": "eye_right", "x": 10, "y": 0, "radius": 5},
            {"type": "mouth", "x": 0, "y": 15, "shape": "arc", "start": 180, "end": 360, "radius": 12},
        ]
    },
    "excited": {
        "frames": 10,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 45},  # Увеличенное тело
            {"type": "head", "x": 0, "y": -5, "radius": 32},  # Поднятая голова
            {"type": "eye_left", "x": -12, "y": -10, "radius": 7},
            {"type": "eye_right", "x": 12, "y": -10, "radius": 7},
            {"type": "mouth", "x": 0, "y": 8, "shape": "ellipse", "width": 20, "height": 15},
        ]
    },
    "surprised": {
        "frames": 8,
        "loop": False,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": 0, "y": -10, "radius": 30},  # Резко поднятая голова
            {"type": "eye_left", "x": -10, "y": -15, "radius": 8, "shape": "circle"},
            {"type": "eye_right", "x": 10, "y": -15, "radius": 8, "shape": "circle"},
            {"type": "mouth", "x": 0, "y": 5, "shape": "ellipse", "width": 12, "height": 18},
        ]
    },
    "thinking": {
        "frames": 30,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": -10, "y": 0, "radius": 30},  # Наклон головы
            {"type": "eye_left", "x": -18, "y": -5, "radius": 4, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "eye_right", "x": -2, "y": -5, "radius": 4, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "mouth", "x": -10, "y": 10, "shape": "line", "width": 15},
        ]
    },
    "listening": {
        "frames": 25,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": 0, "y": 5, "radius": 30},  # Наклон вперед
            {"type": "eye_left", "x": -10, "y": 2, "radius": 6},
            {"type": "eye_right", "x": 10, "y": 2, "radius": 6},
            {"type": "mouth", "x": 0, "y": 15, "shape": "line", "width": 10},
        ]
    },
    "sleepy": {
        "frames": 40,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 45, "radius": 40},
            {"type": "head", "x": 0, "y": 10, "radius": 30},  # Опущенная голова
            {"type": "eye_left", "x": -10, "y": 8, "shape": "line", "width": 8},
            {"type": "eye_right", "x": 10, "y": 8, "shape": "line", "width": 8},
            {"type": "mouth", "x": 0, "y": 18, "shape": "line", "width": 12},
        ]
    },
    "confused": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "body", "x": 0, "y": 40, "radius": 40},
            {"type": "head", "x": 0, "y": 0, "radius": 30},
            {"type": "eye_left", "x": -12, "y": -5, "radius": 5, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "eye_right", "x": 12, "y": -5, "radius": 5, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "mouth", "x": 0, "y": 10, "shape": "line", "width": 8, "curved": True},
        ]
    },
}


def get_animation_frames(emotion: str) -> List[Dict]:
    """
    Получение кадров анимации для эмоции
    
    Args:
        emotion: Название эмоции
        
    Returns:
        Список кадров анимации
    """
    animation = ANIMATIONS.get(emotion.lower(), ANIMATIONS["neutral"])
    frames = []
    
    num_frames = animation["frames"]
    elements = animation["elements"]
    
    for frame_idx in range(num_frames):
        frame = {
            "frame": frame_idx,
            "elements": []
        }
        
        # Анимация элементов с учетом номера кадра
        progress = frame_idx / num_frames if num_frames > 0 else 0
        
        for element in elements:
            animated_element = element.copy()
            
            # Добавление анимации для некоторых элементов
            if element["type"] in ["head", "body"]:
                # Легкое покачивание
                offset_x = math.sin(progress * 2 * math.pi) * 2
                offset_y = math.cos(progress * 2 * math.pi) * 1
                animated_element["x"] = element.get("x", 0) + offset_x
                animated_element["y"] = element.get("y", 0) + offset_y
            
            elif element["type"] in ["eye_left", "eye_right"]:
                # Моргание
                if progress % 0.1 < 0.02:  # Моргание каждые 10% анимации
                    animated_element["radius"] = element.get("radius", 5) * 0.3
                else:
                    animated_element["radius"] = element.get("radius", 5)
            
            frame["elements"].append(animated_element)
        
        frames.append(frame)
    
    return frames


def get_animation_info(emotion: str) -> Dict:
    """Получение информации об анимации"""
    return ANIMATIONS.get(emotion.lower(), ANIMATIONS["neutral"])

