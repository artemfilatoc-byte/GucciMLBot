from contextlib import suppress



from aiogram import Bot, F, Router

from aiogram.enums import ChatType

from aiogram.exceptions import TelegramBadRequest

from aiogram.filters import Command

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from aiogram.types import CallbackQuery, Message



from keyboards.admin import (

    ADMIN_BROADCAST,

    ADMIN_BROADCAST_CANCEL,

    ADMIN_CREATE_KEY,

    ADMIN_KEY_DELETE_PREFIX,

    ADMIN_KEYS_LIST,

    ADMIN_KEYS_PAGE_PREFIX,

    ADMIN_REFRESH,

    ADMIN_USER_REVOKE_PREFIX,

    ADMIN_USERS_LIST,

    ADMIN_USERS_PAGE_PREFIX,

    admin_broadcast_cancel_kb,

    admin_key_delete_confirm_kb,

    admin_keys_kb,

    admin_kb,

    admin_user_revoke_confirm_kb,

    admin_users_kb,

)

from repositories.access import (

    create_access_key,

    deactivate_access_key,

    delete_access_key,

    get_access_key,

    get_access_stats,

    list_access_keys,

)

from repositories.user import list_users_with_access, revoke_user_access

from services.access_control import is_admin_id

from services.background import spawn_background_task

from texts.access import (

    ADMIN_BROADCAST_CANCELLED,

    ADMIN_BROADCAST_EMPTY,

    ADMIN_BROADCAST_PROMPT,

    ADMIN_BROADCAST_STARTED,

    ADMIN_DENIED,

    format_access_key_created,

    format_admin_panel,

    format_broadcast_done,

    format_key_card,

    format_keys_list,

    format_user_card,

    format_users_list,

)





async def cmd_admin(message: Message) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    user = message.from_user

    if user is None or not is_admin_id(user.id):

        await message.answer(ADMIN_DENIED)

        return

    await message.answer(

        format_admin_panel(await get_access_stats()),

        reply_markup=admin_kb(),

    )





async def refresh_admin(callback: CallbackQuery) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    await callback.answer()

    if callback.message is None:

        return

    with suppress(TelegramBadRequest):

        await callback.message.edit_text(

            format_admin_panel(await get_access_stats()),

            reply_markup=admin_kb(),

        )





async def create_key(callback: CallbackQuery) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    result = await create_access_key(callback.from_user.id)

    await callback.answer("Ключ создан.")

    if callback.message is not None:

        await callback.message.answer(format_access_key_created(result.key))

        with suppress(TelegramBadRequest):

            await callback.message.edit_text(

                format_admin_panel(await get_access_stats()),

                reply_markup=admin_kb(),

            )





class AdminBroadcastState(StatesGroup):

    waiting_text = State()





async def open_keys_list(callback: CallbackQuery) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    page = 0

    if callback.data.startswith(ADMIN_KEYS_PAGE_PREFIX):

        try:

            page = int(callback.data.removeprefix(ADMIN_KEYS_PAGE_PREFIX))

        except ValueError:

            page = 0

    keys, has_next = await list_access_keys(page, 6)

    has_prev = page > 0

    text = format_keys_list(page, bool(keys))

    if callback.message is None:

        return

    with suppress(TelegramBadRequest):

        await callback.message.edit_text(text, reply_markup=admin_keys_kb(keys, page, has_prev, has_next))

    await callback.answer()





async def open_key_card(callback: CallbackQuery) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

                                                           

    raw = callback.data.removeprefix(ADMIN_KEY_DELETE_PREFIX)

    is_confirm = raw.endswith(":confirm")

    if is_confirm:

        raw = raw.removesuffix(":confirm")

    try:

        key_id_str, page_str = raw.split(":", 1)

        key_id = int(key_id_str)

        page = int(page_str)

    except ValueError:

        await callback.answer("Ошибка", show_alert=True)

        return

    if is_confirm:

        ok = await delete_access_key(key_id)

        await callback.answer("Удален" if ok else "Не найден", show_alert=True)

        keys, has_next = await list_access_keys(page, 6)

                              

        if not keys and page > 0:

            page -= 1

            keys, has_next = await list_access_keys(page, 6)

        has_prev = page > 0

        text = format_keys_list(page, bool(keys))

        if callback.message:

            with suppress(TelegramBadRequest):

                await callback.message.edit_text(text, reply_markup=admin_keys_kb(keys, page, has_prev, has_next))

        return

    key = await get_access_key(key_id)

    if key is None:

        await callback.answer("Ключ не найден", show_alert=True)

        return

    await callback.answer()

    if callback.message:

        with suppress(TelegramBadRequest):

            await callback.message.edit_text(format_key_card(key), reply_markup=admin_key_delete_confirm_kb(key_id, page))





