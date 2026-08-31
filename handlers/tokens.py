import asyncio

from dataclasses import dataclass



from aiogram import Bot, F, Router

from aiogram.enums import ChatType

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message



from handlers.utils import (

    edit_callback_message,

    parse_id,

    parse_id_and_page,

    parse_page,

    upsert_callback_user,

)

from keyboards.menu import (

    BULK_AVATAR,

    BULK_AVATAR_BATCH_PREFIX,

    BULK_AVATAR_CANCEL,

    CREATE_TOKENS,

    MY_TOKENS,

    MY_TOKENS_DELETE_ALL,

    MY_TOKENS_DELETE_ALL_CONFIRM,

    MY_TOKENS_EXPORT,

    MY_TOKENS_PAGE_PREFIX,

    MY_TOKEN_DELETE_PREFIX,

    MY_TOKEN_EDIT_PREFIX,

    MY_TOKEN_OPEN_PREFIX,

    TOKEN_BATCH_EXPORT_PREFIX,

    TOKEN_BATCH_PAGE_PREFIX,

    TOKEN_BATCH_STOP_PREFIX,

    TOKEN_CREATE_AVATAR_NO,

    TOKEN_CREATE_AVATAR_YES,

    TOKEN_CREATE_CANCEL,

    TOKEN_EDIT_AVATAR_PREFIX,

    TOKEN_EDIT_DESCRIPTION_PREFIX,

    TOKEN_EDIT_MENU_BUTTON_PREFIX,

    TOKEN_EDIT_NAME_PREFIX,

    TOKEN_EDIT_SHORT_DESCRIPTION_PREFIX,

    back_kb,

    bulk_avatar_cancel_kb,

    my_token_card_kb,

    my_tokens_delete_all_confirm_kb,

    my_tokens_kb,

    token_edit_back_kb,

    token_edit_kb,

    token_batch_result_kb,

    token_create_avatar_choice_kb,

    token_create_cancel_kb,

    token_create_progress_kb,

)

from models import TokenCreateBatchItem

from repositories.account import count_accounts

from repositories.token_batch import (

    TokenBatchCreatePayload,

    TokenBatchItemPayload,

    create_running_token_batch,

    decode_batch_base_usernames,

    decode_batch_extra_usernames,

    finish_token_batch,

    get_token_batch,

    is_token_batch_stop_requested,

    list_resumable_token_batches,

    list_token_batch_created_items,

    list_token_batch_failed_items,

    list_token_batch_items,

    list_token_batch_tokens,

    request_stop_token_batch,

    upsert_token_batch_item,

)

from repositories.created_bot import (

    delete_all_created_bots,

    delete_created_bot,

    get_created_bot,

    list_created_bot_tokens,

    list_created_bots,

    update_created_bot_name,

)

from repositories.user import upsert_user

from services.background import spawn_background_task

from services.bot_editor import (

    parse_menu_button_input,

    set_created_bot_avatar,

    set_created_bot_description,

    set_created_bot_menu_button,

    set_created_bot_name,

    set_created_bot_short_description,

)

from services.bot_creator import (

    BotBatchCreateResult,

    BotBatchItem,

    BotBatchProgress,

    build_bot_display_name,

    create_bots_via_botfather,

    normalize_base_usernames,

    normalize_bot_count,

    normalize_bot_name,

    normalize_extra_usernames,

)

from texts.tokens import (

    BULK_AVATAR_BATCH_NO_TOKENS,

    BULK_AVATAR_DONE,

    BULK_AVATAR_NO_TOKENS,

    BULK_AVATAR_PROGRESS,

    BULK_AVATAR_PROMPT,

    BULK_AVATAR_REQUIRED,

    TOKEN_BASE_USERNAME_PROMPT,

    TOKEN_AVATAR_PROMPT,

    TOKEN_BATCH_NOT_FOUND,

    TOKEN_BATCH_STOP_NOT_RUNNING,

    TOKEN_BATCH_STOP_REQUESTED,

    TOKEN_COUNT_PROMPT,

    TOKEN_CREATE_CANCELLED,

    TOKEN_EXTRA_USERNAMES_PROMPT,

    TOKEN_NAME_PROMPT,

    TOKEN_NO_ACCOUNTS,

    TOKEN_NOT_FOUND,

    TOKENS_DELETE_ALL_CONFIRM,

    TOKENS_DELETE_ALL_EMPTY,

    TOKEN_DELETED,

    TOKEN_EDIT_AVATAR_PROMPT,

    TOKEN_EDIT_AVATAR_REQUIRED,

    TOKEN_EDIT_DESCRIPTION_PROMPT,

    TOKEN_EDIT_INVALID_STATE,

    TOKEN_EDIT_MENU_BUTTON_PROMPT,

    TOKEN_EDIT_NAME_PROMPT,

    TOKEN_EDIT_SHORT_DESCRIPTION_PROMPT,

    format_bot_create_error,

    format_created_bot_button,

    format_created_bot_card,

    format_token_edit_error,

    format_token_edit_menu,

    format_token_edit_success,

    format_token_edit_wait,

    format_my_tokens_list,

    format_token_create_progress,

    format_token_create_queued,

    format_token_batch_page,

)



