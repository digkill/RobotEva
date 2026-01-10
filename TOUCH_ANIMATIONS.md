# Touch Animations / Анимации при касании экрана

## Описание

RobotEva поддерживает забавные анимации лица при касании экрана (тачскрина). Когда вы касаетесь дисплея, робот показывает случайную эмоциональную анимацию, а затем возвращается к предыдущей эмоции.

## Функционал

### 🎨 Доступные анимации при касании:

1. **dizzy** - Кружащиеся глаза (@_@)
2. **stars** - Звёздочки в глазах (★_★)
3. **hearts** - Сердечки в глазах (♥_♥)
4. **silly** - Глупое лицо (один глаз закрыт, язык высунут)
5. **crazy** - Безумный взгляд (◉_◉)
6. **sparkle** - Сверкающие глаза (✨_✨)
7. **laugh** - Смех (закрытые глаза + большой рот)
8. **blush** - Застенчивый румянец (//_//)
9. **surprise_big** - Огромное удивление (O_O!)
10. **money** - Денежные знаки ($-$)

### 🎯 Как работает:

1. Вы касаетесь экрана (или кликаете мышью в режиме SDL)
2. Робот выбирает случайную анимацию из списка
3. Показывает анимацию (не зацикленная, проигрывается один раз)
4. Возвращается к предыдущей эмоции через 0.3 секунды

### 🔧 Технические детали:

- **Работает только с backend: sdl** (требуется Desktop GUI)
- Поддерживает touchscreen и мышь
- Обрабатывает события `pygame.FINGERDOWN` и `pygame.MOUSEBUTTONDOWN`
- Все анимации временные (не зацикленные)
- Предыдущая анимация сохраняется и восстанавливается

## Настройка

### config.yaml

```yaml
hardware:
  display:
    small:
      backend: sdl  # ОБЯЗАТЕЛЬНО для touch анимаций!
      touch:
        enabled: true
        # Список анимаций (можно выбрать только те, которые нравятся)
        animations:
          - dizzy
          - stars
          - hearts
          - silly
          - crazy
          - sparkle
          - laugh
          - blush
          - surprise_big
          - money
```

### Опции конфигурации:

- `hardware.display.small.touch.enabled` - включить/выключить touch анимации (default: true)
- `hardware.display.small.touch.animations` - список анимаций (default: все 10)

### Примеры настройки:

#### Только милые анимации:
```yaml
touch:
  enabled: true
  animations:
    - hearts
    - sparkle
    - blush
    - laugh
```

#### Только безумные анимации:
```yaml
touch:
  enabled: true
  animations:
    - dizzy
    - crazy
    - silly
    - money
```

#### Отключить touch анимации:
```yaml
touch:
  enabled: false
```

## Использование

### Требования:

1. **Desktop GUI** - должна быть запущена графическая среда (X11/Wayland)
2. **SDL backend** - в config.yaml должно быть `backend: sdl` или `backend: auto` (если GUI есть)
3. **Touchscreen или мышь** - для генерации событий касания

### Запуск:

```bash
# Убедитесь, что используется SDL backend
cd /home/pi/Projects/RobotEva
python3 main.py
```

### Тестирование:

Создайте тестовый скрипт для проверки анимаций:

```bash
python3 test_touch_animations.py
```

## Кастомизация

### Добавление своих анимаций:

1. Откройте `robot_eva/emotions/animations.py`
2. Добавьте новую анимацию в словарь `ANIMATIONS`:

```python
"my_custom": {
    "frames": 15,
    "loop": False,  # Важно! Touch анимации не зацикленные
    "elements": [
        {"type": "eye_left", "x": -46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
        {"type": "eye_right", "x": 46, "y": -20, "shape": "ellipse", "width": 70, "height": 55},
        {"type": "mouth", "x": 0, "y": 55, "shape": "arc", "start": 20, "end": 160, "radius": 40},
    ],
},
```

3. Добавьте имя анимации в `config.yaml`:

```yaml
animations:
  - my_custom
```

### Элементы анимации:

- **eye_left, eye_right** - глаза (ellipse, line, arc)
- **mouth** - рот (ellipse, line, arc)
- **text** - текст/emoji (поддерживаются эмодзи!)
- **pupil_left, pupil_right** - зрачки

### Фигуры:

- `ellipse` - эллипс (width, height)
- `line` - линия (width)
- `arc` - дуга (start, end, radius)

## Решение проблем

### Touch не работает:

1. **Проверьте backend:**
   ```bash
   grep "backend:" config.yaml
   # Должно быть: backend: auto или backend: sdl
   ```

2. **Проверьте Desktop GUI:**
   ```bash
   echo $DISPLAY
   # Должна быть установлена переменная
   ```

3. **Проверьте логи:**
   ```bash
   tail -f robot_eva.log | grep -i touch
   # Должны быть сообщения: "Touch detected at..."
   ```

### Анимации не отображаются:

1. **Проверьте, что enabled=true:**
   ```bash
   grep -A 5 "touch:" config.yaml
   ```

2. **Проверьте список анимаций:**
   - Убедитесь, что массив `animations` не пустой
   - Все имена должны совпадать с именами в `animations.py`

### Backend не SDL:

```bash
# В логах:
grep "дисплей инициализирован" robot_eva.log
# Если там "fbdev" вместо "sdl" - touch не будет работать
```

**Решение:** Установите `backend: sdl` в config.yaml

## Примеры

### Базовое использование:

```python
# Робот автоматически обрабатывает touch события
# Просто касайтесь экрана!
```

### Программное управление:

```python
# В коде робота:
await display_manager.show_animation("stars")  # Показать звёздочки
await asyncio.sleep(2)
await display_manager.show_animation("neutral")  # Вернуться к нейтральному
```

## Файлы проекта

- `robot_eva/hardware/display.py` - DisplayManager с обработкой touch
- `robot_eva/hardware/display_small_sdl.py` - SDL backend с touch callback
- `robot_eva/emotions/animations.py` - Все анимации, включая touch
- `config.yaml` - Конфигурация touch анимаций

## FAQ

**Q: Можно ли использовать touch с fbdev backend?**
A: Нет, fbdev не поддерживает обработку событий. Нужен SDL backend.

**Q: Можно ли добавить звук при касании?**
A: Да! Модифицируйте метод `_handle_touch` в `display.py` и добавьте воспроизведение звука.

**Q: Работает ли с SSH подключением?**
A: Для SDL нужен локальный Desktop. По SSH используйте X11 forwarding или VNC.

**Q: Можно ли сделать разные анимации для разных областей экрана?**
A: Да! В `_handle_touch` проверяйте координаты `pos` и выбирайте анимацию на их основе.

---

✨ **Наслаждайтесь интерактивными анимациями RobotEva!** ✨
