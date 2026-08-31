from contextlib import suppress



from aiogram import F, Router

from aiogram.enums import ChatType

from aiogram.exceptions import TelegramBadRequest

from aiogram.filters import Command, CommandStart, Filter

from aiogram.filters.command import CommandObject

from aiogram.types import CallbackQuery, Message



from keyboards.menu import (

    MENU,

    menu_kb,

)

from repositories.access import activate_access_key, is_access_key_like

from repositories.user import upsert_user

from services.access_control import can_use_bot

from texts.access import (

    ACCESS_KEY_ACTIVATED,

    ACCESS_KEY_ALREADY_ACTIVE,

    ACCESS_KEY_INVALID,

    ACCESS_KEY_PROMPT,

    ACCESS_KEY_USED,

    ACCESS_REQUIRED_MESSAGE,

)

from texts.menu import MENU as MENU_TEXT





class AccessKeyTextFilter(Filter):

    async def __call__(self, message: Message) -> bool:

        if message.chat.type != ChatType.PRIVATE or not is_access_key_like(message.text):

            return False

        user = message.from_user

        return bool(user and not await can_use_bot(user.id))





async def cmd_start(message: Message, command: CommandObject | None = None) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    user = message.from_user

    if user is None:

        return

    key = command.args.strip() if command and command.args else None

    if key:

        await _activate_key(message, key)

        return

    await upsert_user(user.id, user.username, user.full_name)

    if await can_use_bot(user.id):

        await message.answer(MENU_TEXT, reply_markup=menu_kb())

        return

    await message.answer(ACCESS_REQUIRED_MESSAGE)





async def cmd_key(message: Message, command: CommandObject | None = None) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    key = command.args.strip() if command and command.args else None

    if not key:

        await message.answer(ACCESS_KEY_PROMPT)

        return

    await _activate_key(message, key)





async def activate_plain_key(message: Message) -> None:

    await _activate_key(message, message.text or "")





async def _activate_key(message: Message, key: str) -> None:

    user = message.from_user

    if user is None:

        return

    if not is_access_key_like(key):

        await message.answer(ACCESS_KEY_INVALID)

        return

    result = await activate_access_key(user.id, user.username, user.full_name, key)

    if result.status == "activated":

        await message.answer(

            f"{ACCESS_KEY_ACTIVATED}\n\n{MENU_TEXT}",

            reply_markup=menu_kb(),

        )

    elif result.status == "already_has_access":

        await message.answer(

            f"{ACCESS_KEY_ALREADY_ACTIVE}\n\n{MENU_TEXT}",

            reply_markup=menu_kb(),

        )

    elif result.status == "used":

        await message.answer(ACCESS_KEY_USED)

    else:

        await message.answer(ACCESS_KEY_INVALID)





async def _render(callback: CallbackQuery, text: str, markup) -> None:

    await callback.answer()

    with suppress(TelegramBadRequest):

        await callback.message.edit_text(text, reply_markup=markup)





async def open_menu(callback: CallbackQuery) -> None:

    await _render(callback, MENU_TEXT, menu_kb())





def get_router() -> Router:

    router = Router(name="start")

    router.message.register(cmd_start, CommandStart())

    router.message.register(cmd_key, Command("key"))

    router.message.register(activate_plain_key, AccessKeyTextFilter())

    router.callback_query.register(open_menu, F.data == MENU)

    return router