MY_TOKENS_PER_PAGE = 6

TOKEN_BATCH_PER_PAGE = 20





class TokenCreateState(StatesGroup):

    waiting_avatar_choice = State()

    waiting_name = State()

    waiting_base_username = State()

    waiting_count = State()

    waiting_extra_usernames = State()





class TokenEditState(StatesGroup):

    waiting_avatar = State()

    waiting_name = State()

    waiting_description = State()

    waiting_short_description = State()

    waiting_menu_button = State()





class BulkAvatarState(StatesGroup):

    waiting_photo = State()





@dataclass(frozen=True)

class TokenEditData:

    created_bot_id: int

    page: int

    owner_user_id: int

    bot_token: str





async def open_create_tokens(callback: CallbackQuery, state: FSMContext) -> None:

    owner = await upsert_callback_user(callback)

    if await count_accounts(owner.id) < 1:

        await callback.answer(TOKEN_NO_ACCOUNTS, show_alert=True)

        return

    await state.clear()

    await state.set_state(TokenCreateState.waiting_avatar_choice)

    await edit_callback_message(

        callback,

        TOKEN_AVATAR_PROMPT,

        token_create_avatar_choice_kb(),

    )





async def choose_create_avatars(callback: CallbackQuery, state: FSMContext) -> None:

    set_avatars = callback.data == TOKEN_CREATE_AVATAR_YES

    await state.update_data(set_avatars=set_avatars)

    await state.set_state(TokenCreateState.waiting_name)

    await edit_callback_message(callback, TOKEN_NAME_PROMPT, token_create_cancel_kb())





async def receive_bot_name(message: Message, state: FSMContext) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if message.text is None:

        await message.answer(TOKEN_NAME_PROMPT, reply_markup=token_create_cancel_kb())

        return

    try:

        bot_name = normalize_bot_name(message.text)

    except RuntimeError as exc:

        await message.answer(str(exc), reply_markup=token_create_cancel_kb())

        return

    await state.update_data(name=bot_name)

    await state.set_state(TokenCreateState.waiting_base_username)

    await message.answer(TOKEN_BASE_USERNAME_PROMPT, reply_markup=token_create_cancel_kb())





async def receive_base_username(message: Message, state: FSMContext) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if message.text is None:

        await message.answer(

            TOKEN_BASE_USERNAME_PROMPT,

            reply_markup=token_create_cancel_kb(),

        )

        return

    try:

        base_usernames = normalize_base_usernames(message.text)

    except RuntimeError as exc:

        await message.answer(str(exc), reply_markup=token_create_cancel_kb())

        return

    await state.update_data(base_usernames=base_usernames)

    await state.set_state(TokenCreateState.waiting_count)

    await message.answer(TOKEN_COUNT_PROMPT, reply_markup=token_create_cancel_kb())





async def receive_token_count(message: Message, state: FSMContext) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if message.text is None:

        await message.answer(TOKEN_COUNT_PROMPT, reply_markup=token_create_cancel_kb())

        return

    try:

        amount = normalize_bot_count(int(message.text.strip()))

    except ValueError:

        await message.answer("Отправь число.", reply_markup=token_create_cancel_kb())

        return

    except RuntimeError as exc:

        await message.answer(str(exc), reply_markup=token_create_cancel_kb())

        return

    await state.update_data(amount=amount)

    await state.set_state(TokenCreateState.waiting_extra_usernames)

    await message.answer(

        TOKEN_EXTRA_USERNAMES_PROMPT,

        reply_markup=token_create_cancel_kb(),

    )