async def open_users_list(callback: CallbackQuery) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    page = 0

    if callback.data.startswith(ADMIN_USERS_PAGE_PREFIX):

        try:

            page = int(callback.data.removeprefix(ADMIN_USERS_PAGE_PREFIX))

        except ValueError:

            page = 0

    users, has_next = await list_users_with_access(page, 6)

    has_prev = page > 0

    text = format_users_list(page, bool(users))

    if callback.message is None:

        return

    with suppress(TelegramBadRequest):

        await callback.message.edit_text(text, reply_markup=admin_users_kb(users, page, has_prev, has_next))

    await callback.answer()





async def open_user_card(callback: CallbackQuery) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    raw = callback.data.removeprefix(ADMIN_USER_REVOKE_PREFIX)

    is_confirm = raw.endswith(":confirm")

    if is_confirm:

        raw = raw.removesuffix(":confirm")

    try:

        tid_str, page_str = raw.split(":", 1)

        telegram_id = int(tid_str)

        page = int(page_str)

    except ValueError:

        await callback.answer("Ошибка", show_alert=True)

        return

    if is_confirm:

        ok = await revoke_user_access(telegram_id)

        await callback.answer("Доступ отозван" if ok else "Уже нет доступа", show_alert=True)

        users, has_next = await list_users_with_access(page, 6)

        if not users and page > 0:

            page -= 1

            users, has_next = await list_users_with_access(page, 6)

        has_prev = page > 0

        text = format_users_list(page, bool(users))

        if callback.message:

            with suppress(TelegramBadRequest):

                await callback.message.edit_text(text, reply_markup=admin_users_kb(users, page, has_prev, has_next))

        return

                       

    from repositories.user import get_user_by_telegram_id



    user = await get_user_by_telegram_id(telegram_id)

    if user is None:

        await callback.answer("Пользователь не найден", show_alert=True)

        return

    await callback.answer()

    if callback.message:

        with suppress(TelegramBadRequest):

            await callback.message.edit_text(format_user_card(user), reply_markup=admin_user_revoke_confirm_kb(telegram_id, page))





async def request_broadcast(callback: CallbackQuery, state: FSMContext) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    await state.set_state(AdminBroadcastState.waiting_text)

    await callback.answer()

    if callback.message:

        with suppress(TelegramBadRequest):

            await callback.message.edit_text(ADMIN_BROADCAST_PROMPT, reply_markup=admin_broadcast_cancel_kb())

    else:

        await callback.message.answer(ADMIN_BROADCAST_PROMPT, reply_markup=admin_broadcast_cancel_kb())





async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:

    if not is_admin_id(callback.from_user.id):

        await callback.answer(ADMIN_DENIED, show_alert=True)

        return

    await state.clear()

    await callback.answer()

    if callback.message:

        with suppress(TelegramBadRequest):

            await callback.message.edit_text(ADMIN_BROADCAST_CANCELLED, reply_markup=admin_kb())

            await callback.message.edit_text(format_admin_panel(await get_access_stats()), reply_markup=admin_kb())





async def process_broadcast(message: Message, state: FSMContext, bot: Bot) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if not is_admin_id(message.from_user.id if message.from_user else 0):

        await message.answer(ADMIN_DENIED)

        return

                                               

    text = (message.text or message.caption or "").strip()

    if not text:

                                         

        await message.answer(ADMIN_BROADCAST_EMPTY, reply_markup=admin_broadcast_cancel_kb())

        return

                                                               

    broadcast_text = message.html_text or text

    await state.clear()

    status_msg = await message.answer(ADMIN_BROADCAST_STARTED)



    async def run_broadcast() -> None:

        from services.broadcast import broadcast_to_all



        stats = await broadcast_to_all(bot, broadcast_text, message.from_user.id if message.from_user else None)

        try:

            await bot.edit_message_text(

                chat_id=status_msg.chat.id,

                message_id=status_msg.message_id,

                text=format_broadcast_done(stats),

            )

        except Exception:

            await bot.send_message(status_msg.chat.id, format_broadcast_done(stats))



    spawn_background_task(run_broadcast())





def get_router() -> Router:

    router = Router(name="admin")

    router.message.register(cmd_admin, Command("admin"))

    router.callback_query.register(create_key, F.data == ADMIN_CREATE_KEY)

    router.callback_query.register(refresh_admin, F.data == ADMIN_REFRESH)

    router.callback_query.register(open_keys_list, F.data == ADMIN_KEYS_LIST)

    router.callback_query.register(open_keys_list, F.data.startswith(ADMIN_KEYS_PAGE_PREFIX))

    router.callback_query.register(open_key_card, F.data.startswith(ADMIN_KEY_DELETE_PREFIX))

    router.callback_query.register(open_users_list, F.data == ADMIN_USERS_LIST)

    router.callback_query.register(open_users_list, F.data.startswith(ADMIN_USERS_PAGE_PREFIX))

    router.callback_query.register(open_user_card, F.data.startswith(ADMIN_USER_REVOKE_PREFIX))

    router.callback_query.register(request_broadcast, F.data == ADMIN_BROADCAST)

    router.callback_query.register(cancel_broadcast, F.data == ADMIN_BROADCAST_CANCEL)

    router.message.register(process_broadcast, AdminBroadcastState.waiting_text)

    return router

