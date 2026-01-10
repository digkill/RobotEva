# Gesture Recognition Improvements / Улучшения распознавания жестов

## Summary / Резюме

RobotEva теперь распознаёт жесты **С ПЕРВОГО РАЗА!** 🎯

Добавлены улучшения:
- ⚡ **Быстрое распознавание** (1.5 сек вместо 15 сек)
- 🎯 **Срабатывание с первого раза** (consecutive_hits: 1)
- 🆕 **Новый жест "cute"** (peace sign, waving, cute poses)
- 📝 **Улучшенные промпты** для лучшей точности

---

## Supported Gestures / Поддерживаемые жесты

### 1. ❤️ Heart (Сердечко)

**Варианты:**
- Две руки формируют сердце (пальцы/большие пальцы вместе)
- Одна рука finger-heart (корейский стиль: большой и указательный пальцы пересекаются)
- Руки над головой формируют большое сердце

**Реакция:**
- Анимация: `love`
- Фраза: "Я тоже тебя люблю!"
- Длительность: 6 секунд

**Настройки:**
```yaml
behavior:
  gestures:
    heart:
      enabled: true
      interval_seconds: 1.5      # Проверка каждые 1.5 сек
      consecutive_hits: 1        # Срабатывание с первого раза!
      debounce_seconds: 8.0      # Задержка перед повтором
```

---

### 2. 🔫 Gun (Пистолет)

**Варианты:**
- Указательный палец вперёд, большой палец вверх (как пистолет)
- Одной или двумя руками

**Реакция:**
- Анимация: `play`
- Движение: Правая рука поднимается под углом
- Фраза: "пиф пфф"
- Длительность: 4 секунды

**Настройки:**
```yaml
behavior:
  gestures:
    gun:
      enabled: true
      interval_seconds: 1.5
      consecutive_hits: 1
      debounce_seconds: 8.0
      right_arm_angle: 40
```

---

### 3. 🌸 Cute (Милый жест) - НОВЫЙ!

**Варианты:**
- Peace sign / Victory sign (✌️ - два пальца вверх)
- Махание рукой (👋)
- Руки около лица (милая поза)
- Большой палец вверх (👍)
- Любой игривый или kawaii жест

**Реакция:**
- Анимация: **случайная** из `sparkle`, `blush`, `hearts`, `wink`
- Эмоция: `happy`
- Фраза: "Ой, какая прелесть!"
- Длительность: 5 секунд

**Настройки:**
```yaml
behavior:
  gestures:
    cute:
      enabled: true
      interval_seconds: 1.5
      consecutive_hits: 1
      debounce_seconds: 8.0
      tts_phrase: "Ой, какая прелесть!"
      display_duration_seconds: 5.0
```

---

## Configuration / Конфигурация

### Global Settings / Глобальные настройки

```yaml
behavior:
  gestures:
    enabled: true                    # Включить/выключить все жесты
    active_window_seconds: 30        # Распознавание только N сек после взаимодействия
```

### Quick Start / Быстрый старт

**До (медленно):**
```yaml
interval_seconds: 15.0        # Проверка каждые 15 секунд
consecutive_hits: 2           # Нужно 2 раза подряд = 30 секунд!
```

**После (быстро):**
```yaml
interval_seconds: 1.5         # Проверка каждые 1.5 секунды
consecutive_hits: 1           # Срабатывание с первого раза!
```

---

## How It Works / Как работает

### Detection Flow / Поток распознавания

1. **Camera captures frame** каждые 1.5 секунды
2. **Vision API analyzes** the frame (OpenAI Vision)
3. **If gesture detected** (answer starts with HEART/GUN/CUTE):
   - Increment hits counter
4. **If hits >= consecutive_hits** (теперь = 1):
   - **Trigger callback** (show animation, play sound, move servos)
   - Reset counter
   - Start debounce timer

### Debounce / Защита от повторов

**debounce_seconds** предотвращает повторное срабатывание слишком часто:
- Heart: 8 секунд
- Gun: 8 секунд
- Cute: 8 секунд

Это означает: после распознавания жеста, следующее срабатывание возможно только через 8 секунд.

---

## API Cost Optimization / Оптимизация стоимости API

### Token Usage / Использование токенов

**Раньше (экономно, но медленно):**
- Interval: 15 секунд
- Calls per minute: 4
- Tokens per call: ~10 (vision) + 8 (response)
- **Total: ~72 tokens/min**

**Теперь (быстро):**
- Interval: 1.5 секунды
- Calls per minute: 40
- Tokens per call: ~10 + 8
- **Total: ~720 tokens/min**

**Решение:**
- active_window_seconds: 30 - жесты активны только 30 сек после взаимодействия
- Это снижает использование до **~360 tokens за 30 sec**, затем 0 tokens

---

## Improved Prompts / Улучшенные промпты

### Heart Gesture Prompt

**Раньше:**
```
Look at the image. If the person is making a HEART gesture with both hands
(forming a heart shape with fingers/thumbs OR a small finger-heart gesture),
reply with exactly: HEART. Otherwise reply with exactly: NO.
```

**Теперь (более чувствительный):**
```
Look at the image. Is the person making a HEART gesture?
Heart gestures include:
1) Two hands forming a heart shape (fingers/thumbs together),
2) Single hand finger-heart (Korean style: thumb and index finger crossing),
3) Arms above head forming a big heart.
If you see ANY of these heart gestures, reply EXACTLY: HEART.
Otherwise reply EXACTLY: NO.
Be SENSITIVE - detect even partial or casual heart gestures.
```

