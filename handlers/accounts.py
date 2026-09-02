import logging

from contextlib import suppress



from aiogram import Bot, F, Router

from aiogram.enums import ChatType

from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup

from aiogram.types import CallbackQuery, Message

from core.temp_files import app_temp_dir



from keyboards.menu import (

    ACCOUNTS,

    ACCOUNTS_CHECK,

    ACCOUNTS_PAGE_PREFIX,

    ACCOUNTS_PROXY_CANCEL,

    ACCOUNTS_PROXY_UPLOAD,

    ACCOUNT_DELETE_ALL,

    ACCOUNT_DELETE_ALL_CONFIRM,

    ACCOUNT_DELETE_PREFIX,

    ACCOUNT_IMPORT,

    ACCOUNT_IMPORT_CANCEL,

    ACCOUNT_OPEN_PREFIX,

    account_card_kb,

    account_delete_all_confirm_kb,

    account_import_cancel_kb,

    account_proxy_cancel_kb,

    accounts_kb,

)

from handlers.utils import (

    edit_callback_message,

    parse_id_and_page,

    parse_page,

    upsert_callback_user,

)

from repositories.account import (

    delete_account,

    delete_all_accounts,

    get_account,

    list_accounts,

)

from repositories.created_bot import list_account_ids_with_created_bots

from repositories.user import upsert_user

from services.account_import import import_account_document

from services.background import spawn_background_task

from texts.accounts import (

    ACCOUNTS_CHECK_EMPTY,

    ACCOUNTS_CHECK_STARTED,

    ACCOUNTS_DELETED,

    ACCOUNTS_DELETE_ALL_CONFIRM,

    ACCOUNTS_DELETE_ALL_EMPTY,

    ACCOUNTS_OPEN_ERROR,

    ACCOUNT_IMPORT_INVALID_FILE,

    ACCOUNT_IMPORT_PROMPT,

    ACCOUNT_IMPORT_SINGLE_FILE_ONLY,

    ACCOUNT_IMPORT_STARTED,

    ACCOUNT_NOT_FOUND,

    PROXY_UPLOAD_DONE,

    PROXY_UPLOAD_EMPTY,

    PROXY_UPLOAD_INVALID,

    PROXY_UPLOAD_PROMPT,

    format_account_button,

    format_account_card,

    format_accounts_check_report,

    format_accounts_list,

)



ACCOUNTS_PER_PAGE = 6

_active_account_imports: set[int] = set()

_rejected_account_import_media_groups: set[str] = set()

_active_account_checks: set[int] = set()

logger = logging.getLogger(__name__)





class AccountImportState(StatesGroup):

    waiting_file = State()





class AccountProxyState(StatesGroup):

    waiting_file = State()





async def open_accounts(callback: CallbackQuery) -> None:

    with suppress(TelegramBadRequest):

        await callback.answer()

    try:

        await _render_accounts(

            callback,

            parse_page(callback.data, ACCOUNTS_PAGE_PREFIX),

            answer_callback=False,

        )

    except Exception:

        logger.exception("Failed to open accounts for user %s", callback.from_user.id)

        if isinstance(callback.message, Message):

            with suppress(TelegramBadRequest):

                await callback.message.answer(ACCOUNTS_OPEN_ERROR)





async def request_import(callback: CallbackQuery, state: FSMContext) -> None:

    await state.set_state(AccountImportState.waiting_file)

    await edit_callback_message(callback, ACCOUNT_IMPORT_PROMPT, account_import_cancel_kb())





