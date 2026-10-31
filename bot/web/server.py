import json
import os
from aiohttp import web
from bot.config import config
from bot.database import requests as db

WEBAPP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "webapp")

def json_response(data, status=200):
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        status=status,
        content_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

async def handle_options(request):
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

# 1. API Init — загрузка данных для Mini App
async def api_init(request):
    user_id = request.query.get("user_id")
    user_data = None
    if user_id and user_id.isdigit():
        uid = int(user_id)
        u = await db.get_user(uid)
        if not u:
            u, _ = await db.get_or_create_user(uid)
        ref_count, _ = await db.get_referral_stats(uid)
        user_data = {
            "id": u.telegram_id,
            "full_name": u.full_name or "Покупатель",
            "username": u.username or "",
            "balance": round(u.balance, 2),
            "referrals": ref_count
        }

    categories = await db.get_categories()
    cat_list = [{"id": c.id, "name": c.name} for c in categories]

    # Товары
    all_prods = []
    for c in categories:
        prods = await db.get_products_by_category(c.id)
        for p in prods:
            stock = 999 if p.product_type == "infinite" else await db.get_available_items_count(p.id)
            all_prods.append({
                "id": p.id,
                "category_id": p.category_id,
                "category_name": c.name,
                "name": p.name,
                "description": p.description,
                "price": round(p.price, 2),
                "product_type": p.product_type,
                "stock": stock
            })

    return json_response({
        "shop_name": config.SHOP_NAME,
        "star_rate": config.STAR_RATE_RUB,
        "user": user_data,
        "categories": cat_list,
        "products": all_prods
    })

# 2. API Buy — покупка прямо из Mini App
async def api_buy(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "Неверный формат запроса"}, 400)

    user_id = body.get("user_id")
    prod_id = body.get("product_id")

    if not user_id or not prod_id:
        return json_response({"ok": False, "error": "Отсутствуют обязательные поля"}, 400)

    user = await db.get_user(int(user_id))
    product = await db.get_product(int(prod_id))

    if not user or not product:
        return json_response({"ok": False, "error": "Товар или пользователь не найден"}, 404)

    if user.balance < product.price:
        return json_response({"ok": False, "error": "Недостаточно средств на балансе"}, 400)

    # Выдача товара
    delivered_data = None
    if product.product_type == "unique":
        delivered_data = await db.pop_item_for_delivery(product.id)
        if not delivered_data:
            return json_response({"ok": False, "error": "Товар закончился"}, 400)
    else:
        delivered_data = product.static_content or "Товар успешно оплачен."

    # Списание средств
    new_balance = await db.update_user_balance(user.telegram_id, -product.price)

    # Создание заказа
    order = await db.create_order(
        user_id=user.telegram_id,
        product_id=product.id,
        product_name=product.name,
        amount=product.price,
        payment_method="webapp_balance",
        delivered_data=delivered_data
    )

    # Реферальный бонус
    if user.referrer_id and config.REFERRAL_PERCENT > 0:
        reward = round(product.price * (config.REFERRAL_PERCENT / 100), 2)
        if reward > 0:
            await db.update_user_balance(user.referrer_id, reward)

    return json_response({
        "ok": True,
        "order_code": order.order_code,
        "delivered_data": delivered_data,
        "new_balance": new_balance
    })

# 3. API Promo — активация промокода
async def api_promo(request):
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "Неверный формат"}, 400)

    user_id = body.get("user_id")
    code = body.get("code")

    if not user_id or not code:
        return json_response({"ok": False, "error": "Укажите промокод"}, 400)

    success, msg, amount = await db.activate_promo_code(int(user_id), code)
    if success:
        user = await db.get_user(int(user_id))
        return json_response({
            "ok": True,
            "message": msg,
            "new_balance": round(user.balance, 2)
        })
    else:
        return json_response({"ok": False, "error": msg}, 400)

# 4. API Orders — список покупок
async def api_orders(request):
    user_id = request.query.get("user_id")
    if not user_id or not user_id.isdigit():
        return json_response([])

    orders = await db.get_user_orders(int(user_id), limit=15)
    result = [{
        "order_code": o.order_code,
        "product_name": o.product_name,
        "amount": round(o.amount, 2),
        "delivered_data": o.delivered_data,
        "created_at": o.created_at.strftime("%d.%m.%Y %H:%M")
    } for o in orders]

    return json_response(result)

def create_web_app():
    app = web.Application()
    
    # API эндпоинты
    app.router.add_route("OPTIONS", "/api/{tail:.*}", handle_options)
    app.router.add_get("/api/init", api_init)
    app.router.add_post("/api/buy", api_buy)
    app.router.add_post("/api/promo", api_promo)
    app.router.add_get("/api/orders", api_orders)

    # Статика Mini App
    app.router.add_static("/", path=WEBAPP_DIR, show_index=True)

    return app
