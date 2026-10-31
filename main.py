import asyncio
import io
import logging
import sys
from aiohttp import web

# Принудительная установка UTF-8 для консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import MenuButtonDefault, MenuButtonWebApp, WebAppInfo
from bot.config import config
from bot.database.setup import init_db
from bot.handlers.admin import admin_router
from bot.handlers.payments import payments_router
from bot.handlers.user import user_router
from bot.middlewares.throttler import ThrottlingMiddleware
from bot.web.server import create_web_app

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoShop")

async def main():
    if not config.BOT_TOKEN:
        logger.error("[ERROR] Не указан BOT_TOKEN в файле .env!")
        return

    logger.info("[DB] Инициализация базы данных SQLite...")
    await init_db()
    logger.info("[DB] База данных готова к работе.")

    # 1. Запуск WebApp веб-сервера (aiohttp)
    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.WEBAPP_PORT)
    await site.start()
    logger.info(f"[WEBAPP] Сервер Mini App запущен на http://localhost:{config.WEBAPP_PORT}")

    # 2. Создание экземпляра бота
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 3. Настройка кнопки меню в Telegram (MenuButtonWebApp)
    if config.WEBAPP_URL:
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🛍️ Магазин",
                    web_app=WebAppInfo(url=config.WEBAPP_URL)
                )
            )
            logger.info(f"[MENU] Установлена кнопка WebApp меню: {config.WEBAPP_URL}")
        except Exception as e:
            logger.warning(f"[MENU] Не удалось установить MenuButtonWebApp: {e}")
    else:
        try:
            await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        except Exception:
            pass

    dp = Dispatcher()

    # Подключение Middleware защиты от спама
    dp.message.middleware(ThrottlingMiddleware(limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=0.3))

    # Регистрация роутеров (важен порядок: admin -> payments -> user)
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    dp.include_router(user_router)

    # Информация о запуске
    bot_info = await bot.get_me()
    print("=" * 60)
    print(f">> AUTOSHOP PRO v2.4 (+ MINI APP) УСПЕШНО ЗАПУЩЕН!")
    print(f">> Бот: @{bot_info.username} ({bot_info.first_name}) [ID: {bot_info.id}]")
    print(f">> Mini App Server: http://localhost:{config.WEBAPP_PORT}")
    print(f">> WebApp URL: {config.WEBAPP_URL or 'Локальный режим (укажите WEBAPP_URL в .env)'}")
    print(f">> Оплата Stars: {'Включена' if config.ENABLE_STARS else 'Выключена'}")
    print(f">> CryptoBot: {'Включен' if config.ENABLE_CRYPTO else 'Выключен'}")
    print(f">> СБП/Карты: {'Включены' if config.ENABLE_SBP_MANUAL else 'Выключены'}")
    print("=" * 60)

    try:
        # Удаляем вебхуки и запускаем Long Polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