async def cancel_import(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    await _render_accounts(callback, 0)





async def receive_import_file(message: Message, state: FSMContext, bot: Bot) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if message.document is None:

        await message.answer(ACCOUNT_IMPORT_INVALID_FILE)

        return

    filename = message.document.file_name or ""

    suffix = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""

    if message.media_group_id is not None and suffix in {"session", "txt"}:

        if message.media_group_id in _rejected_account_import_media_groups:

            return

        _rejected_account_import_media_groups.add(message.media_group_id)

        await message.answer(ACCOUNT_IMPORT_SINGLE_FILE_ONLY)

        return

    user = message.from_user

    if user is None:

        return

    if user.id in _active_account_imports:

        return

    _active_account_imports.add(user.id)

    owner = await upsert_user(user.id, user.username, user.full_name)

    await state.clear()

    progress_message = await message.answer(ACCOUNT_IMPORT_STARTED)



    async def run_import() -> None:

        try:

            await import_account_document(

                bot=bot,

                chat_id=message.chat.id,

                owner_user_id=owner.id,

                document=message.document,

                progress_message_id=progress_message.message_id,

            )

        finally:

            _active_account_imports.discard(user.id)



    spawn_background_task(

        run_import()

    )





async def open_account_card(callback: CallbackQuery) -> None:

    owner = await upsert_callback_user(callback)

    account_id, page = parse_id_and_page(callback.data, ACCOUNT_OPEN_PREFIX)

    account = await get_account(owner.id, account_id)

    if account is None:

        await edit_callback_message(

            callback,

            ACCOUNT_NOT_FOUND,

            accounts_kb([], page, page > 0, False, False),

        )

        return

    await edit_callback_message(

        callback,

        format_account_card(account),

        account_card_kb(account.id, page),

    )





async def delete_account_card(callback: CallbackQuery) -> None:

    owner = await upsert_callback_user(callback)

    account_id, page = parse_id_and_page(callback.data, ACCOUNT_DELETE_PREFIX)

    await delete_account(owner.id, account_id)

    await _render_accounts(callback, page, ACCOUNTS_DELETED)





async def confirm_delete_all(callback: CallbackQuery) -> None:

    await edit_callback_message(

        callback,

        ACCOUNTS_DELETE_ALL_CONFIRM,

        account_delete_all_confirm_kb(),

    )





async def delete_all(callback: CallbackQuery) -> None:

    owner = await upsert_callback_user(callback)

    deleted = await delete_all_accounts(owner.id)

    await _render_accounts(

        callback,

        0,

        f"Удалено: {deleted}" if deleted else ACCOUNTS_DELETE_ALL_EMPTY,

    )





async def check_accounts(callback: CallbackQuery, bot: Bot) -> None:

    owner = await upsert_callback_user(callback)

    if owner.id in _active_account_checks:

        await callback.answer("Проверка уже идет...", show_alert=True)

        return

    await callback.answer()

                       

    from repositories.account import count_accounts



    if await count_accounts(owner.id) == 0:

        await edit_callback_message(callback, ACCOUNTS_CHECK_EMPTY, accounts_kb([], 0, False, False, False))

        return

    _active_account_checks.add(owner.id)

    progress_msg = None

    try:

        progress_msg = await bot.send_message(callback.from_user.id, ACCOUNTS_CHECK_STARTED)

    except Exception:

        pass



    async def run_check() -> None:

        try:

            from services.account_checker import check_accounts_and_cleanup



            result = await check_accounts_and_cleanup(owner.id)

            report = format_accounts_check_report(result)

            if progress_msg is not None:

                try:

                    await bot.edit_message_text(

                        chat_id=progress_msg.chat.id,

                        message_id=progress_msg.message_id,

                        text=report,

                    )

                except Exception:

                    await bot.send_message(callback.from_user.id, report)

            else:

                await bot.send_message(callback.from_user.id, report)

        finally:

            _active_account_checks.discard(owner.id)



    spawn_background_task(run_check())





async def request_proxy_upload(callback: CallbackQuery, state: FSMContext) -> None:

    await state.set_state(AccountProxyState.waiting_file)

    await edit_callback_message(callback, PROXY_UPLOAD_PROMPT, account_proxy_cancel_kb())





async def cancel_proxy_upload(callback: CallbackQuery, state: FSMContext) -> None:

    await state.clear()

    await _render_accounts(callback, 0)





async def receive_proxy_file(message: Message, state: FSMContext, bot: Bot) -> None:

    if message.chat.type != ChatType.PRIVATE:

        return

    if message.document is None:

        await message.answer(PROXY_UPLOAD_INVALID, reply_markup=account_proxy_cancel_kb())

        return

    if message.document.file_name and not message.document.file_name.lower().endswith(".txt"):

        await message.answer(PROXY_UPLOAD_INVALID, reply_markup=account_proxy_cancel_kb())

        return

    user = message.from_user

    if user is None:

        return

    owner = await upsert_user(user.id, user.username, user.full_name)

    await state.clear()

                      

    from repositories.account import bulk_assign_proxies, count_accounts

    from services.telegram_client import parse_proxy_url



    if await count_accounts(owner.id) == 0:

        await message.answer("Сначала добавь аккаунты.", reply_markup=account_proxy_cancel_kb())

        return



    with app_temp_dir("filya_proxies_") as tmp:

        tmp_path = tmp / "proxies.txt"

        await bot.download(message.document, destination=tmp_path)

        text = tmp_path.read_text(encoding="utf-8", errors="ignore")

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        valid: list[str] = []

        for line in lines:

            if parse_proxy_url(line) is not None:

                valid.append(line)

        if not valid:

            await message.answer(PROXY_UPLOAD_EMPTY, reply_markup=account_proxy_cancel_kb())

            return

        assigned = await bulk_assign_proxies(owner.id, valid)

        await message.answer(

            PROXY_UPLOAD_DONE.format(accounts=await count_accounts(owner.id), proxies=len(valid), assigned=assigned)

        )





async def _render_accounts(

    callback: CallbackQuery,

    page: int,

    notice: str | None = None,

    answer_callback: bool = True,

) -> None:

    owner = await upsert_callback_user(callback)

    current_page = max(page, 0)

    accounts, has_next = await list_accounts(owner.id, current_page, ACCOUNTS_PER_PAGE)

    if not accounts and current_page > 0:

        current_page -= 1

        accounts, has_next = await list_accounts(

            owner.id,

            current_page,

            ACCOUNTS_PER_PAGE,

        )

    used_account_ids = await list_account_ids_with_created_bots(

        owner.id,

        [account.id for account in accounts],

    )

    buttons = [

        (account.id, format_account_button(account, account.id in used_account_ids))

        for account in accounts

    ]

    await edit_callback_message(

        callback,

        format_accounts_list(accounts, current_page),

        accounts_kb(

            buttons,

            current_page,

            current_page > 0,

            has_next,

            bool(accounts),

        ),

        notice,

        answer_callback=answer_callback,

    )





def get_router() -> Router:

    router = Router(name="accounts")

    router.callback_query.register(open_accounts, F.data == ACCOUNTS)

    router.callback_query.register(open_accounts, F.data.startswith(ACCOUNTS_PAGE_PREFIX))

    router.callback_query.register(request_import, F.data == ACCOUNT_IMPORT)

    router.callback_query.register(cancel_import, F.data == ACCOUNT_IMPORT_CANCEL)

    router.callback_query.register(request_proxy_upload, F.data == ACCOUNTS_PROXY_UPLOAD)

    router.callback_query.register(cancel_proxy_upload, F.data == ACCOUNTS_PROXY_CANCEL)

    router.callback_query.register(check_accounts, F.data == ACCOUNTS_CHECK)

    router.message.register(receive_import_file, AccountImportState.waiting_file)

    router.message.register(receive_proxy_file, AccountProxyState.waiting_file)

    router.callback_query.register(

        open_account_card,

        F.data.startswith(ACCOUNT_OPEN_PREFIX),

    )

    router.callback_query.register(

        delete_account_card,

        F.data.startswith(ACCOUNT_DELETE_PREFIX),

    )

    router.callback_query.register(confirm_delete_all, F.data == ACCOUNT_DELETE_ALL_CONFIRM)

    router.callback_query.register(delete_all, F.data == ACCOUNT_DELETE_ALL)

    return router

