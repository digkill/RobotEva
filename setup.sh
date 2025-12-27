#!/bin/bash
# Скрипт установки RobotEva

echo "Установка RobotEva..."

# Обновление системы
echo "Обновление системы..."
sudo apt-get update
sudo apt-get upgrade -y

# Установка системных зависимостей
echo "Установка системных зависимостей..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    i2c-tools \
    libasound2-dev \
    portaudio19-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    vlc \
    libopencv-dev \
    python3-opencv \
    git \
    libffi-dev \
    libssl-dev

# Включение I2C
echo "Включение I2C..."
sudo raspi-config nonint do_i2c 0

# Создание виртуального окружения (опционально, но рекомендуется)
if [ "$1" != "--no-venv" ]; then
    echo "Создание виртуального окружения..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    PIP_CMD="pip"
else
    PIP_CMD="pip3"
fi

# Установка Python зависимостей
echo "Установка Python зависимостей..."
$PIP_CMD install --upgrade pip
$PIP_CMD install -r requirements.txt

# Создание директорий
echo "Создание необходимых директорий..."
mkdir -p /home/pi/Music
mkdir -p /home/pi/Projects/RobotEva/logs

# Установка прав на выполнение
chmod +x main.py

echo "Установка завершена!"
echo ""
echo "Следующие шаги:"
echo "1. Настройте config.yaml с вашими API ключами"
echo "2. Убедитесь, что все устройства подключены"
echo "3. Запустите: python3 main.py"