async def receive_extra_usernames(

    message: Message,

    state: FSMContext,

    bot: Bot,

) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if message.text is None:

        await message.answer(

            TOKEN_EXTRA_USERNAMES_PROMPT,

            reply_markup=token_create_cancel_kb(),

        )

        return



    data = await state.get_data()

    bot_name = data.get("name")

    base_usernames = data.get("base_usernames")

    amount = data.get("amount")

    set_avatars = data.get("set_avatars")

    if (

        not isinstance(bot_name, str)

        or not isinstance(base_usernames, list)

        or not all(isinstance(value, str) for value in base_usernames)

        or not base_usernames

        or not isinstance(amount, int)

        or not isinstance(set_avatars, bool)

    ):

        await state.clear()

        await message.answer("Создание сброшено. Начни заново.", reply_markup=back_kb())

        return



    try:

        extra_usernames = normalize_extra_usernames(message.text.split())

        for index in range(1, amount + 1):

            build_bot_display_name(bot_name, extra_usernames, index)

    except RuntimeError as exc:

        await message.answer(str(exc), reply_markup=token_create_cancel_kb())

        return



    user = message.from_user

    if user is None:

        return

    owner = await upsert_user(user.id, user.username, user.full_name)

    available_accounts = await count_accounts(owner.id)

    if available_accounts < 1:

        await state.clear()

        await message.answer(TOKEN_NO_ACCOUNTS, reply_markup=back_kb())

        return

    await state.clear()

    progress_message = await message.answer(

        format_token_create_queued(amount, available_accounts)

    )

    batch = await create_running_token_batch(

        TokenBatchCreatePayload(

            owner_user_id=owner.id,

            requested_count=amount,

            name=bot_name,

            base_username=base_usernames[0],

            base_usernames=base_usernames,

            extra_usernames=extra_usernames,

            account_limit=None,

            set_avatars=set_avatars,

            chat_id=message.chat.id,

            progress_message_id=progress_message.message_id,

        )

    )

    await progress_message.edit_reply_markup(

        reply_markup=token_create_progress_kb(batch.id)

    )

    spawn_background_task(

        _create_tokens_job(

            bot=bot,

            chat_id=message.chat.id,

            progress_message_id=progress_message.message_id,

            batch_id=batch.id,

            owner_user_id=owner.id,

            name=bot_name,

            base_usernames=base_usernames,

            amount=amount,

            extra_usernames=extra_usernames,

            account_limit=None,

            set_avatars=set_avatars,

        )

    )





