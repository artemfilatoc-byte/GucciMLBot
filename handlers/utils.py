from contextlib import suppress



from aiogram.exceptions import TelegramBadRequest

from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from aiogram.types import User as AiogramUser



from models import User

from repositories.user import upsert_user





async def edit_callback_message(

    callback: CallbackQuery,

    text: str,

    markup: InlineKeyboardMarkup,

    notice: str | None = None,

) -> None:

    await callback.answer(notice)

    if callback.message is None:

        return

    with suppress(TelegramBadRequest):

        await callback.message.edit_text(text, reply_markup=markup)





async def upsert_callback_user(callback: CallbackQuery) -> User:

    user: AiogramUser = callback.from_user

    return await upsert_user(user.id, user.username, user.full_name)





def parse_page(data: str | None, prefix: str) -> int:

    if not data or not data.startswith(prefix):

        return 0

    try:

        return max(int(data.removeprefix(prefix)), 0)

    except ValueError:

        return 0





def parse_id(data: str | None, prefix: str) -> int:

    if not data or not data.startswith(prefix):

        return 0

    try:

        return int(data.removeprefix(prefix))

    except ValueError:

        return 0





def parse_id_and_page(data: str | None, prefix: str) -> tuple[int, int]:

    if not data or not data.startswith(prefix):

        return 0, 0

    parts = data.removeprefix(prefix).split(":", maxsplit=1)

    try:

        item_id = int(parts[0])

        page = int(parts[1]) if len(parts) > 1 else 0

    except ValueError:

        return 0, 0

    return item_id, max(page, 0)

