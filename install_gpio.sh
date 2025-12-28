#!/bin/bash
# Скрипт установки GPIO зависимостей для RobotEva на Raspberry Pi 5

echo "=========================================="
echo "Установка GPIO зависимостей для RobotEva"
echo "=========================================="
echo ""

# Проверка, что скрипт запущен на Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Предупреждение: Этот скрипт предназначен для Raspberry Pi"
    read -p "Продолжить установку? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Определение версии Raspberry Pi
PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0')
echo "Обнаружена модель: $PI_MODEL"
echo ""

# Обновление списка пакетов
echo "Обновление списка пакетов..."
sudo apt-get update

# Базовые зависимости для компиляции
echo "Установка базовых зависимостей для компиляции..."
sudo apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-venv \
    git \
    swig \
    cmake

# GPIO библиотеки для Raspberry Pi 5
echo "Установка GPIO библиотек для Raspberry Pi 5..."
sudo apt-get install -y \
    liblgpio-dev \
    liblgpio1 \
    lgpio \
    python3-lgpio

# GPIO библиотеки для совместимости (старые версии Pi)
echo "Установка GPIO библиотек для совместимости..."
sudo apt-get install -y \
    python3-rpi.gpio \
    python3-gpiozero

# I2C инструменты
echo "Установка I2C инструментов..."
sudo apt-get install -y \
    i2c-tools \
    libi2c-dev

# SPI инструменты
echo "Установка SPI инструментов..."
sudo apt-get install -y \
    python3-spidev

# Включение I2C и SPI через raspi-config
echo "Включение I2C и SPI интерфейсов..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# Проверка виртуального окружения
if [ -d ".venv" ] || [ -d "venv" ]; then
    VENV_DIR=".venv"
    if [ ! -d ".venv" ]; then
        VENV_DIR="venv"
    fi
    
    echo "Обнаружено виртуальное окружение: $VENV_DIR"
    echo "Активация виртуального окружения..."
    source $VENV_DIR/bin/activate
    
    echo "Установка Python GPIO пакетов..."
    pip install --upgrade pip
    pip install lgpio
    pip install RPi.GPIO
    pip install gpiozero
    
    echo "Установка Adafruit CircuitPython библиотек..."
    pip install adafruit-circuitpython-servokit
    pip install adafruit-circuitpython-bme280
    pip install adafruit-circuitpython-lsm6ds
    pip install adafruit-blinka
    
    deactivate
    echo "Виртуальное окружение деактивировано"
else
    echo "Виртуальное окружение не найдено"
    echo "Установка Python GPIO пакетов глобально..."
    pip3 install --upgrade pip
    pip3 install lgpio
    pip3 install RPi.GPIO
    pip3 install gpiozero
    
    echo "Установка Adafruit CircuitPython библиотек..."
    pip3 install adafruit-circuitpython-servokit
    pip3 install adafruit-circuitpython-bme280
    pip3 install adafruit-circuitpython-lsm6ds
    pip3 install adafruit-blinka
fi

echo ""
echo "=========================================="
echo "Проверка установки GPIO..."
echo "=========================================="

# Проверка I2C
echo "Проверка I2C устройств..."
if command -v i2cdetect &> /dev/null; then
    echo "I2C устройства:"
    i2cdetect -y 1 2>/dev/null || echo "I2C не доступен (возможно, требуется перезагрузка)"
else
    echo "i2cdetect не найден"
fi

# Проверка Python модулей
echo ""
echo "Проверка Python модулей..."
if [ -d ".venv" ] || [ -d "venv" ]; then
    VENV_DIR=".venv"
    if [ ! -d ".venv" ]; then
        VENV_DIR="venv"
    fi
    source $VENV_DIR/bin/activate
    python3 -c "import lgpio; print('✓ lgpio установлен')" 2>/dev/null || echo "✗ lgpio не установлен"
    python3 -c "import RPi.GPIO; print('✓ RPi.GPIO установлен')" 2>/dev/null || echo "✗ RPi.GPIO не установлен"
    python3 -c "import gpiozero; print('✓ gpiozero установлен')" 2>/dev/null || echo "✗ gpiozero не установлен"
    python3 -c "import board; print('✓ adafruit-blinka установлен')" 2>/dev/null || echo "✗ adafruit-blinka не установлен"
    python3 -c "from adafruit_servokit import ServoKit; print('✓ adafruit-circuitpython-servokit установлен')" 2>/dev/null || echo "✗ adafruit-circuitpython-servokit не установлен"
    deactivate
else
    python3 -c "import lgpio; print('✓ lgpio установлен')" 2>/dev/null || echo "✗ lgpio не установлен"
    python3 -c "import RPi.GPIO; print('✓ RPi.GPIO установлен')" 2>/dev/null || echo "✗ RPi.GPIO не установлен"
    python3 -c "import gpiozero; print('✓ gpiozero установлен')" 2>/dev/null || echo "✗ gpiozero не установлен"
    python3 -c "import board; print('✓ adafruit-blinka установлен')" 2>/dev/null || echo "✗ adafruit-blinka не установлен"
fi

echo ""
echo "=========================================="
echo "Установка завершена!"
echo "=========================================="
echo ""
echo "Важные заметки:"
echo "1. Если I2C/SPI не работают, может потребоваться перезагрузка:"
echo "   sudo reboot"
echo ""
echo "2. Для проверки I2C устройств используйте:"
echo "   i2cdetect -y 1"
echo ""
echo "3. Для проверки прав доступа к GPIO:"
echo "   ls -l /dev/gpiochip*"
echo ""
echo "4. Если возникают проблемы с правами, добавьте пользователя в группу gpio:"
echo "   sudo usermod -a -G gpio $USER"
echo "   (требуется перелогиниться)"
echo ""

