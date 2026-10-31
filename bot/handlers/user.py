from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from bot.config import config
from bot.database import requests as db
from bot.keyboards import user_kb

user_router = Router(name="user_router")

class PromoStates(StatesGroup):
    waiting_for_code = State()

def format_start_text(user_name: str) -> str:
    return (
        f"👋 <b>Добро пожаловать в {config.SHOP_NAME}, {user_name}!</b>\n\n"
        "Здесь вы можете приобрести цифровые товары, подписки, ключи и услуги с <b>мгновенной автовыдачей 24/7</b>.\n\n"
        "💡 <i>Выберите интересующий раздел в меню ниже:</i>"
    )

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Обработка реферального кода из диплинка (/start ref_123456)
    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        raw_ref = args[1].replace("ref_", "")
        if raw_ref.isdigit():
            referrer_id = int(raw_ref)

    user, is_new = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        referrer_id=referrer_id
    )

    is_admin = message.from_user.id in config.ADMIN_IDS
    await message.answer(
        format_start_text(message.from_user.first_name),
        reply_markup=user_kb.main_menu_kb(is_admin),
        parse_mode="HTML"
    )

@user_router.callback_query(F.data == "to_main")
async def cb_to_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    is_admin = call.from_user.id in config.ADMIN_IDS
    try:
        await call.message.edit_text(
            format_start_text(call.from_user.first_name),
            reply_markup=user_kb.main_menu_kb(is_admin),
            parse_mode="HTML"
        )
    except Exception:
        await call.message.answer(
            format_start_text(call.from_user.first_name),
            reply_markup=user_kb.main_menu_kb(is_admin),
            parse_mode="HTML"
        )
    await call.answer()

# ================= КАТАЛОГ И ТОВАРЫ =================