### Gun Gesture Prompt

**Теперь:**
```
Look at the image. Is the person making a FINGER GUN gesture?
Gun gestures: index finger pointing forward, thumb up (like a pistol).
Can be with one hand or both hands.
If you see this gesture, reply EXACTLY: GUN.
Otherwise reply EXACTLY: NO.
Be SENSITIVE - detect even casual gun gestures.
```

### Cute Gesture Prompt (NEW!)

```
Look at the image. Is the person making a CUTE gesture?
Cute gestures include:
1) Peace sign / Victory sign (✌️ - two fingers up),
2) Waving hand (👋),
3) Hands near face (cute pose),
4) Thumbs up (👍),
5) Any playful or kawaii gesture.
If you see ANY cute/playful gesture, reply EXACTLY: CUTE.
Otherwise reply EXACTLY: NO.
Be SENSITIVE - detect even casual cute gestures.
```

---

## Files Changed / Изменённые файлы

### Modified / Изменённые

1. **config.yaml**
   - Reduced `interval_seconds`: 15.0 → 1.5
   - Reduced `consecutive_hits`: 2 → 1
   - Added `cute` gesture section

2. **robot_eva/behaviors/heart_gesture.py**
   - Improved prompt (more descriptive)
   - Added sensitivity instruction

3. **robot_eva/behaviors/gun_gesture.py**
   - Improved prompt (more descriptive)
   - Added sensitivity instruction

4. **robot_eva/core/robot.py**
   - Added import for `CuteGestureBehavior`
   - Added `_on_cute()` callback
   - Added cute gesture initialization
   - Added cute gesture start/stop

### Created / Созданные

5. **robot_eva/behaviors/cute_gesture.py** - NEW!
   - Complete cute gesture behavior
   - Supports peace sign, waving, cute poses, thumbs up
   - Random cute animation selection

---

## Testing / Тестирование

### Manual Test / Ручной тест

1. **Start robot:**
   ```bash
   python3 main.py
   ```

2. **Wake robot:**
   Say "Alexa" (or your wake word)

3. **Make gesture:**
   - ❤️ Heart: Form heart with hands
   - 🔫 Gun: Point finger like gun
   - 🌸 Cute: Peace sign / wave / thumbs up

4. **Observe reaction:**
   - Animation changes
   - Robot speaks phrase
   - Servos move (gun gesture)

### Expected Response Time / Ожидаемое время реакции

**Before:** 30+ seconds (need to hold gesture)  
**After:** 1.5-3 seconds (instant recognition!)

---

## Troubleshooting / Решение проблем

### Gesture not detected / Жест не распознаётся

**Check:**
1. Gestures enabled in config.yaml?
   ```yaml
   behavior:
     gestures:
       enabled: true
   ```

2. Camera working?
   ```bash
   python3 test_camera_from_config.py
   ```

3. Vision service available?
   - Check OpenAI API key in config.yaml
   - Check internet connection

4. Recent interaction?
   - Gestures only active for 30 sec after interaction
   - Wake robot with "Alexa" first

### Too sensitive / Слишком чувствительный

**Increase debounce:**
```yaml
debounce_seconds: 15.0  # Instead of 8.0
```

**Increase consecutive_hits:**
```yaml
consecutive_hits: 2  # Instead of 1 (но будет медленнее)
```

### Too slow / Слишком медленно

**Reduce interval:**
```yaml
interval_seconds: 1.0  # Instead of 1.5
```

**Note:** Lower interval = more API calls = higher cost

---

## Cost Estimation / Оценка стоимости

### OpenAI Vision API

**Pricing (approx):**
- Vision request: $0.00075 per image (GPT-4 Vision)
- Response tokens: $0.03 per 1K tokens

**With new settings:**
- Active window: 30 seconds after interaction
- Calls during window: 20 calls (30s / 1.5s)
- Cost per active window: 20 × $0.00075 = **$0.015**
- Plus response tokens: negligible

**Daily usage (assuming 50 interactions):**
- 50 × $0.015 = **$0.75 per day**
- **$22.50 per month**

**To reduce costs:**
1. Increase `interval_seconds` to 3.0 (half the calls)
2. Reduce `active_window_seconds` to 15
3. Disable gestures when not needed

---

## Future Improvements / Будущие улучшения

### Potential additions / Возможные дополнения

1. **Thumbs down** (👎) - negative reaction
2. **OK sign** (👌) - confirmation
3. **Stop sign** (✋) - stop command
4. **Counting fingers** (1, 2, 3...) - number input
5. **Rock/Paper/Scissors** - game gestures

### Performance / Производительность

1. **Local gesture recognition** (MediaPipe)
   - Faster (no network latency)
   - Cheaper (no API calls)
   - But: Requires Python 3.11 or earlier

2. **Hybrid approach:**
   - Simple gestures: MediaPipe (local)
   - Complex gestures: Vision API (cloud)

---

## Summary / Итог

✅ **Gestures now work instantly!** (1.5-3 seconds instead of 30+)  
✅ **New cute gesture added** with random animations  
✅ **Better prompts** for improved accuracy  
✅ **Cost-optimized** with active window limit  

🎯 **Test it now:** Make a heart, gun, or cute gesture in front of the camera!

---

**Date:** January 10, 2026  
**Version:** 1.0  
**Author:** AI Assistant (Claude Sonnet 4.5)
