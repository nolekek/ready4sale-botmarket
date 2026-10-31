import aiohttp
from typing import Optional, Dict, Any
from bot.config import config

CRYPTO_API_URL = "https://pay.crypt.bot/api"

class CryptoBotService:
    def __init__(self, token: str):
        self.token = token
        self.headers = {"Crypto-Pay-API-Token": token}

    async def create_invoice(self, amount: float, fiat_currency: str = "RUB", description: str = "Пополнение баланса") -> Optional[Dict[str, Any]]:
        """
        Создание счета в CryptoBot с автоматической конвертацией из фиата (RUB).
        Возвращает словарь с bot_invoice_url и invoice_id.
        """
        if not self.token:
            return None
            
        endpoint = f"{CRYPTO_API_URL}/createInvoice"
        payload = {
            "amount": str(round(amount, 2)),
            "currency_type": "fiat",
            "fiat": fiat_currency,
            "description": description,
            "accepted_assets": "USDT,TON,BTC,ETH,TRX",
            "expires_in": 3600  # 1 час на оплату
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=self.headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok"):
                            result = data.get("result", {})
                            return {
                                "invoice_id": result.get("invoice_id"),
                                "pay_url": result.get("bot_invoice_url") or result.get("mini_app_invoice_url"),
                                "status": result.get("status")
                            }
        except Exception as e:
            print(f"[CryptoBot] Error creating invoice: {e}")
        return None

    async def check_invoice_paid(self, invoice_id: int) -> bool:
        """Проверка статуса оплаты инвойса"""
        if not self.token:
            return False
            
        endpoint = f"{CRYPTO_API_URL}/getInvoices"
        params = {"invoice_ids": str(invoice_id)}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, params=params, headers=self.headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("ok") and data.get("result", {}).get("items"):
                            item = data["result"]["items"][0]
                            return item.get("status") == "paid"
        except Exception as e:
            print(f"[CryptoBot] Error checking invoice {invoice_id}: {e}")
        return False

crypto_service = CryptoBotService(config.CRYPTOBOT_TOKEN)
