import os
from typing import List
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
    
    # Список администраторов
    raw_admins = os.getenv("ADMIN_IDS", "").strip()
    ADMIN_IDS: List[int] = [
        int(x.strip()) for x in raw_admins.split(",") if x.strip().isdigit()
    ]
    
    SHOP_NAME: str = os.getenv("SHOP_NAME", "🔥 Digital Hub Shop").strip()
    SUPPORT_CONTACT: str = os.getenv("SUPPORT_CONTACT", "@admin").strip()
    CHANNEL_URL: str = os.getenv("CHANNEL_URL", "").strip()
    SHOP_CURRENCY: str = os.getenv("SHOP_CURRENCY", "RUB").strip()
    
    try:
        REFERRAL_PERCENT: float = float(os.getenv("REFERRAL_PERCENT", "5.0"))
    except ValueError:
        REFERRAL_PERCENT = 5.0
        
    # Telegram Mini App
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "").strip()
    try:
        WEBAPP_PORT: int = int(os.getenv("WEBAPP_PORT", "8080"))
    except ValueError:
        WEBAPP_PORT = 8080

    # Платежи
    ENABLE_STARS: bool = os.getenv("ENABLE_STARS", "True").lower() in ("true", "1", "yes")
    try:
        STAR_RATE_RUB: float = float(os.getenv("STAR_RATE_RUB", "2.0"))
    except ValueError:
        STAR_RATE_RUB = 2.0
        
    CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN", "").strip()
    ENABLE_CRYPTO: bool = bool(CRYPTOBOT_TOKEN)
    
    ENABLE_SBP_MANUAL: bool = os.getenv("ENABLE_SBP_MANUAL", "True").lower() in ("true", "1", "yes")
    SBP_REQUISITES: str = os.getenv("SBP_REQUISITES", "Сбер / Т-Банк: +7 (999) 000-00-00 (Иван И.)").strip()

config = Config()
