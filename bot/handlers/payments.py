from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ContentType, LabeledPrice, Message, PreCheckoutQuery
from bot.config import config
from bot.database import requests as db
from bot.keyboards import user_kb
from bot.services.cryptobot import crypto_service

payments_router = Router(name="payments_router")

class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()

# ================= НАЧАЛО ПОПОЛНЕНИЯ =================

@payments_router.callback_query(F.data == "deposit_start")
async def cb_deposit_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(DepositStates.waiting_for_amount)
    text = (
        "💳 <b>Пополнение баланса</b>\n\n"
        "Введите желаемую сумму пополнения в рублях (например, <code>250</code>):"
    )
    await call.message.edit_text(text, reply_markup=user_kb.back_to_main_kb(), parse_mode="HTML")
    await call.answer()

@payments_router.message(DepositStates.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    text = message.text.strip().replace(",", ".")
    try:
        amount = float(text)
        if amount < 10:
            await message.answer("Минимальная сумма пополнения — 10 руб. Попробуйте снова:")
            return
        if amount > 100000:
            await message.answer("Слишком большая сумма. Максимум 100 000 руб.")
            return
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например, 250):")
        return

    await state.update_data(deposit_amount=amount)
    
    text_info = (
        f"💳 <b>Пополнение на сумму: {amount:.0f} {config.SHOP_CURRENCY}</b>\n\n"
        "Выберите удобный способ оплаты:"
    )
    await message.answer(text_info, reply_markup=user_kb.deposit_methods_kb(amount), parse_mode="HTML")

# ================= 1. ОПЛАТА ЧЕРЕЗ TELEGRAM STARS =================

@payments_router.callback_query(F.data.startswith("pay_stars_"))
async def cb_pay_stars(call: CallbackQuery, state: FSMContext):
    amount_rub = float(call.data.replace("pay_stars_", ""))
    stars_amount = max(1, int(amount_rub / config.STAR_RATE_RUB))
    
    invoice = await db.create_payment_invoice(call.from_user.id, amount_rub, method="stars")

    prices = [LabeledPrice(label="Пополнение баланса", amount=stars_amount)]
    
    await call.bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"Пополнение баланса на {amount_rub:.0f} руб.",
        description=f"Оплата цифровых товаров в {config.SHOP_NAME} за Telegram Stars.",
        payload=f"stars_{invoice.id}_{amount_rub}",
        currency="XTR",
        prices=prices,
        provider_token=""  # Для Telegram Stars provider_token всегда пустой
    )
    await call.answer()

@payments_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@payments_router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    # payload вида stars_{invoice_id}_{amount_rub}
    if payload.startswith("stars_"):
        parts = payload.split("_")
        invoice_id = int(parts[1])
        amount_rub = float(parts[2])
        
        await db.confirm_invoice_paid(invoice_id)
        
        is_admin = message.from_user.id in config.ADMIN_IDS
        await message.answer(
            f"🎉 <b>Оплата Telegram Stars успешно получена!</b>\n"
            f"На ваш баланс зачислено: <b>+{amount_rub:.0f} руб.</b>",
            reply_markup=user_kb.main_menu_kb(is_admin),
            parse_mode="HTML"
        )

# ================= 2. ОПЛАТА ЧЕРЕЗ CRYPTOBOT =================

@payments_router.callback_query(F.data.startswith("pay_crypto_"))
async def cb_pay_crypto(call: CallbackQuery):
    amount_rub = float(call.data.replace("pay_crypto_", ""))
    
    invoice_data = await crypto_service.create_invoice(
        amount=amount_rub,
        fiat_currency="RUB",
        description=f"Пополнение в {config.SHOP_NAME}"
    )
    
    if not invoice_data:
        await call.answer("Сервис CryptoPay временно недоступен. Выберите другой метод.", show_alert=True)
        return

    ext_id = str(invoice_data["invoice_id"])
    invoice = await db.create_payment_invoice(call.from_user.id, amount_rub, method="cryptobot", external_id=ext_id)

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Перейти к оплате в CryptoBot", url=invoice_data["pay_url"])],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_crypto_{invoice.id}_{ext_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="profile")]
    ])

    text = (
        f"💎 <b>Оплата через CryptoBot</b>\n\n"
        f"Сумма к оплате: <b>{amount_rub:.0f} руб.</b>\n"
        f"Номер счета: <code>#{ext_id}</code>\n\n"
        "Нажмите кнопку ниже для перехода к оплате в боте CryptoBot. "
        "После перевода средств нажмите <b>«Проверить оплату»</b>."
    )
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()

@payments_router.callback_query(F.data.startswith("check_crypto_"))
async def cb_check_crypto(call: CallbackQuery):
    parts = call.data.split("_")
    invoice_id = int(parts[2])
    ext_id = int(parts[3])
    
    is_paid = await crypto_service.check_invoice_paid(ext_id)
    if is_paid:
        inv = await db.confirm_invoice_paid(invoice_id)
        if inv:
            is_admin = call.from_user.id in config.ADMIN_IDS
            await call.message.edit_text(
                f"🎉 <b>Оплата криптовалютой подтверждена!</b>\nНа ваш баланс зачислено: <b>+{inv.amount_rub:.0f} руб.</b>",
                reply_markup=user_kb.main_menu_kb(is_admin),
                parse_mode="HTML"
            )
        else:
            await call.answer("Платеж уже был обработан.", show_alert=True)
    else:
        await call.answer("Оплата пока не поступила в блокчейн. Подождите 1-2 минуты и проверьте снова.", show_alert=True)

