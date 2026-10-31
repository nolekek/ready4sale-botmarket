from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database.models import Category, Product

def admin_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика и доходы", callback_data="adm_stats")],
        [
            InlineKeyboardButton(text="📁 Категории", callback_data="adm_categories"),
            InlineKeyboardButton(text="🛍️ Товары", callback_data="adm_products"),
        ],
        [
            InlineKeyboardButton(text="➕ Загрузить остатки (ключи)", callback_data="adm_add_items"),
            InlineKeyboardButton(text="🎁 Создать промокод", callback_data="adm_create_promo"),
        ],
        [
            InlineKeyboardButton(text="📢 Рассылка сообщений", callback_data="adm_broadcast"),
            InlineKeyboardButton(text="💾 Скачать бэкап базы (.db)", callback_data="adm_backup"),
        ],
        [InlineKeyboardButton(text="👤 Выйти в меню покупателя", callback_data="to_main")]
    ])

def admin_categories_manage_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="➕ Создать категорию", callback_data="adm_new_cat")]]
    for cat in categories:
        buttons.append([
            InlineKeyboardButton(text=f"❌ Удалить: {cat.name}", callback_data=f"adm_del_cat_{cat.id}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_products_list_kb(products: list[Product]) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="➕ Добавить новый товар", callback_data="adm_new_prod")]]
    for p in products:
        buttons.append([
            InlineKeyboardButton(text=f"📦 {p.name} ({p.price:.0f} руб.)", callback_data=f"adm_prod_info_{p.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"adm_del_prod_{p.id}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_choose_category_for_product_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"📁 {cat.name}", callback_data=f"adm_sel_cat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_choose_product_for_stock_kb(products: list[Product]) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        if p.product_type == "unique":
            buttons.append([InlineKeyboardButton(text=f"📥 {p.name}", callback_data=f"adm_stock_{p.id}")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_fsm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
