from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from bot.config import config
from bot.database.models import Category, Product

def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    
    # Главная кнопка WebApp (если указан WEBAPP_URL)
    if config.WEBAPP_URL:
        buttons.append([
            InlineKeyboardButton(
                text="🚀 Открыть WebApp Магазин",
                web_app=WebAppInfo(url=config.WEBAPP_URL)
            )
        ])
        buttons.append([InlineKeyboardButton(text="🛍️ Обычный каталог (текст)", callback_data="catalog")])
    else:
        buttons.append([InlineKeyboardButton(text="🛍️ Каталог товаров", callback_data="catalog")])

    buttons.extend([
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="💳 Пополнить", callback_data="deposit_start"),
        ],
        [
            InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders"),
            InlineKeyboardButton(text="🎁 Промокод", callback_data="enter_promo"),
        ],
        [
            InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
            InlineKeyboardButton(text="💬 Поддержка", url=f"https://t.me/{config.SUPPORT_CONTACT.lstrip('@')}"),
        ],
    ])
    
    if config.CHANNEL_URL:
        buttons.append([InlineKeyboardButton(text="📢 Наш канал / Отзывы", url=config.CHANNEL_URL)])
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_panel")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"📁 {cat.name}", callback_data=f"cat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="◀️ В главное меню", callback_data="to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def products_kb(category_id: int, products: list[Product], items_counts: dict[int, int]) -> InlineKeyboardMarkup:
    buttons = []
    for prod in products:
        count = items_counts.get(prod.id, 0)
        stock_badge = "♾️" if prod.product_type == "infinite" else f"{count} шт."
        buttons.append([
            InlineKeyboardButton(
                text=f"{prod.name} | {prod.price:.0f} {config.SHOP_CURRENCY} ({stock_badge})",
                callback_data=f"prod_{prod.id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ К категориям", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_detail_kb(product: Product, is_available: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_available:
        buttons.append([InlineKeyboardButton(text=f"💳 Купить за {product.price:.0f} {config.SHOP_CURRENCY}", callback_data=f"buy_balance_{product.id}")])
        
        # Быстрая покупка без пополнения
        quick_pay = []
        if config.ENABLE_STARS:
            stars_price = max(1, int(product.price / config.STAR_RATE_RUB))
            quick_pay.append(InlineKeyboardButton(text=f"⭐ Stars ({stars_price} ⭐️)", callback_data=f"buy_stars_{product.id}"))
        if config.ENABLE_CRYPTO:
            quick_pay.append(InlineKeyboardButton(text="💎 CryptoBot", callback_data=f"buy_crypto_{product.id}"))
        if quick_pay:
            buttons.append(quick_pay)
    else:
        buttons.append([InlineKeyboardButton(text="❌ Нет в наличии", callback_data="out_of_stock")])
        
    buttons.append([InlineKeyboardButton(text="◀️ Назад к товарам", callback_data=f"cat_{product.category_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="deposit_start"),
            InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_orders")
        ],
        [
            InlineKeyboardButton(text="🎁 Активировать промокод", callback_data="enter_promo"),
            InlineKeyboardButton(text="👥 Партнерская программа", callback_data="referrals")
        ],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="to_main")]
    ])

def deposit_methods_kb(amount: float) -> InlineKeyboardMarkup:
    buttons = []
    if config.ENABLE_STARS:
        stars_amount = max(1, int(amount / config.STAR_RATE_RUB))
        buttons.append([InlineKeyboardButton(text=f"⭐ Telegram Stars ({stars_amount} ⭐️)", callback_data=f"pay_stars_{amount}")])
    if config.ENABLE_CRYPTO:
        buttons.append([InlineKeyboardButton(text="💎 CryptoBot (USDT / TON / BTC)", callback_data=f"pay_crypto_{amount}")])
    if config.ENABLE_SBP_MANUAL:
        buttons.append([InlineKeyboardButton(text="💳 СБП / Карта РФ (Ручной перевод)", callback_data=f"pay_sbp_{amount}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="profile")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def sbp_manual_kb(invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил (Отправить чек)", callback_data=f"sbp_paid_{invoice_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="profile")]
    ])

def admin_receipt_action_kb(invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить зачисление", callback_data=f"adm_confirm_pay_{invoice_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_reject_pay_{invoice_id}")
        ]
    ])

def back_to_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="to_main")]
    ])