# ================= 3. РУЧНОЙ ПЕРЕВОД (СБП / КАРТА) =================

@payments_router.callback_query(F.data.startswith("pay_sbp_"))
async def cb_pay_sbp(call: CallbackQuery, state: FSMContext):
    amount_rub = float(call.data.replace("pay_sbp_", ""))
    invoice = await db.create_payment_invoice(call.from_user.id, amount_rub, method="sbp_manual")

    await state.update_data(active_invoice_id=invoice.id, active_amount=amount_rub)
    await state.set_state(DepositStates.waiting_for_receipt)

    text = (
        f"💳 <b>Перевод по СБП / Карте РФ</b>\n\n"
        f"Сумма к переводу: <b>{amount_rub:.0f} {config.SHOP_CURRENCY}</b>\n\n"
        f"Реквизиты:\n<code>{config.SBP_REQUISITES}</code>\n\n"
        f"⚠️ <b>Внимание:</b> Переведите точную сумму, после чего <b>отправьте скриншот/фото чека</b> прямо в этот диалог."
    )
    await call.message.edit_text(text, reply_markup=user_kb.back_to_main_kb(), parse_mode="HTML")
    await call.answer()

@payments_router.message(DepositStates.waiting_for_receipt, F.photo | F.document)
async def process_payment_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    invoice_id = data.get("active_invoice_id")
    amount = data.get("active_amount", 0)
    await state.clear()

    # Оповещаем администраторов о новом чеке
    admin_text = (
        f"🔔 <b>Новая заявка на пополнение по СБП!</b>\n\n"
        f"👤 Покупатель: @{message.from_user.username or 'без_юзернейма'} (ID: <code>{message.from_user.id}</code>)\n"
        f"💰 Заявленная сумма: <b>{amount:.0f} руб.</b>\n"
        f"🆔 Инвойс ID: #{invoice_id}\n\n"
        f"<i>Проверьте поступление средств в банковском приложении и нажмите кнопку действия:</i>"
    )

    for admin_id in config.ADMIN_IDS:
        try:
            if message.photo:
                await message.bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=admin_text,
                    reply_markup=user_kb.admin_receipt_action_kb(invoice_id),
                    parse_mode="HTML"
                )
            elif message.document:
                await message.bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=admin_text,
                    reply_markup=user_kb.admin_receipt_action_kb(invoice_id),
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Error forwarding receipt to admin {admin_id}: {e}")

    is_admin = message.from_user.id in config.ADMIN_IDS
    await message.answer(
        "✅ <b>Чек успешно принят в обработку!</b>\n\n"
        "Администратор проверит зачисление в течение 5-15 минут, и ваш баланс будет пополнен автоматически.",
        reply_markup=user_kb.main_menu_kb(is_admin),
        parse_mode="HTML"
    )

# ================= ДЕЙСТВИЯ АДМИНИСТРАТОРА С ЧЕКОМ =================

@payments_router.callback_query(F.data.startswith("adm_confirm_pay_"))
async def cb_admin_confirm_payment(call: CallbackQuery):
    if call.from_user.id not in config.ADMIN_IDS:
        await call.answer("Доступ запрещен.", show_alert=True)
        return

    invoice_id = int(call.data.replace("adm_confirm_pay_", ""))
    inv = await db.confirm_invoice_paid(invoice_id)
    if inv:
        # Уведомляем пользователя
        try:
            await call.bot.send_message(
                inv.user_id,
                f"🎉 <b>Ваш платеж подтвержден!</b>\nНа ваш баланс зачислено: <b>+{inv.amount_rub:.0f} руб.</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass

        await call.message.edit_caption(
            caption=(call.message.caption or "") + f"\n\n✅ <b>ПОДТВЕРЖДЕНО администратором {call.from_user.first_name}</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
        await call.answer("Баланс пользователя успешно пополнен!", show_alert=True)
    else:
        await call.answer("Этот счет уже был подтвержден или отменен.", show_alert=True)

@payments_router.callback_query(F.data.startswith("adm_reject_pay_"))
async def cb_admin_reject_payment(call: CallbackQuery):
    if call.from_user.id not in config.ADMIN_IDS:
        await call.answer("Доступ запрещен.", show_alert=True)
        return

    invoice_id = int(call.data.replace("adm_reject_pay_", ""))
    await call.message.edit_caption(
        caption=(call.message.caption or "") + f"\n\n❌ <b>ОТКЛОНЕНО администратором {call.from_user.first_name}</b>",
        reply_markup=None,
        parse_mode="HTML"
    )
    await call.answer("Заявка отклонена.", show_alert=True)
