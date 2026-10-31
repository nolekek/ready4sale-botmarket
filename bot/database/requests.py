import random
import string
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import func, select, update, delete
from sqlalchemy.orm import selectinload
from bot.database.models import Category, Item, Order, PaymentInvoice, Product, PromoActivation, PromoCode, User
from bot.database.setup import async_session

def generate_code(prefix: str = "ORD") -> str:
    rnd = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{rnd}"

# ================= USER CRUD =================

async def get_or_create_user(telegram_id: int, username: Optional[str] = None, full_name: Optional[str] = None, referrer_id: Optional[int] = None) -> Tuple[User, bool]:
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        created = False
        if not user:
            # Предотвращаем само-реферальность
            valid_ref = referrer_id if referrer_id and referrer_id != telegram_id else None
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                referrer_id=valid_ref,
                balance=0.0
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            created = True
        else:
            # Обновляем профиль при изменениях
            if user.username != username or user.full_name != full_name:
                user.username = username
                user.full_name = full_name
                await session.commit()
        return user, created

async def get_user(telegram_id: int) -> Optional[User]:
    async with async_session() as session:
        return await session.get(User, telegram_id)

async def update_user_balance(telegram_id: int, amount_change: float) -> Optional[float]:
    """Изменение баланса (положительное или отрицательное)"""
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.balance = round(user.balance + amount_change, 2)
            if user.balance < 0:
                user.balance = 0.0
            await session.commit()
            return user.balance
        return None

async def get_referral_stats(telegram_id: int) -> Tuple[int, float]:
    """Количество приглашенных и сумма покупок рефералов"""
    async with async_session() as session:
        count_stmt = select(func.count(User.telegram_id)).where(User.referrer_id == telegram_id)
        count_res = await session.execute(count_stmt)
        ref_count = count_res.scalar() or 0
        return ref_count, 0.0

async def get_all_users_count() -> int:
    async with async_session() as session:
        res = await session.execute(select(func.count(User.telegram_id)))
        return res.scalar() or 0

async def get_all_user_ids() -> List[int]:
    async with async_session() as session:
        res = await session.execute(select(User.telegram_id))
        return [row[0] for row in res.fetchall()]

# ================= CATEGORY & PRODUCT CRUD =================

async def get_categories() -> List[Category]:
    async with async_session() as session:
        res = await session.execute(select(Category).order_by(Category.position.asc(), Category.id.asc()))
        return list(res.scalars().all())

async def get_category(category_id: int) -> Optional[Category]:
    async with async_session() as session:
        return await session.get(Category, category_id)

async def create_category(name: str) -> Category:
    async with async_session() as session:
        cat = Category(name=name)
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat

async def delete_category(category_id: int) -> bool:
    async with async_session() as session:
        cat = await session.get(Category, category_id)
        if cat:
            await session.delete(cat)
            await session.commit()
            return True
        return False

async def get_products_by_category(category_id: int) -> List[Product]:
    async with async_session() as session:
        res = await session.execute(select(Product).where(Product.category_id == category_id).order_by(Product.id.asc()))
        return list(res.scalars().all())

async def get_product(product_id: int) -> Optional[Product]:
    async with async_session() as session:
        res = await session.execute(
            select(Product).options(selectinload(Product.items)).where(Product.id == product_id)
        )
        return res.scalar_one_or_none()

async def create_product(category_id: int, name: str, description: str, price: float, product_type: str = "unique", static_content: Optional[str] = None) -> Product:
    async with async_session() as session:
        prod = Product(
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            product_type=product_type,
            static_content=static_content
        )
        session.add(prod)
        await session.commit()
        await session.refresh(prod)
        return prod

async def delete_product(product_id: int) -> bool:
    async with async_session() as session:
        prod = await session.get(Product, product_id)
        if prod:
            await session.delete(prod)
            await session.commit()
            return True
        return False

# ================= ITEM CRUD (STOCK / АВТОВЫДАЧА) =================

async def add_items_bulk(product_id: int, items_data: List[str]) -> int:
    """Добавление списка строк товара в базу"""
    async with async_session() as session:
        added_count = 0
        for data in items_data:
            clean = data.strip()
            if clean:
                session.add(Item(product_id=product_id, data=clean))
                added_count += 1
        await session.commit()
        return added_count

async def get_available_items_count(product_id: int) -> int:
    async with async_session() as session:
        res = await session.execute(
            select(func.count(Item.id)).where(Item.product_id == product_id, Item.is_sold == False)
        )
        return res.scalar() or 0

