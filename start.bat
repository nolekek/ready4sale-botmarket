@echo off
chcp 65001 >nul
title AutoShop Pro — Запуск бота
color 0b

echo ========================================================
echo        🚀 ЗАПУСК ТЕЛЕГРАМ-БОТА AUTOSHOP PRO
echo ========================================================
echo.

:: Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0c
    echo [ОШИБКА] Python не найден в системе!
    echo Установите Python версии 3.10 или выше с сайта https://python.org
    echo ОБЯЗАТЕЛЬНО поставьте галочку "Add Python to PATH" при установке.
    pause
    exit /b
)

:: Проверка файла настроек .env
if not exist .env (
    echo [ВНИМАНИЕ] Файл настроек .env не найден.
    echo Создаем .env из шаблона .env.example...
    copy .env.example .env >nul
    echo.
    echo Сейчас откроется файл .env в Блокноте.
    echo Вставьте туда токен вашего бота от @BotFather и сохраните файл (Ctrl+S).
    echo.
    pause
    notepad .env
)

:: Создание виртуального окружения venv, если его нет
if not exist venv (
    echo [ИНФО] Создание виртуального окружения (venv)...
    python -m venv venv
)

:: Активация venv и установка зависимостей
call venv\Scripts\activate.bat

echo [ИНФО] Проверка и установка библиотек...
pip install -r requirements.txt --quiet

echo.
echo ========================================================
echo [УСПЕХ] Запуск основного скрипта...
echo ========================================================
echo.

python main.py

echo.
echo Бот завершил работу.
pause
