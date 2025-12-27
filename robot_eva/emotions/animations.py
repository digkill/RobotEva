"""
Анимации для дисплея робота (в стиле Eilik)
"""
from typing import List, Dict
import math


# Определение анимаций для разных эмоций
ANIMATIONS = {
    "neutral": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 160, "y": 80, "radius": 30},
            {"type": "eye_left", "x": 150, "y": 75, "radius": 5},
            {"type": "eye_right", "x": 170, "y": 75, "radius": 5},
        ]
    },
    "happy": {
        "frames": 15,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 160, "y": 80, "radius": 30},
            {"type": "eye_left", "x": 150, "y": 75, "radius": 5, "shape": "ellipse", "width": 8, "height": 4},
            {"type": "eye_right", "x": 170, "y": 75, "radius": 5, "shape": "ellipse", "width": 8, "height": 4},
            {"type": "mouth", "x": 160, "y": 90, "shape": "arc", "start": 0, "end": 180, "radius": 15},
        ]
    },
    "sad": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 160, "y": 85, "radius": 30},  # Опущенная голова
            {"type": "eye_left", "x": 150, "y": 80, "radius": 5},
            {"type": "eye_right", "x": 170, "y": 80, "radius": 5},
            {"type": "mouth", "x": 160, "y": 95, "shape": "arc", "start": 180, "end": 360, "radius": 12},
        ]
    },
    "excited": {
        "frames": 10,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 45},  # Увеличенное тело
            {"type": "head", "x": 160, "y": 75, "radius": 32},  # Поднятая голова
            {"type": "eye_left", "x": 148, "y": 70, "radius": 7},
            {"type": "eye_right", "x": 172, "y": 70, "radius": 7},
            {"type": "mouth", "x": 160, "y": 88, "shape": "ellipse", "width": 20, "height": 15},
        ]
    },
    "surprised": {
        "frames": 8,
        "loop": False,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 160, "y": 70, "radius": 30},  # Резко поднятая голова
            {"type": "eye_left", "x": 150, "y": 65, "radius": 8, "shape": "circle"},
            {"type": "eye_right", "x": 170, "y": 65, "radius": 8, "shape": "circle"},
            {"type": "mouth", "x": 160, "y": 85, "shape": "ellipse", "width": 12, "height": 18},
        ]
    },
    "thinking": {
        "frames": 30,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 150, "y": 80, "radius": 30},  # Наклон головы
            {"type": "eye_left", "x": 142, "y": 75, "radius": 4, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "eye_right", "x": 158, "y": 75, "radius": 4, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "mouth", "x": 150, "y": 90, "shape": "line", "width": 15},
        ]
    },
    "listening": {
        "frames": 25,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 160, "y": 85, "radius": 30},  # Наклон вперед
            {"type": "eye_left", "x": 150, "y": 82, "radius": 6},
            {"type": "eye_right", "x": 170, "y": 82, "radius": 6},
            {"type": "mouth", "x": 160, "y": 95, "shape": "line", "width": 10},
        ]
    },
    "sleepy": {
        "frames": 40,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 125, "radius": 40},
            {"type": "head", "x": 160, "y": 90, "radius": 30},  # Опущенная голова
            {"type": "eye_left", "x": 150, "y": 88, "shape": "line", "width": 8},
            {"type": "eye_right", "x": 170, "y": 88, "shape": "line", "width": 8},
            {"type": "mouth", "x": 160, "y": 98, "shape": "line", "width": 12},
        ]
    },
    "confused": {
        "frames": 20,
        "loop": True,
        "elements": [
            {"type": "body", "x": 160, "y": 120, "radius": 40},
            {"type": "head", "x": 160, "y": 80, "radius": 30},
            {"type": "eye_left", "x": 148, "y": 75, "radius": 5, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "eye_right", "x": 172, "y": 75, "radius": 5, "shape": "ellipse", "width": 6, "height": 8},
            {"type": "mouth", "x": 160, "y": 90, "shape": "line", "width": 8, "curved": True},
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
                animated_element["x"] = element["x"] + offset_x
                animated_element["y"] = element["y"] + offset_y
            
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

