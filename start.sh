#!/bin/bash
# ========================================================
# Скрипт автоматического запуска AutoShop Pro на Linux VPS
# ========================================================

set -e

echo "========================================================"
echo "      🚀 ЗАПУСК AUTOSHOP PRO НА LINUX VDS / VPS"
echo "========================================================"

# Проверка Python 3
if ! command -v python3 &> /dev/null; then
    echo "Python3 не найден. Установка python3 и python3-venv..."
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv
fi

# Проверка .env
if [ ! -f .env ]; then
    echo "Файл .env не найден! Копируем из .env.example..."
    cp .env.example .env
    echo "Отредактируйте .env перед запуском: nano .env"
    exit 1
fi

# Создание виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения venv..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Установка зависимостей..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo "Запуск бота..."
python3 main.py