async def pop_item_for_delivery(product_id: int) -> Optional[str]:
    """Атомарная выдача штучного товара из остатков"""
    async with async_session() as session:
        # Выбираем один непроданный товар
        stmt = select(Item).where(Item.product_id == product_id, Item.is_sold == False).limit(1).with_for_update()
        res = await session.execute(stmt)
        item = res.scalar_one_or_none()
        if item:
            item.is_sold = True
            await session.commit()
            return item.data
        return None

# ================= ORDER CRUD =================

async def create_order(user_id: int, product_id: int, product_name: str, amount: float, payment_method: str, delivered_data: str) -> Order:
    async with async_session() as session:
        order = Order(
            order_code=generate_code("ORD"),
            user_id=user_id,
            product_id=product_id,
            product_name=product_name,
            amount=amount,
            payment_method=payment_method,
            delivered_data=delivered_data
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

async def get_user_orders(user_id: int, limit: int = 10) -> List[Order]:
    async with async_session() as session:
        res = await session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(limit)
        )
        return list(res.scalars().all())

async def get_orders_stats() -> dict:
    """Статистика для админки"""
    async with async_session() as session:
        total_orders = await session.scalar(select(func.count(Order.id))) or 0
        total_revenue = await session.scalar(select(func.sum(Order.amount))) or 0.0
        
        # Заказы за 24 часа
        yesterday = datetime.utcnow() - timedelta(days=1)
        orders_today = await session.scalar(select(func.count(Order.id)).where(Order.created_at >= yesterday)) or 0
        revenue_today = await session.scalar(select(func.sum(Order.amount)).where(Order.created_at >= yesterday)) or 0.0
        
        return {
            "total_orders": total_orders,
            "total_revenue": round(total_revenue, 2),
            "orders_today": orders_today,
            "revenue_today": round(revenue_today, 2)
        }

# ================= PROMOCODES =================

async def create_promo_code(code: str, reward_amount: float, max_activations: int = 1) -> PromoCode:
    async with async_session() as session:
        promo = PromoCode(
            code=code.strip().upper(),
            reward_amount=reward_amount,
            max_activations=max_activations
        )
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
        return promo

async def activate_promo_code(user_id: int, code: str) -> Tuple[bool, str, float]:
    """
    Активация промокода пользователем.
    Возвращает (успех, сообщение, начисленная_сумма)
    """
    clean_code = code.strip().upper()
    async with async_session() as session:
        res = await session.execute(select(PromoCode).where(PromoCode.code == clean_code))
        promo = res.scalar_one_or_none()
        if not promo:
            return False, "❌ Промокод не найден или неверен.", 0.0
            
        if promo.activated_count >= promo.max_activations:
            return False, "❌ Лимит активаций этого промокода исчерпан.", 0.0
            
        # Проверяем, не активировал ли уже этот пользователь
        act_res = await session.execute(
            select(PromoActivation).where(PromoActivation.promo_id == promo.id, PromoActivation.user_id == user_id)
        )
        if act_res.scalar_one_or_none():
            return False, "❌ Вы уже активировали этот промокод ранее.", 0.0
            
        # Начисляем пользователю баланс
        user = await session.get(User, user_id)
        if not user:
            return False, "❌ Ошибка пользователя.", 0.0
            
        promo.activated_count += 1
        user.balance = round(user.balance + promo.reward_amount, 2)
        
        activation = PromoActivation(promo_id=promo.id, user_id=user_id)
        session.add(activation)
        
        await session.commit()
        return True, f"✅ Промокод успешно активирован! На ваш баланс начислено {promo.reward_amount} руб.", promo.reward_amount

# ================= INVOICES (ПОПОЛНЕНИЕ БАЛАНСА) =================

async def create_payment_invoice(user_id: int, amount_rub: float, method: str, external_id: Optional[str] = None) -> PaymentInvoice:
    async with async_session() as session:
        invoice = PaymentInvoice(
            invoice_code=generate_code("INV"),
            user_id=user_id,
            amount_rub=amount_rub,
            method=method,
            external_id=external_id,
            status="pending"
        )
        session.add(invoice)
        await session.commit()
        await session.refresh(invoice)
        return invoice

async def get_invoice_by_code(code: str) -> Optional[PaymentInvoice]:
    async with async_session() as session:
        res = await session.execute(select(PaymentInvoice).where(PaymentInvoice.invoice_code == code))
        return res.scalar_one_or_none()

async def confirm_invoice_paid(invoice_id: int) -> Optional[PaymentInvoice]:
    async with async_session() as session:
        inv = await session.get(PaymentInvoice, invoice_id)
        if inv and inv.status == "pending":
            inv.status = "paid"
            # Пополняем баланс юзера
            user = await session.get(User, inv.user_id)
            if user:
                user.balance = round(user.balance + inv.amount_rub, 2)
            await session.commit()
            return inv
        return None
