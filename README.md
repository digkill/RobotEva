# RobotEva - Робот-ассистент Eva

Модульный фреймворк для робота-ассистента Eva на Raspberry Pi 5.

## Возможности

- 🎤 **Голосовое управление** - активация по фразе "Hey Eve", распознавание речи через OpenAI Whisper
- 🗣️ **Синтез речи** - генерация естественной речи через OpenAI TTS
- 🤖 **Умные ответы** - интеграция с Grok API для генерации ответов
- 👁️ **Компьютерное зрение** - описание того, что видит камера через GPT-4 Vision
- 🏠 **Умный дом** - управление устройствами через MQTT, Home Assistant, Zigbee, Z-Wave
- 🌐 **Поиск в интернете** - поиск информации через DuckDuckGo или Google
- 🎵 **Медиа** - воспроизведение музыки, видео, YouTube
- 😊 **Эмоции** - система эмоций с анимациями на дисплее
- 👤 **Датчик присутствия** - обнаружение человека, мониторинг сна и сердцебиения через mmWave C1001
- 🎮 **Сервоприводы** - управление головой, шеей и руками через PCA9685
- 📺 **Дисплеи** - анимации на 2.8" дисплее и HDMI
- 💡 **LED индикатор** - отображение состояния робота

## Требования

- Raspberry Pi 5
- Python 3.9+
- USB микрофон
- USB динамики
- USB камера
- 2.8" дисплей (SPI)
- HDMI дисплей
- PCA9685 контроллер сервоприводов
- 4 сервопривода (голова, шея, 2 руки)
- mmWave датчик C1001 DFRobot
- Расширительная плата датчиков для Raspberry Pi
- Arduino модуль LED (7-цветной мигающий)

## Установка

1. Клонируйте репозиторий или перейдите в директорию проекта:
```bash
cd /home/pi/Projects/RobotEva
```

2. Установите GPIO зависимости (обязательно для Raspberry Pi):
```bash
./install_gpio.sh
```

Этот скрипт установит все необходимые библиотеки для работы с GPIO, I2C, SPI и сервоприводами.

3. Установите остальные системные зависимости:
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev libportaudio2 libportaudiocpp0 libasound2-dev build-essential
```

4. Запустите скрипт установки (рекомендуется):
```bash
./setup.sh
```

Скрипт автоматически:
- Установит все системные зависимости
- Создаст виртуальное окружение (если не указан флаг `--no-venv`)
- Установит Python зависимости

Или установите зависимости вручную:
```bash
# Создайте виртуальное окружение (рекомендуется)
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

5. Загрузите код на Arduino для LED контроллера:
   - Откройте `arduino_led/led_controller.ino` в Arduino IDE
   - Настройте пины RGB LED в соответствии с вашим модулем
   - Загрузите код на Arduino
   - Подключите Arduino к Raspberry Pi через USB

6. Настройте конфигурацию:
```bash
cp config.yaml config.yaml.example
nano config.yaml
```

Заполните необходимые API ключи:
- `ai.openai.api_key` - ключ OpenAI API
- `ai.grok.api_key` - ключ Grok API

7. Убедитесь, что все устройства подключены и доступны:
- Проверьте I2C устройства (PCA9685): `i2cdetect -y 1`
- Проверьте USB устройства: `lsusb`
- Проверьте последовательные порты: `ls /dev/tty*`
- Проверьте камеру: `lsusb | grep -i camera`
- Проверьте микрофон: `arecord -l`
- Проверьте динамики: `aplay -l`

## Запуск

Если используете виртуальное окружение (рекомендуется):
```bash
source venv/bin/activate
python main.py
```

### Если на DSI виден рабочий стол, а эмоций нет

Если у вас включён Desktop (видите рабочий стол), а робот запущен из SSH/tty, у процесса **нет** `DISPLAY/WAYLAND_DISPLAY`,
и SDL-окно с эмоциями не появится.

Запускайте робота внутри desktop-сессии через скрипт:

```bash
./scripts/run_on_desktop.sh
```

Или без виртуального окружения:
```bash
python3 main.py
```

Или с правами суперпользователя (если требуется доступ к некоторым устройствам):
```bash
sudo python3 main.py
```

**Важно:** Если вы используете виртуальное окружение, активируйте его перед запуском!

## Настройка Arduino LED

Если вы используете Arduino для управления LED индикатором:

1. Откройте `arduino_led/led_controller.ino` в Arduino IDE
2. Настройте пины RGB LED в соответствии с вашим модулем (по умолчанию: 9, 10, 11)
3. Загрузите код на Arduino
4. Подключите Arduino к Raspberry Pi через USB
5. Убедитесь, что порт указан правильно в `config.yaml` (по умолчанию: `/dev/ttyACM0`)

## Файлы конфигурации

### gpio_mapping.yaml

Централизованный файл маппинга GPIO и устройств. Содержит:
- I2C адреса устройств (PCA9685, BME280, LSM6DS)
- Конфигурацию сервоприводов (каналы, углы)
- GPIO пины для mmWave C1001 (через UART)
- GPIO пины для RGB LED модуля (прямое подключение)
- USB устройства (микрофон, динамики, камера)
- SPI настройки (дисплей)