async def cancel_create(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    await edit_callback_message(callback, TOKEN_CREATE_CANCELLED, back_kb())





async def open_my_tokens(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    await _render_my_tokens(

        callback,

        parse_page(callback.data, MY_TOKENS_PAGE_PREFIX),

    )





async def open_token_card(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    owner = await upsert_callback_user(callback)

    created_bot_id, page = parse_id_and_page(callback.data, MY_TOKEN_OPEN_PREFIX)

    created_bot = await get_created_bot(owner.id, created_bot_id)

    if created_bot is None:

        await edit_callback_message(

            callback,

            TOKEN_NOT_FOUND,

            my_tokens_kb([], page, page > 0, False, False),

        )

        return

    await edit_callback_message(

        callback,

        format_created_bot_card(created_bot),

        my_token_card_kb(created_bot.id, page),

    )





async def delete_my_token(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    owner = await upsert_callback_user(callback)

    created_bot_id, page = parse_id_and_page(callback.data, MY_TOKEN_DELETE_PREFIX)

    deleted = await delete_created_bot(owner.id, created_bot_id)

    await _render_my_tokens(

        callback,

        page,

        TOKEN_DELETED if deleted else TOKEN_NOT_FOUND,

    )





async def confirm_delete_all_my_tokens(

    callback: CallbackQuery,

    state: FSMContext,

) -> None:

    await state.clear()

    await edit_callback_message(

        callback,

        TOKENS_DELETE_ALL_CONFIRM,

        my_tokens_delete_all_confirm_kb(),

    )





async def delete_all_my_tokens(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    owner = await upsert_callback_user(callback)

    deleted = await delete_all_created_bots(owner.id)

    await _render_my_tokens(

        callback,

        0,

        f"Удалено: {deleted}" if deleted else TOKENS_DELETE_ALL_EMPTY,

    )





async def open_token_edit(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    owner = await upsert_callback_user(callback)

    created_bot_id, page = parse_id_and_page(callback.data, MY_TOKEN_EDIT_PREFIX)

    created_bot = await get_created_bot(owner.id, created_bot_id)

    if created_bot is None:

        await edit_callback_message(callback, TOKEN_NOT_FOUND, back_kb())

        return

    await edit_callback_message(

        callback,

        format_token_edit_menu(created_bot),

        token_edit_kb(created_bot.id, page),

    )





async def request_edit_avatar(callback: CallbackQuery, state: FSMContext) -> None:

    await _request_token_edit(

        callback,

        state,

        TOKEN_EDIT_AVATAR_PREFIX,

        TokenEditState.waiting_avatar,

        TOKEN_EDIT_AVATAR_PROMPT,

    )





async def request_edit_name(callback: CallbackQuery, state: FSMContext) -> None:

    await _request_token_edit(

        callback,

        state,

        TOKEN_EDIT_NAME_PREFIX,

        TokenEditState.waiting_name,

        TOKEN_EDIT_NAME_PROMPT,

    )





async def request_edit_description(callback: CallbackQuery, state: FSMContext) -> None:

    await _request_token_edit(

        callback,

        state,

        TOKEN_EDIT_DESCRIPTION_PREFIX,

        TokenEditState.waiting_description,

        TOKEN_EDIT_DESCRIPTION_PROMPT,

    )





async def request_edit_short_description(

    callback: CallbackQuery,

    state: FSMContext,

) -> None:

    await _request_token_edit(

        callback,

        state,

        TOKEN_EDIT_SHORT_DESCRIPTION_PREFIX,

        TokenEditState.waiting_short_description,

        TOKEN_EDIT_SHORT_DESCRIPTION_PROMPT,

    )





async def request_edit_menu_button(callback: CallbackQuery, state: FSMContext) -> None:

    await _request_token_edit(

        callback,

        state,

        TOKEN_EDIT_MENU_BUTTON_PREFIX,

        TokenEditState.waiting_menu_button,

        TOKEN_EDIT_MENU_BUTTON_PROMPT,

    )





async def process_edit_avatar(

    message: Message,

    state: FSMContext,

    bot: Bot,

) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    edit_data = await _get_token_edit_data(message, state)

    if edit_data is None:

        return

    if not message.photo:

        await message.answer(

            TOKEN_EDIT_AVATAR_REQUIRED,

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

        return



    status = await message.answer(format_token_edit_wait("Устанавливаю аватар..."))

    try:

        file = await bot.get_file(message.photo[-1].file_id)

        if file.file_path is None:

            raise RuntimeError("не удалось скачать фото")

        photo_stream = await bot.download_file(file.file_path)

        photo_bytes = photo_stream.read()

        await set_created_bot_avatar(edit_data.bot_token, photo_bytes)

        await status.edit_text(

            format_token_edit_success("Аватар изменён"),

            reply_markup=token_edit_kb(edit_data.created_bot_id, edit_data.page),

        )

    except Exception as exc:

        await status.edit_text(

            format_token_edit_error(str(exc)),

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

    finally:

        await state.clear()





async def process_edit_name(message: Message, state: FSMContext) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    edit_data = await _get_token_edit_data(message, state)

    if edit_data is None:

        return

    if message.text is None:

        await message.answer(

            TOKEN_EDIT_NAME_PROMPT,

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

        return



    status = await message.answer(format_token_edit_wait("Устанавливаю имя..."))

    try:

        name = await set_created_bot_name(edit_data.bot_token, message.text)

        await update_created_bot_name(

            edit_data.owner_user_id,

            edit_data.created_bot_id,

            name,

        )

        await status.edit_text(

            format_token_edit_success("Имя изменено"),

            reply_markup=token_edit_kb(edit_data.created_bot_id, edit_data.page),

        )

    except Exception as exc:

        await status.edit_text(

            format_token_edit_error(str(exc)),

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

    finally:

        await state.clear()





async def process_edit_description(message: Message, state: FSMContext) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    edit_data = await _get_token_edit_data(message, state)

    if edit_data is None:

        return

    if message.text is None:

        await message.answer(

            TOKEN_EDIT_DESCRIPTION_PROMPT,

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

        return



    status = await message.answer(format_token_edit_wait("Устанавливаю описание..."))

    try:

        await set_created_bot_description(edit_data.bot_token, message.text)

        await status.edit_text(

            format_token_edit_success("Описание изменено"),

            reply_markup=token_edit_kb(edit_data.created_bot_id, edit_data.page),

        )

    except Exception as exc:

        await status.edit_text(

            format_token_edit_error(str(exc)),

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

    finally:

        await state.clear()





async def process_edit_short_description(

    message: Message,

    state: FSMContext,

) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    edit_data = await _get_token_edit_data(message, state)

    if edit_data is None:

        return

    if message.text is None:

        await message.answer(

            TOKEN_EDIT_SHORT_DESCRIPTION_PROMPT,

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

        return



    status = await message.answer(

        format_token_edit_wait("Устанавливаю короткое описание...")

    )

    try:

        await set_created_bot_short_description(edit_data.bot_token, message.text)

        await status.edit_text(

            format_token_edit_success("Короткое описание изменено"),

            reply_markup=token_edit_kb(edit_data.created_bot_id, edit_data.page),

        )

    except Exception as exc:

        await status.edit_text(

            format_token_edit_error(str(exc)),

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

    finally:

        await state.clear()





async def process_edit_menu_button(message: Message, state: FSMContext) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    edit_data = await _get_token_edit_data(message, state)

    if edit_data is None:

        return

    if message.text is None:

        await message.answer(

            TOKEN_EDIT_MENU_BUTTON_PROMPT,

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

        return



    status = await message.answer(format_token_edit_wait("Устанавливаю Menu Button..."))

    try:

        button_text, url = parse_menu_button_input(message.text)

        await set_created_bot_menu_button(edit_data.bot_token, button_text, url)

        await status.edit_text(

            format_token_edit_success("Menu Button установлен"),

            reply_markup=token_edit_kb(edit_data.created_bot_id, edit_data.page),

        )

    except Exception as exc:

        await status.edit_text(

            format_token_edit_error(str(exc)),

            reply_markup=token_edit_back_kb(edit_data.created_bot_id, edit_data.page),

        )

    finally:

        await state.clear()





async def request_bulk_avatar(callback: CallbackQuery, state: FSMContext) -> None:

    owner = await upsert_callback_user(callback)

    tokens = await list_created_bot_tokens(owner.id)

    if not tokens:

        await callback.answer(BULK_AVATAR_NO_TOKENS, show_alert=True)

        return

    await state.clear()

    await state.set_state(BulkAvatarState.waiting_photo)

    await state.update_data(scope="all", batch_id=None)

    await edit_callback_message(callback, BULK_AVATAR_PROMPT, bulk_avatar_cancel_kb())





async def request_bulk_avatar_batch(callback: CallbackQuery, state: FSMContext) -> None:

    owner = await upsert_callback_user(callback)

    batch_id = parse_id(callback.data, BULK_AVATAR_BATCH_PREFIX)

    tokens = await list_token_batch_tokens(owner.id, batch_id)

    if not tokens:

        await callback.answer(BULK_AVATAR_BATCH_NO_TOKENS, show_alert=True)

        return

    await state.clear()

    await state.set_state(BulkAvatarState.waiting_photo)

    await state.update_data(scope="batch", batch_id=batch_id)

    await edit_callback_message(callback, BULK_AVATAR_PROMPT, bulk_avatar_cancel_kb())





async def cancel_bulk_avatar(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    await edit_callback_message(callback, TOKEN_CREATE_CANCELLED, back_kb())





async def process_bulk_avatar(message: Message, state: FSMContext, bot: Bot) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if not message.photo:

        await message.answer(BULK_AVATAR_REQUIRED, reply_markup=bulk_avatar_cancel_kb())

        return

    data = await state.get_data()

    scope = data.get("scope")

    batch_id = data.get("batch_id")

    if scope not in {"all", "batch"}:

        await state.clear()

        await message.answer(TOKEN_EDIT_INVALID_STATE, reply_markup=back_kb())

        return

    user = message.from_user

    if user is None:

        return

    owner = await upsert_user(user.id, user.username, user.full_name)

    if scope == "batch" and isinstance(batch_id, int):

        tokens = await list_token_batch_tokens(owner.id, batch_id)

        if not tokens:

            await state.clear()

            await message.answer(BULK_AVATAR_BATCH_NO_TOKENS, reply_markup=back_kb())

            return

    else:

        tokens = await list_created_bot_tokens(owner.id)

        if not tokens:

            await state.clear()

            await message.answer(BULK_AVATAR_NO_TOKENS, reply_markup=back_kb())

            return



    await state.clear()

    file = await bot.get_file(message.photo[-1].file_id)

    if file.file_path is None:

        await message.answer(format_token_edit_error("не удалось скачать фото"), reply_markup=back_kb())

        return

    photo_stream = await bot.download_file(file.file_path)

    photo_bytes = photo_stream.read()



    from services.bulk_avatar import bulk_set_avatar_for_tokens



    status = await message.answer(BULK_AVATAR_PROGRESS.format(done=0, total=len(tokens), ok=0, fail=0))



    async def progress_cb(done: int, total: int, ok: int, fail: int) -> None:

        try:

            await status.edit_text(BULK_AVATAR_PROGRESS.format(done=done, total=total, ok=ok, fail=fail))

        except Exception:

            pass



    ok, fail = await bulk_set_avatar_for_tokens(tokens, photo_bytes, progress_cb)

    try:

        await status.edit_text(BULK_AVATAR_DONE.format(ok=ok, fail=fail), reply_markup=back_kb())

    except Exception:

        await message.answer(BULK_AVATAR_DONE.format(ok=ok, fail=fail), reply_markup=back_kb())





async def open_token_batch_page(callback: CallbackQuery) -> None:

    owner = await upsert_callback_user(callback)

    batch_id, page = parse_id_and_page(callback.data, TOKEN_BATCH_PAGE_PREFIX)

    await _render_token_batch_result(callback, owner.id, batch_id, page)





async def stop_token_batch(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    owner = await upsert_callback_user(callback)

    batch_id = parse_id(callback.data, TOKEN_BATCH_STOP_PREFIX)

    stopped = await request_stop_token_batch(owner.id, batch_id)

    await callback.answer(

        TOKEN_BATCH_STOP_REQUESTED if stopped else TOKEN_BATCH_STOP_NOT_RUNNING,

        show_alert=True,

    )





async def export_token_batch(callback: CallbackQuery, bot: Bot) -> None:

    owner = await upsert_callback_user(callback)

    batch_id = parse_id(callback.data, TOKEN_BATCH_EXPORT_PREFIX)

    tokens = await list_token_batch_tokens(owner.id, batch_id)

    if not tokens:

        await callback.answer("Токенов нет.", show_alert=True)

        return



    content = ("\n".join(tokens) + "\n").encode("utf-8")

    document = BufferedInputFile(content, filename=f"tokens_{batch_id}.txt")

    await bot.send_document(callback.from_user.id, document)

    await callback.answer("Файл отправлен.")





async def export_my_tokens(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:

    await state.clear()

    owner = await upsert_callback_user(callback)

    tokens = await list_created_bot_tokens(owner.id)

    if not tokens:

        await callback.answer("Токенов нет.", show_alert=True)

        return



    content = ("\n".join(tokens) + "\n").encode("utf-8")

    document = BufferedInputFile(content, filename="my_tokens.txt")

    await bot.send_document(callback.from_user.id, document)

    await callback.answer("Файл отправлен.")





async def resume_pending_token_batches(bot: Bot) -> None:

    batches = await list_resumable_token_batches()

    for batch in batches:

        base_usernames = decode_batch_base_usernames(batch)

        if batch.status == "stopping":

            await finish_token_batch(batch.id, "stopped")

            if batch.chat_id is not None and batch.progress_message_id is not None:

                await _send_token_batch_result(

                    bot,

                    batch.chat_id,

                    batch.progress_message_id,

                    batch.owner_user_id,

                    batch.id,

                )

            continue

        if (

            batch.name is None

            or not base_usernames

            or batch.chat_id is None

            or batch.progress_message_id is None

        ):

            await finish_token_batch(batch.id, "failed")

            continue

        spawn_background_task(

            _create_tokens_job(

                bot=bot,

                chat_id=batch.chat_id,

                progress_message_id=batch.progress_message_id,

                batch_id=batch.id,

                owner_user_id=batch.owner_user_id,

                name=batch.name,

                base_usernames=base_usernames,

                amount=batch.requested_count,

                extra_usernames=decode_batch_extra_usernames(batch),

                account_limit=batch.account_limit,

                set_avatars=batch.set_avatars,

            )

        )





async def _request_token_edit(

    callback: CallbackQuery,

    state: FSMContext,

    prefix: str,

    next_state: State,

    prompt: str,

) -> None:

    owner = await upsert_callback_user(callback)

    created_bot_id, page = parse_id_and_page(callback.data, prefix)

    created_bot = await get_created_bot(owner.id, created_bot_id)

    if created_bot is None:

        await edit_callback_message(callback, TOKEN_NOT_FOUND, back_kb())

        return



    await state.clear()

    await state.update_data(

        created_bot_id=created_bot.id,

        page=page,

        owner_user_id=owner.id,

        bot_token=created_bot.token,

    )

    await state.set_state(next_state)

    await edit_callback_message(

        callback,

        prompt,

        token_edit_back_kb(created_bot.id, page),

    )





async def _get_token_edit_data(

    message: Message,

    state: FSMContext,

) -> TokenEditData | None:

    data = await state.get_data()

    created_bot_id = data.get("created_bot_id")

    page = data.get("page")

    owner_user_id = data.get("owner_user_id")

    bot_token = data.get("bot_token")

    if (

        not isinstance(created_bot_id, int)

        or not isinstance(page, int)

        or not isinstance(owner_user_id, int)

        or not isinstance(bot_token, str)

    ):

        await state.clear()

        await message.answer(TOKEN_EDIT_INVALID_STATE, reply_markup=back_kb())

        return None

    return TokenEditData(

        created_bot_id=created_bot_id,

        page=page,

        owner_user_id=owner_user_id,

        bot_token=bot_token,

    )





async def _create_tokens_job(

    bot: Bot,

    chat_id: int,

    progress_message_id: int,

    batch_id: int,

    owner_user_id: int,

    name: str,

    base_usernames: list[str],

    amount: int,

    extra_usernames: list[str],

    account_limit: int | None,

    set_avatars: bool,

) -> None:

    async def update_progress(progress: BotBatchProgress) -> None:

        await _edit_token_create_progress(

            bot,

            chat_id,

            progress_message_id,

            progress,

            batch_id,

        )



    async def save_item(item: BotBatchItem) -> None:

        await upsert_token_batch_item(batch_id, _build_token_batch_payload(item))



    async def should_stop() -> bool:

        return await is_token_batch_stop_requested(batch_id)



    try:

        initial_items = [

            _bot_batch_item_from_model(item)

            for item in await list_token_batch_items(owner_user_id, batch_id)

        ]

                                                              

        total_timeout = max(600, amount * 200 + 300)

        try:

            result = await asyncio.wait_for(

                create_bots_via_botfather(

                    owner_user_id=owner_user_id,

                    name=name,

                    base_username=base_usernames,

                    amount=amount,

                    extra_usernames=extra_usernames,

                    account_limit=account_limit,

                    set_avatars=set_avatars,

                    initial_items=initial_items,

                    progress_callback=update_progress,

                    item_callback=save_item,

                    should_stop_callback=should_stop,

                ),

                timeout=total_timeout,

            )

        except asyncio.TimeoutError as exc:

            raise RuntimeError(f"батч завис (таймаут {total_timeout}с), прерываю") from exc

        status = "stopped" if await is_token_batch_stop_requested(batch_id) else "completed"

        await finish_token_batch(batch_id, status)

        await _send_token_batch_result(

            bot,

            chat_id,

            progress_message_id,

            owner_user_id,

            batch_id,

        )

    except Exception as exc:

        try:

            await finish_token_batch(batch_id, "failed")

            await _send_token_batch_result(

                bot,

                chat_id,

                progress_message_id,

                owner_user_id,

                batch_id,

            )

        except Exception:

            await _edit_or_send_message(

                bot,

                chat_id,

                progress_message_id,

                format_bot_create_error(str(exc)),

            )





async def _send_token_batch_result(

    bot: Bot,

    chat_id: int,

    progress_message_id: int,

    owner_user_id: int,

    batch_id: int,

) -> None:

    batch = await get_token_batch(owner_user_id, batch_id)

    if batch is None:

        await _edit_or_send_message(

            bot,

            chat_id,

            progress_message_id,

            format_bot_create_error(TOKEN_BATCH_NOT_FOUND),

        )

        return

    items, has_next = await list_token_batch_created_items(

        owner_user_id,

        batch.id,

        0,

        TOKEN_BATCH_PER_PAGE,

    )

    errors = await list_token_batch_failed_items(owner_user_id, batch.id, 5)

    await _edit_or_send_message(

        bot,

        chat_id,

        progress_message_id,

        format_token_batch_page(batch, items, 0, TOKEN_BATCH_PER_PAGE, errors),

        reply_markup=token_batch_result_kb(

            batch.id,

            0,

            False,

            has_next,

            batch.created_count > 0,

        ),

    )





async def _edit_token_create_progress(

    bot: Bot,

    chat_id: int,

    message_id: int,

    progress: BotBatchProgress,

    batch_id: int,

) -> None:

    try:

        await bot.edit_message_text(

            chat_id=chat_id,

            message_id=message_id,

            text=format_token_create_progress(progress),

            reply_markup=token_create_progress_kb(batch_id),

        )

    except (TelegramBadRequest, TelegramRetryAfter):

        return





async def _edit_or_send_message(

    bot: Bot,

    chat_id: int,

    message_id: int,

    text: str,

    reply_markup: InlineKeyboardMarkup | None = None,

) -> None:

    try:

        await bot.edit_message_text(

            chat_id=chat_id,

            message_id=message_id,

            text=text,

            reply_markup=reply_markup,

        )

        return

    except TelegramRetryAfter as exc:

        await asyncio.sleep(exc.retry_after)

        try:

            await bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text=text,

                reply_markup=reply_markup,

            )

            return

        except TelegramBadRequest as retry_exc:

            if _is_message_not_modified(retry_exc):

                return

        except TelegramRetryAfter:

            pass

    except TelegramBadRequest as exc:

        if _is_message_not_modified(exc):

            return

        if not _can_send_fallback_after_edit_error(exc):

            return

    await bot.send_message(chat_id, text, reply_markup=reply_markup)





def _is_message_not_modified(exc: TelegramBadRequest) -> bool:

    return "message is not modified" in str(exc).casefold()





def _can_send_fallback_after_edit_error(exc: TelegramBadRequest) -> bool:

    message = str(exc).casefold()

    return (

        "message to edit not found" in message

        or "message can't be edited" in message

        or "message_id_invalid" in message

        or "there is no text in the message to edit" in message

    )





async def _render_token_batch_result(

    callback: CallbackQuery,

    owner_user_id: int,

    batch_id: int,

    page: int,

) -> None:

    batch = await get_token_batch(owner_user_id, batch_id)

    if batch is None:

        await edit_callback_message(callback, TOKEN_BATCH_NOT_FOUND, back_kb())

        return



    current_page = max(page, 0)

    items, has_next = await list_token_batch_created_items(

        owner_user_id,

        batch_id,

        current_page,

        TOKEN_BATCH_PER_PAGE,

    )

    errors = (

        await list_token_batch_failed_items(owner_user_id, batch_id, 5)

        if current_page == 0

        else []

    )

    if not items and current_page > 0:

        current_page -= 1

        items, has_next = await list_token_batch_created_items(

            owner_user_id,

            batch_id,

            current_page,

            TOKEN_BATCH_PER_PAGE,

        )

        errors = (

            await list_token_batch_failed_items(owner_user_id, batch_id, 5)

            if current_page == 0

            else []

        )



    await edit_callback_message(

        callback,

        format_token_batch_page(

            batch,

            items,

            current_page,

            TOKEN_BATCH_PER_PAGE,

            errors,

        ),

        token_batch_result_kb(

            batch.id,

            current_page,

            current_page > 0,

            has_next,

            batch.created_count > 0,

        ),

    )





def _build_token_batch_payloads(

    result: BotBatchCreateResult,

) -> list[TokenBatchItemPayload]:

    return [

        _build_token_batch_payload(item)

        for item in result.items

    ]





def _build_token_batch_payload(item: BotBatchItem) -> TokenBatchItemPayload:

    return TokenBatchItemPayload(

        position=item.index,

        ok=item.ok,

        account_title=item.account_title,

        name=item.name,

        created_bot_id=item.created_bot_id,

        account_id=item.account_id,

        username=item.username,

        token=item.token,

        error=item.error,

    )





def _bot_batch_item_from_model(item: TokenCreateBatchItem) -> BotBatchItem:

    return BotBatchItem(

        index=item.position,

        ok=item.ok,

        account_title=item.account_title,

        name=item.name,

        created_bot_id=item.created_bot_id,

        account_id=item.account_id,

        username=item.username,

        token=item.token,

        error=item.error,

    )





async def _render_my_tokens(

    callback: CallbackQuery,

    page: int,

    notice: str | None = None,

) -> None:

    owner = await upsert_callback_user(callback)

    current_page = max(page, 0)

    created_bots, has_next = await list_created_bots(

        owner.id,

        current_page,

        MY_TOKENS_PER_PAGE,

    )

    if not created_bots and current_page > 0:

        current_page -= 1

        created_bots, has_next = await list_created_bots(

            owner.id,

            current_page,

            MY_TOKENS_PER_PAGE,

        )

    buttons = [

        (created_bot.id, format_created_bot_button(created_bot))

        for created_bot in created_bots

    ]

    await edit_callback_message(

        callback,

        format_my_tokens_list(created_bots, current_page),

        my_tokens_kb(

            buttons,

            current_page,

            current_page > 0,

            has_next,

            bool(created_bots),

        ),

        notice,

    )





def get_router() -> Router:

    router = Router(name="tokens")

    router.callback_query.register(open_create_tokens, F.data == CREATE_TOKENS)

    router.callback_query.register(

        choose_create_avatars,

        F.data.in_({TOKEN_CREATE_AVATAR_YES, TOKEN_CREATE_AVATAR_NO}),

    )

    router.callback_query.register(cancel_create, F.data == TOKEN_CREATE_CANCEL)

    router.message.register(receive_bot_name, TokenCreateState.waiting_name)

    router.message.register(receive_base_username, TokenCreateState.waiting_base_username)

    router.message.register(receive_token_count, TokenCreateState.waiting_count)

    router.message.register(

        receive_extra_usernames,

        TokenCreateState.waiting_extra_usernames,

    )

    router.callback_query.register(open_my_tokens, F.data == MY_TOKENS)

    router.callback_query.register(export_my_tokens, F.data == MY_TOKENS_EXPORT)

    router.callback_query.register(

        confirm_delete_all_my_tokens,

        F.data == MY_TOKENS_DELETE_ALL_CONFIRM,

    )

    router.callback_query.register(delete_all_my_tokens, F.data == MY_TOKENS_DELETE_ALL)

    router.callback_query.register(

        open_my_tokens,

        F.data.startswith(MY_TOKENS_PAGE_PREFIX),

    )

    router.callback_query.register(

        open_token_card,

        F.data.startswith(MY_TOKEN_OPEN_PREFIX),

    )

    router.callback_query.register(

        delete_my_token,

        F.data.startswith(MY_TOKEN_DELETE_PREFIX),

    )

    router.callback_query.register(

        open_token_edit,

        F.data.startswith(MY_TOKEN_EDIT_PREFIX),

    )

    router.callback_query.register(

        request_edit_avatar,

        F.data.startswith(TOKEN_EDIT_AVATAR_PREFIX),

    )

    router.callback_query.register(

        request_edit_name,

        F.data.startswith(TOKEN_EDIT_NAME_PREFIX),

    )

    router.callback_query.register(

        request_edit_description,

        F.data.startswith(TOKEN_EDIT_DESCRIPTION_PREFIX),

    )

    router.callback_query.register(

        request_edit_short_description,

        F.data.startswith(TOKEN_EDIT_SHORT_DESCRIPTION_PREFIX),

    )

    router.callback_query.register(

        request_edit_menu_button,

        F.data.startswith(TOKEN_EDIT_MENU_BUTTON_PREFIX),

    )

    router.message.register(process_edit_avatar, TokenEditState.waiting_avatar)

    router.message.register(process_edit_name, TokenEditState.waiting_name)

    router.message.register(

        process_edit_description,

        TokenEditState.waiting_description,

    )

    router.message.register(

        process_edit_short_description,

        TokenEditState.waiting_short_description,

    )

    router.message.register(

        process_edit_menu_button,

        TokenEditState.waiting_menu_button,

    )

    router.callback_query.register(

        stop_token_batch,

        F.data.startswith(TOKEN_BATCH_STOP_PREFIX),

    )

    router.callback_query.register(

        open_token_batch_page,

        F.data.startswith(TOKEN_BATCH_PAGE_PREFIX),

    )

    router.callback_query.register(

        export_token_batch,

        F.data.startswith(TOKEN_BATCH_EXPORT_PREFIX),

    )

    router.callback_query.register(request_bulk_avatar, F.data == BULK_AVATAR)

    router.callback_query.register(

        request_bulk_avatar_batch, F.data.startswith(BULK_AVATAR_BATCH_PREFIX)

    )

    router.callback_query.register(cancel_bulk_avatar, F.data == BULK_AVATAR_CANCEL)

    router.message.register(process_bulk_avatar, BulkAvatarState.waiting_photo)

    return router