@user_router.callback_query(F.data == "catalog")
async def cb_catalog(call: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await call.answer("Раздел каталога пока пуст. Ожидайте пополнения!", show_alert=True)
        return
        
    text = "📁 <b>Каталог товаров:</b>\n\nВыберите нужную категорию для просмотра доступных позиций:"
    await call.message.edit_text(text, reply_markup=user_kb.categories_kb(categories), parse_mode="HTML")
    await call.answer()

@user_router.callback_query(F.data.startswith("cat_"))
async def cb_category_products(call: CallbackQuery):
    cat_id = int(call.data.replace("cat_", ""))
    category = await db.get_category(cat_id)
    if not category:
        await call.answer("Категория не найдена.", show_alert=True)
        return

    products = await db.get_products_by_category(cat_id)
    if not products:
        await call.answer("В этой категории пока нет товаров.", show_alert=True)
        return

    items_counts = {}
    for p in products:
        if p.product_type == "unique":
            items_counts[p.id] = await db.get_available_items_count(p.id)
        else:
            items_counts[p.id] = 999  # бесконечный

    text = f"📁 <b>Категория: {category.name}</b>\n\nВыберите товар для ознакомления:"
    await call.message.edit_text(
        text,
        reply_markup=user_kb.products_kb(cat_id, products, items_counts),
        parse_mode="HTML"
    )
    await call.answer()

@user_router.callback_query(F.data.startswith("prod_"))
async def cb_product_detail(call: CallbackQuery):
    prod_id = int(call.data.replace("prod_", ""))
    product = await db.get_product(prod_id)
    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return

    stock = 999 if product.product_type == "infinite" else await db.get_available_items_count(product.id)
    is_available = stock > 0

    stock_text = "В наличии (много)" if product.product_type == "infinite" else f"{stock} шт."
    desc = product.description or "Описание отсутствует."

    text = (
        f"📦 <b>{product.name}</b>\n\n"
        f"📝 <b>Описание:</b>\n{desc}\n\n"
        f"💵 <b>Цена:</b> {product.price:.0f} {config.SHOP_CURRENCY}\n"
        f"📊 <b>Остаток:</b> {stock_text}\n"
    )

    await call.message.edit_text(
        text,
        reply_markup=user_kb.product_detail_kb(product, is_available),
        parse_mode="HTML"
    )
    await call.answer()

# ================= ПОКУПКА ЗА БАЛАНС =================

@user_router.callback_query(F.data.startswith("buy_balance_"))
async def cb_buy_balance(call: CallbackQuery):
    prod_id = int(call.data.replace("buy_balance_", ""))
    product = await db.get_product(prod_id)
    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return

    user = await db.get_user(call.from_user.id)
    if not user:
        await call.answer("Ошибка пользователя.", show_alert=True)
        return

    if user.balance < product.price:
        needed = product.price - user.balance
        await call.answer(
            f"Недостаточно средств на балансе!\nВаш баланс: {user.balance:.0f} руб.\nНе хватает: {needed:.0f} руб.\nПополните баланс в профиле.",
            show_alert=True
        )
        return

    # Проверяем наличие
    delivered_data = None
    if product.product_type == "unique":
        delivered_data = await db.pop_item_for_delivery(product.id)
        if not delivered_data:
            await call.answer("К сожалению, данный товар только что закончился!", show_alert=True)
            return
    else:
        delivered_data = product.static_content or "Товар успешно оплачен."

    # Списываем баланс
    await db.update_user_balance(user.telegram_id, -product.price)

    # Создаем заказ
    order = await db.create_order(
        user_id=user.telegram_id,
        product_id=product.id,
        product_name=product.name,
        amount=product.price,
        payment_method="balance",
        delivered_data=delivered_data
    )

    # Начисление реферального бонуса (если есть пригласивший)
    if user.referrer_id and config.REFERRAL_PERCENT > 0:
        reward = round(product.price * (config.REFERRAL_PERCENT / 100), 2)
        if reward > 0:
            await db.update_user_balance(user.referrer_id, reward)
            try:
                await call.bot.send_message(
                    user.referrer_id,
                    f"🎉 <b>Реферальный бонус!</b>\nВаш реферал совершил покупку. Вам начислено <b>+{reward} руб.</b> на баланс!",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # Отправляем товар покупателю
    success_text = (
        f"✅ <b>Заказ #{order.order_code} успешно выполнен!</b>\n\n"
        f"📦 <b>Товар:</b> {product.name}\n"
        f"💵 <b>Списано с баланса:</b> {product.price:.0f} {config.SHOP_CURRENCY}\n\n"
        f"🎁 <b>ВАШИ ДАННЫЕ / ТОВАР:</b>\n"
        f"<code>{delivered_data}</code>\n\n"
        f"<i>Спасибо за покупку! Сохраните эти данные.</i>"
    )

    await call.message.edit_text(
        success_text,
        reply_markup=user_kb.back_to_main_kb(),
        parse_mode="HTML"
    )
    await call.answer()

# ================= ПРОФИЛЬ И РЕФЕРАЛЫ =================

@user_router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    if not user:
        user, _ = await db.get_or_create_user(call.from_user.id)

    ref_count, _ = await db.get_referral_stats(user.telegram_id)

    text = (
        f"👤 <b>Личный кабинет:</b>\n\n"
        f"🆔 <b>Ваш ID:</b> <code>{user.telegram_id}</code>\n"
        f"💰 <b>Баланс:</b> <b>{user.balance:.2f} {config.SHOP_CURRENCY}</b>\n"
        f"👥 <b>Приглашено рефералов:</b> {ref_count}\n"
        f"📅 <b>Дата регистрации:</b> {user.joined_at.strftime('%d.%m.%Y')}\n"
    )

    await call.message.edit_text(text, reply_markup=user_kb.profile_kb(), parse_mode="HTML")
    await call.answer()

@user_router.callback_query(F.data == "my_orders")
async def cb_my_orders(call: CallbackQuery):
    orders = await db.get_user_orders(call.from_user.id, limit=5)
    if not orders:
        await call.answer("У вас пока нет оформленных заказов.", show_alert=True)
        return

    text = "📦 <b>Последние покупки:</b>\n\n"
    for o in orders:
        text += (
            f"🔹 <b>Заказ:</b> #{o.order_code}\n"
            f"Товар: {o.product_name} ({o.amount:.0f} руб.)\n"
            f"Дата: {o.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Выданные данные: <code>{o.delivered_data}</code>\n\n"
        )

    await call.message.edit_text(text, reply_markup=user_kb.back_to_main_kb(), parse_mode="HTML")
    await call.answer()

@user_router.callback_query(F.data == "referrals")
async def cb_referrals(call: CallbackQuery):
    bot_info = await call.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{call.from_user.id}"
    ref_count, _ = await db.get_referral_stats(call.from_user.id)

    text = (
        f"👥 <b>Партнерская программа</b>\n\n"
        f"Приглашайте друзей и получайте <b>{config.REFERRAL_PERCENT}%</b> от каждой их покупки на свой баланс!\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"• Приглашено пользователей: <b>{ref_count}</b>\n"
        f"• Бонусы начисляются на баланс автоматически при оплате покупок."
    )

    await call.message.edit_text(text, reply_markup=user_kb.back_to_main_kb(), parse_mode="HTML")
    await call.answer()

# ================= ПРОМОКОДЫ =================

@user_router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(call: CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.waiting_for_code)
    text = "🎁 <b>Активация промокода</b>\n\nОтправьте промокод сообщением в чат:"
    await call.message.edit_text(text, reply_markup=user_kb.back_to_main_kb(), parse_mode="HTML")
    await call.answer()

@user_router.message(PromoStates.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip()
    success, msg, amount = await db.activate_promo_code(message.from_user.id, code)
    await state.clear()
    
    is_admin = message.from_user.id in config.ADMIN_IDS
    await message.answer(msg, reply_markup=user_kb.main_menu_kb(is_admin))
