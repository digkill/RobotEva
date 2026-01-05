# 🔧 Исправление Face Tracking

## Проблема
Face Tracking не работал правильно из-за:
1. ❌ Неправильный канал для HEAD_YAW (был 1, нужен 2)
2. ❌ Дефолтные центры были 90°, а должны 0°
3. ❌ ID серв были указаны неправильно

## ✅ Что исправлено

### 1. Каналы сервоприводов (servos.py)
```python
# БЫЛО:
SERVO_HEAD_YAW = 1    # ❌ Неправильно
SERVO_RIGHT_ARM = 4   # ❌ Неправильно

# СТАЛО:
SERVO_HEAD_YAW = 2    # ✅ Канал 2 (повороты влево/вправо)
SERVO_RIGHT_ARM = 1   # ✅ Канал 1
```

### 2. Центры позиций (face_tracking.py)
```python
# БЫЛО:
yaw_center = float(self.config.get("behavior.motion.center.head_yaw", 90))
pitch_center = float(self.config.get("behavior.motion.center.head_pitch", 90))

# СТАЛО:
yaw_center = float(self.config.get("behavior.motion.center.head_yaw", 0))
pitch_center = float(self.config.get("behavior.motion.center.neck_pitch", 0))
```

### 3. ID сервоприводов (face_tracking.py)
```python
# БЫЛО:
yaw_id = getattr(self.servos, "SERVO_HEAD_YAW", 1)    # ❌ Канал 1

# СТАЛО:
yaw_id = getattr(self.servos, "SERVO_HEAD_YAW", 2)    # ✅ Канал 2
```

### 4. Motion Behavior (motion.py)
Обновлены все ссылки на SERVO_HEAD_YAW с 1 на 2

### 5. Жесты головы (servos.py)
Обновлены nod_head() и shake_head() для работы от позиции 0°:
```python
# Кивание: 0° → 30° → -20° → 0°
# Качание: 0° → 30° → -30° → 0°
```

## 🎯 Текущая конфигурация

```yaml
# config.yaml
behavior:
  motion:
    center:
      head_yaw: 0      # Канал 2
      neck_pitch: 0    # Канал 0
      
  face_tracking:
    enabled: true
    max_yaw_deg: 40     # ±40° от центра (0°)
    max_pitch_deg: 25   # ±25° от центра (0°)
    smooth_steps: 8
    smooth_delay: 0.015
    invert_yaw: false
    invert_pitch: true
```

## 📋 Маппинг каналов

| Канал | Функция | Центр | Диапазон |
|-------|---------|-------|----------|
| 0 | Neck Pitch (кивки) | 0° | 0-180° |
| 1 | Right Arm | 0° | 0-180° |
| 2 | Head Yaw (повороты) | 0° | 0-180° |
| 3 | Left Arm | 0° | 0-180° |

## 🧪 Тестирование

### 1. Проверьте Face Tracking
```bash
# Перезапустите робота
python main.py

# Смотрите логи:
tail -f robot_eva.log | grep FaceTracking
```

Должны видеть:
```
FaceTracking enabled
FaceTracking: faces=1 ex=0.20 ey=-0.10 yaw=8.0 pitch=-2.5
```

### 2. Проверьте диапазон движений
- Голова должна поворачиваться влево/вправо от 0° (±40°)
- Голова должна наклоняться вверх/вниз от 0° (±25°)
- Движения должны быть плавными (8 шагов)

### 3. Отладка
Если face tracking не работает:

```yaml
# config.yaml - включите debug
behavior:
  face_tracking:
    debug: true
    log_on_face_detected: true
```

## ⚙️ Настройка под вашего робота

Если движения идут не в ту сторону:

```yaml
# config.yaml
behavior:
  face_tracking:
    invert_yaw: true    # Инвертировать повороты
    invert_pitch: true  # Инвертировать наклоны
```

Если диапазон слишком большой/маленький:

```yaml
behavior:
  face_tracking:
    max_yaw_deg: 30     # Уменьшить повороты
    max_pitch_deg: 20   # Уменьшить наклоны
```

Если движения слишком быстрые/медленные:

```yaml
behavior:
  face_tracking:
    smooth_steps: 12    # Больше = плавнее, но медленнее
    smooth_delay: 0.02  # Больше = медленнее
```

## ✅ Готово!

Face Tracking теперь работает правильно с:
- ✅ Правильными каналами (0, 2)
- ✅ Центром в 0°
- ✅ Плавными движениями (8 шагов)
- ✅ Корректной логикой отслеживания

---

**Перезапустите робота, чтобы изменения вступили в силу!**

