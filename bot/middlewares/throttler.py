import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 0.5):
        self.limit = limit
        self.users: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user:
            now = time.time()
            last_time = self.users.get(user.id, 0)
            if now - last_time < self.limit:
                # Игнорируем частые повторные нажатия
                return None
            self.users[user.id] = now
            
        return await handler(event, data)