**Важно:** mmWave C1001 и RGB LED подключаются через GPIO пины, а не через USB/Serial.

Для проверки маппинга:
```bash
python scripts/check_gpio_mapping.py
```

## Структура проекта

```
RobotEva/
├── robot_eva/
│   ├── core/           # Основные компоненты
│   │   ├── config.py   # Управление конфигурацией
│   │   └── robot.py    # Главный класс робота
│   ├── hardware/       # Управление железом
│   │   ├── servos.py   # Сервоприводы
│   │   ├── display.py  # Дисплеи
│   │   ├── audio.py    # Аудио
│   │   ├── camera.py   # Камера
│   │   ├── sensors.py  # Сенсоры
│   │   └── led.py      # LED индикатор
│   ├── ai/             # AI модули
│   │   ├── wake_word.py
│   │   ├── speech_to_text.py
│   │   ├── text_to_speech.py
│   │   ├── llm.py
│   │   └── vision.py
│   ├── emotions/       # Система эмоций
│   │   ├── emotion_engine.py
│   │   └── animations.py
│   └── services/       # Внешние сервисы
│       ├── smart_home.py
│       ├── internet.py
│       └── media.py
├── models/             # Модели (wake word)
├── config.yaml        # Конфигурация
├── requirements.txt   # Зависимости
├── main.py           # Точка входа
└── README.md         # Документация
```

## Расширение функционала

Фреймворк разработан с учетом расширяемости. Вы можете:

1. **Добавить новые модули железа** в `robot_eva/hardware/`
2. **Добавить новые AI сервисы** в `robot_eva/ai/`
3. **Добавить новые эмоции и анимации** в `robot_eva/emotions/`
4. **Добавить новые сервисы** в `robot_eva/services/`

Все модули следуют единому интерфейсу с методами `initialize()`, `cleanup()` и соответствующими методами работы.

## Решение проблем

### Ошибка при установке pyaudio

Если при установке `pyaudio` возникает ошибка `fatal error: portaudio.h: No such file or directory`:

```bash
sudo apt-get install -y portaudio19-dev libportaudio2 libportaudiocpp0 libasound2-dev build-essential
```

Затем повторите установку:
```bash
pip install pyaudio
```

### Ошибка ModuleNotFoundError: No module named 'lgpio'

Для Raspberry Pi 5 требуется библиотека `lgpio`. Установите системные зависимости:

```bash
sudo apt-get install -y swig liblgpio-dev
```

Затем установите Python пакет:
```bash
pip install lgpio

### 2.8" SPI дисплей: "GPIO busy" на CS (BCM8/BCM7)

Если при старте видите:

- `Не удалось захватить CS pin (BCM8) — GPIO busy`

Это означает, что стандартные SPI chip-select линии **CE0/CE1** заняты ядром Linux (у вас есть `/dev/spidev0.0`, `/dev/spidev0.1`), и библиотека дисплея не может “захватить” CS как GPIO.

Решение:

- Подключите **CS (chip select) дисплея** на **любой свободный GPIO** (например **BCM5** или **BCM6**)
- В `config.yaml` установите:
  - `hardware.display.small.cs_pin: 5` (или другой пин, который вы выбрали)

Также убедитесь, что `dc_pin` и `reset_pin` выставлены под вашу разводку.
```

### Ошибка ImportError: cannot import name 'LSM6DS33'

Если возникает ошибка импорта `LSM6DS33`, это уже исправлено в коде. Убедитесь, что используете последнюю версию кода. Правильное имя класса - `LSM6DS`.

### Ошибка "externally-managed-environment"

Если получаете ошибку о внешне управляемом окружении, используйте виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Проблемы с GPIO/I2C устройствами

Если возникают проблемы с GPIO или I2C устройствами:

1. Запустите скрипт установки GPIO:
```bash
./install_gpio.sh
```

2. Проверьте подключение I2C:
```bash
i2cdetect -y 1
```

3. Убедитесь, что I2C включен:
```bash
sudo raspi-config
# Интерфейсы -> I2C -> Enable
```

4. Если сервоконтроллер PCA9685 не определяется, проверьте:
   - Правильность подключения к I2C шине
   - Адрес устройства (по умолчанию 0x40)
   - Права доступа к /dev/i2c-1
   - **Важно:** Робот будет работать даже без PCA9685, просто без управления сервоприводами

5. Для проблем с правами доступа к GPIO:
```bash
sudo usermod -a -G gpio,i2c $USER
# Требуется перелогиниться
```

6. Ошибка "Resource temporarily unavailable" при инициализации I2C:
   - Устройство может быть не подключено - это нормально, робот продолжит работу
   - Проверьте подключение устройств
   - Убедитесь, что I2C шина не занята другим процессом

### Проблемы с USB устройствами

Проверьте подключение USB устройств:
```bash
lsusb
ls /dev/tty*
```

## Лицензия

MIT

## Автор

RobotEva Framework

