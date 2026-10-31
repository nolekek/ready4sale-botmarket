import asyncio
import os
from datetime import datetime
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message
from bot.config import config
from bot.database import requests as db
from bot.database.setup import DB_PATH
from bot.keyboards import admin_kb, user_kb

admin_router = Router(name="admin_router")

class NewCategoryStates(StatesGroup):
    waiting_for_name = State()

class NewProductStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_name = State()
    waiting_for_desc = State()
    waiting_for_price = State()
    waiting_for_type = State()  # "unique" или "infinite"
    waiting_for_static_content = State()

class StockUploadStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_items_data = State()

class NewPromoStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_amount = State()
    waiting_for_activations = State()

class BroadcastStates(StatesGroup):
    waiting_for_content = State()

# Проверка прав администратора
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@admin_router.callback_query(F.data == "admin_panel")
@admin_router.message(Command("admin"))
async def open_admin_panel(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("Доступ запрещен.", show_alert=True)
        return

    text = (
        "⚙️ <b>Панель управления магазином AutoShop Pro</b>\n\n"
        "Выберите раздел для управления товарами, рассылками или просмотром статистики:"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=admin_kb.admin_main_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=admin_kb.admin_main_kb(), parse_mode="HTML")

# ================= СТАТИСТИКА =================

@admin_router.callback_query(F.data == "adm_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    users_count = await db.get_all_users_count()
    stats = await db.get_orders_stats()

    text = (
        "📊 <b>Статистика магазина</b>\n\n"
        f"👥 Всего пользователей в базе: <b>{users_count}</b>\n\n"
        f"📦 Всего успешных заказов: <b>{stats['total_orders']}</b>\n"
        f"💰 Общая выручка: <b>{stats['total_revenue']} {config.SHOP_CURRENCY}</b>\n\n"
        f"📅 <b>За последние 24 часа:</b>\n"
        f"• Новых заказов: <b>{stats['orders_today']}</b>\n"
        f"• Выручка за сутки: <b>{stats['revenue_today']} {config.SHOP_CURRENCY}</b>\n"
    )

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

# ================= УПРАВЛЕНИЕ КАТЕГОРИЯМИ =================

@admin_router.callback_query(F.data == "adm_categories")
async def cb_admin_categories(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    categories = await db.get_categories()
    text = (
        "📁 <b>Управление категориями:</b>\n\n"
        "Вы можете создать новую категорию или удалить существующую (внимание: при удалении категории удаляются привязанные товары)."
    )
    await call.message.edit_text(text, reply_markup=admin_kb.admin_categories_manage_kb(categories), parse_mode="HTML")
    await call.answer()

@admin_router.callback_query(F.data == "adm_new_cat")
async def cb_new_category(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(NewCategoryStates.waiting_for_name)
    await call.message.edit_text(
        "Введите название новой категории (например, <code>🎮 Игровые аккаунты</code>):",
        reply_markup=admin_kb.cancel_fsm_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(NewCategoryStates.waiting_for_name)
async def process_new_category_name(message: Message, state: FSMContext):
    cat_name = message.text.strip()
    await db.create_category(cat_name)
    await state.clear()
    await message.answer(f"✅ Категория <b>«{cat_name}»</b> успешно создана!", reply_markup=admin_kb.admin_main_kb(), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_del_cat_"))
async def cb_del_category(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    cat_id = int(call.data.replace("adm_del_cat_", ""))
    await db.delete_category(cat_id)
    await call.answer("Категория удалена.", show_alert=True)
    
    categories = await db.get_categories()
    await call.message.edit_reply_markup(reply_markup=admin_kb.admin_categories_manage_kb(categories))

# ================= УПРАВЛЕНИЕ ТОВАРАМИ =================

@admin_router.callback_query(F.data == "adm_products")
async def cb_admin_products(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    categories = await db.get_categories()
    all_products = []
    for c in categories:
        prods = await db.get_products_by_category(c.id)
        all_products.extend(prods)

    text = "🛍️ <b>Управление товарами:</b>\n\nСписок всех активных товаров в магазине:"
    await call.message.edit_text(text, reply_markup=admin_kb.admin_products_list_kb(all_products), parse_mode="HTML")
    await call.answer()

@admin_router.callback_query(F.data == "adm_new_prod")
async def cb_new_product_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    categories = await db.get_categories()
    if not categories:
        await call.answer("Сначала создайте хотя бы одну категорию!", show_alert=True)
        return

    await state.set_state(NewProductStates.waiting_for_category)
    await call.message.edit_text(
        "Выберите категорию для нового товара:",
        reply_markup=admin_kb.admin_choose_category_for_product_kb(categories)
    )
    await call.answer()

@admin_router.callback_query(NewProductStates.waiting_for_category, F.data.startswith("adm_sel_cat_"))
async def process_prod_category(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.replace("adm_sel_cat_", ""))
    await state.update_data(category_id=cat_id)
    await state.set_state(NewProductStates.waiting_for_name)
    await call.message.edit_text("Введите название товара (например, <code>Steam Ключ CS2 Prime</code>):", parse_mode="HTML")
    await call.answer()

@admin_router.message(NewProductStates.waiting_for_name)
async def process_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(NewProductStates.waiting_for_desc)
    await message.answer("Введите описание товара (характеристики, правила, гарантия):")

@admin_router.message(NewProductStates.waiting_for_desc)
async def process_prod_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(NewProductStates.waiting_for_price)
    await message.answer("Укажите цену товара в рублях (например, <code>199</code>):", parse_mode="HTML")

@admin_router.message(NewProductStates.waiting_for_price)
async def process_prod_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректная цена. Введите положительное число (например, 199):")
        return

    await state.update_data(price=price)
    await state.set_state(NewProductStates.waiting_for_type)
    
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Штучный товар (ключи, аккаунты)", callback_data="type_unique")],
        [InlineKeyboardButton(text="♾️ Бесконечный товар (ссылка, мануал, софт)", callback_data="type_infinite")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
    ])
    await message.answer("Выберите тип товара:\n\n• <b>Штучный:</b> списывается по 1 строке из остатков при каждой покупке.\n• <b>Бесконечный:</b> выдает один и тот же текст/ссылку/файл всем покупателям.", reply_markup=kb, parse_mode="HTML")

@admin_router.callback_query(NewProductStates.waiting_for_type, F.data == "type_unique")
async def process_type_unique(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prod = await db.create_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        price=data["price"],
        product_type="unique"
    )
    await state.clear()
    await call.message.edit_text(
        f"✅ Товар <b>«{prod.name}»</b> успешно создан!\n\n"
        "Теперь перейдите в раздел <b>«Загрузить остатки»</b>, чтобы залить ключи/строки для автовыдачи.",
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.callback_query(NewProductStates.waiting_for_type, F.data == "type_infinite")
async def process_type_infinite_prompt(call: CallbackQuery, state: FSMContext):
    await state.set_state(NewProductStates.waiting_for_static_content)
    await call.message.edit_text(
        "Введите текст/ссылку/инструкцию, которая будет автоматически отправляться покупателю после оплаты:",
        reply_markup=admin_kb.cancel_fsm_kb()
    )
    await call.answer()

@admin_router.message(NewProductStates.waiting_for_static_content)
async def process_type_infinite_save(message: Message, state: FSMContext):
    data = await state.get_data()
    prod = await db.create_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        price=data["price"],
        product_type="infinite",
        static_content=message.text.strip()
    )
    await state.clear()
    await message.answer(
        f"✅ Бесконечный товар <b>«{prod.name}»</b> создан и готов к автопродаже!",
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML"
    )

@admin_router.callback_query(F.data.startswith("adm_del_prod_"))
async def cb_del_product(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    prod_id = int(call.data.replace("adm_del_prod_", ""))
    await db.delete_product(prod_id)
    await call.answer("Товар удален.", show_alert=True)
    
    # Обновляем список
    categories = await db.get_categories()
    all_products = []
    for c in categories:
        prods = await db.get_products_by_category(c.id)
        all_products.extend(prods)
    await call.message.edit_reply_markup(reply_markup=admin_kb.admin_products_list_kb(all_products))

# ================= ЗАГРУЗКА ОСТАТКОВ (КЛЮЧИ / СТРОКИ) =================

@admin_router.callback_query(F.data == "adm_add_items")
async def cb_add_items_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    categories = await db.get_categories()
    all_products = []
    for c in categories:
        prods = await db.get_products_by_category(c.id)
        all_products.extend(prods)

    unique_products = [p for p in all_products if p.product_type == "unique"]
    if not unique_products:
        await call.answer("Нет штучных товаров. Создайте товар с типом 'Штучный'.", show_alert=True)
        return

    await state.set_state(StockUploadStates.waiting_for_product)
    await call.message.edit_text(
        "Выберите товар, для которого хотите загрузить остатки:",
        reply_markup=admin_kb.admin_choose_product_for_stock_kb(unique_products)
    )
    await call.answer()

@admin_router.callback_query(StockUploadStates.waiting_for_product, F.data.startswith("adm_stock_"))
async def process_stock_select_prod(call: CallbackQuery, state: FSMContext):
    prod_id = int(call.data.replace("adm_stock_", ""))
    product = await db.get_product(prod_id)
    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return

    await state.update_data(stock_product_id=prod_id)
    await state.set_state(StockUploadStates.waiting_for_items_data)

    text = (
        f"📥 <b>Загрузка остатков для «{product.name}»</b>\n\n"
        "Отправьте данные построчно прямо в сообщении или прикрепите <b>.txt файл</b>.\n\n"
        "<i>Пример:</i>\n"
        "<code>key_1111-2222-3333</code>\n"
        "<code>key_4444-5555-6666</code>\n"
        "<code>login:password:token</code>"
    )
    await call.message.edit_text(text, reply_markup=admin_kb.cancel_fsm_kb(), parse_mode="HTML")
    await call.answer()

@admin_router.message(StockUploadStates.waiting_for_items_data)
async def process_stock_items_upload(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data.get("stock_product_id")
    
    lines = []
    if message.document and message.document.file_name.endswith(".txt"):
        file_obj = await message.bot.get_file(message.document.file_id)
        downloaded = await message.bot.download_file(file_obj.file_path)
        content = downloaded.read().decode("utf-8", errors="ignore")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
    elif message.text:
        lines = [line.strip() for line in message.text.splitlines() if line.strip()]
    else:
        await message.answer("Пожалуйста, отправьте текстовое сообщение или файл .txt:")
        return

    if not lines:
        await message.answer("Не найдено строк для загрузки. Попробуйте снова:")
        return

    count = await db.add_items_bulk(prod_id, lines)
    await state.clear()
    await message.answer(
        f"✅ <b>Успешно добавлено {count} позиций товара!</b>",
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML"
    )

# ================= СОЗДАНИЕ ПРОМОКОДА =================

@admin_router.callback_query(F.data == "adm_create_promo")
async def cb_create_promo_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(NewPromoStates.waiting_for_code)
    await call.message.edit_text(
        "Введите текст промокода (например, <code>GIFT100</code>):",
        reply_markup=admin_kb.cancel_fsm_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@admin_router.message(NewPromoStates.waiting_for_code)
async def process_promo_name(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip().upper())
    await state.set_state(NewPromoStates.waiting_for_amount)
    await message.answer("Введите сумму бонуса в рублях (например, <code>100</code>):", parse_mode="HTML")

@admin_router.message(NewPromoStates.waiting_for_amount)
async def process_promo_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное число:")
        return

    await state.update_data(amount=amount)
    await state.set_state(NewPromoStates.waiting_for_activations)
    await message.answer("Сколько всего человек смогут активировать промокод? (например, <code>10</code>):", parse_mode="HTML")

@admin_router.message(NewPromoStates.waiting_for_activations)
async def process_promo_activations(message: Message, state: FSMContext):
    try:
        max_act = int(message.text.strip())
        if max_act <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите целое положительное число:")
        return

    data = await state.get_data()
    promo = await db.create_promo_code(data["code"], data["amount"], max_act)
    await state.clear()
    await message.answer(
        f"✅ Промокод <code>{promo.code}</code> на {promo.reward_amount:.0f} руб. (макс. {promo.max_activations} акт.) успешно создан!",
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML"
    )

# ================= РАССЫЛКА ПОЛЬЗОВАТЕЛЯМ =================

@admin_router.callback_query(F.data == "adm_broadcast")
async def cb_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    await state.set_state(BroadcastStates.waiting_for_content)
    text = (
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Отправьте текст (или фото с описанием), который вы хотите разослать всем пользователям бота:"
    )
    await call.message.edit_text(text, reply_markup=admin_kb.cancel_fsm_kb(), parse_mode="HTML")
    await call.answer()

@admin_router.message(BroadcastStates.waiting_for_content)
async def process_broadcast(message: Message, state: FSMContext):
    user_ids = await db.get_all_user_ids()
    await state.clear()

    status_msg = await message.answer(f"⏳ Рассылка запущена... Получателей: {len(user_ids)}")
    sent = 0
    blocked = 0

    for uid in user_ids:
        try:
            if message.photo:
                await message.bot.send_photo(
                    uid,
                    message.photo[-1].file_id,
                    caption=message.caption or "",
                    caption_entities=message.caption_entities
                )
            else:
                await message.bot.send_message(
                    uid,
                    message.text,
                    entities=message.entities
                )
            sent += 1
            await asyncio.sleep(0.04)  # 25 сообщений в секунду для соблюдения лимитов Telegram
        except Exception:
            blocked += 1

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"• Доставлено: <b>{sent}</b>\n"
        f"• Заблокировали бота / недоступно: <b>{blocked}</b>",
        reply_markup=admin_kb.admin_main_kb(),
        parse_mode="HTML"
    )

# ================= БЭКАП БАЗЫ ДАННЫХ =================

@admin_router.callback_query(F.data == "adm_backup")
async def cb_admin_backup(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return

    if not os.path.exists(DB_PATH):
        await call.answer("Файл базы данных еще не создан.", show_alert=True)
        return

    doc = FSInputFile(DB_PATH, filename=f"shop_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.db")
    await call.message.answer_document(
        doc,
        caption=f"💾 <b>Резервная копия базы данных</b>\nДата выгрузки: {datetime.utcnow().strftime('%d.%m.%Y %H:%M')} UTC",
        parse_mode="HTML"
    )
    await call.answer("Бэкап отправлен!", show_alert=False)
