from collections.abc import Awaitable, Callable

from typing import Any



from aiogram import BaseMiddleware

from aiogram.enums import ChatType

from aiogram.types import CallbackQuery, Message, TelegramObject

from aiogram.types import User as AiogramUser



from repositories.access import is_access_key_like

from services.access_control import can_use_bot

from texts.access import ACCESS_REQUIRED_ALERT, ACCESS_REQUIRED_MESSAGE





class AccessMiddleware(BaseMiddleware):

    async def __call__(

        self,

        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],

        event: TelegramObject,

        data: dict[str, Any],

    ) -> Any:

        user = self._get_user(event)

        if user is None:

            return await handler(event, data)

        if await can_use_bot(user.id):

            return await handler(event, data)

        if self._is_allowed_activation_event(event):

            return await handler(event, data)

        if isinstance(event, CallbackQuery):

            await event.answer(ACCESS_REQUIRED_ALERT, show_alert=True)

            return None

        if isinstance(event, Message):

            await event.answer(ACCESS_REQUIRED_MESSAGE)

            return None

        return await handler(event, data)



    @staticmethod

    def _get_user(event: TelegramObject) -> AiogramUser | None:

        if isinstance(event, Message):

            return event.from_user

        if isinstance(event, CallbackQuery):

            return event.from_user

        return None



    @staticmethod

    def _is_allowed_activation_event(event: TelegramObject) -> bool:

        if isinstance(event, CallbackQuery):

            return False

        if not isinstance(event, Message):

            return False

        if event.chat.type != ChatType.PRIVATE:

            return True

        text = (event.text or "").strip()

        if not text:

            return False

        command = text.split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower()

        return command in {"/start", "/key", "/admin"} or is_access_key_like(text)

