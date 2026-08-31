from collections.abc import Sequence

from html import escape

from typing import TYPE_CHECKING



from models import CreatedBot, TokenCreateBatch, TokenCreateBatchItem



if TYPE_CHECKING:

    from services.bot_creator import BotBatchCreateResult, BotBatchProgress



TOKEN_NAME_PROMPT = "<b>Создать токены</b>\n\nВведите имя бота:"

TOKEN_AVATAR_PROMPT = "<b>Создать токены</b>\n\nСтавить случайные аватарки ботам?"

TOKEN_BASE_USERNAME_PROMPT = (

    "Введите основной username или список примеров через пробел:"

)

TOKEN_COUNT_PROMPT = "Сколько токенов создать всего?"

TOKEN_EXTRA_USERNAMES_PROMPT = (

    "Введи <b>от 4 до ∞</b> дополнительных юзернеймов через пробел для имени ботов.\n"

    "Каждому боту выберу 4 случайных в случайном порядке (антифрод). До 32 символов в слове.\n"

    "Если не нужно — отправь <code>-</code>"

)

TOKEN_NO_ACCOUNTS = "Сначала добавь рабочие аккаунты."

TOKEN_CREATING = "Принял. Создаю токены в фоне и пришлю результат."

TOKEN_CREATE_CANCELLED = "Создание токенов отменено."

TOKEN_NOT_FOUND = "Бот не найден."

TOKEN_BATCH_NOT_FOUND = "Результат создания не найден."

TOKEN_BATCH_STOP_REQUESTED = "Останавливаю создание. Уже созданные токены сохранены."

TOKEN_BATCH_STOP_NOT_RUNNING = "Эта задача уже не выполняется."

TOKEN_DELETED = "Токен удалён."

TOKENS_DELETE_ALL_CONFIRM = "Удалить все токены из базы?"

TOKENS_DELETE_ALL_EMPTY = "Токенов для удаления нет."

TOKEN_EDIT_AVATAR_PROMPT = "<b>Сменить аватар</b>\n\nОтправь фото для аватарки бота:"

TOKEN_EDIT_AVATAR_REQUIRED = "Отправь именно фото."

TOKEN_EDIT_NAME_PROMPT = "<b>Сменить имя</b>\n\nВведи новое имя бота:"

TOKEN_EDIT_DESCRIPTION_PROMPT = "<b>Сменить описание</b>\n\nВведи новое описание бота:"

TOKEN_EDIT_SHORT_DESCRIPTION_PROMPT = (

    "<b>Сменить короткое описание</b>\n\nВведи новое короткое описание бота:"

)

TOKEN_EDIT_MENU_BUTTON_PROMPT = (

    "<b>Установить Menu Button</b>\n\n"

    "Отправь текст кнопки и https://URL через пробел.\n"

    "Например: <code>Маркет https://example.com</code>"

)

TOKEN_EDIT_INVALID_STATE = "Редактирование сброшено. Открой карточку бота заново."

BULK_AVATAR_PROMPT = "<b>Массовая аватарка</b>\n\nОтправь фото — поставлю его всем твоим ботам:"

BULK_AVATAR_REQUIRED = "Отправь именно фото."

BULK_AVATAR_NO_TOKENS = "У тебя нет токенов для установки аватарки."

BULK_AVATAR_PROGRESS = "<b>Ставлю аватарку...</b>\n{done}/{total} — {ok} успешно, {fail} ошибок"

BULK_AVATAR_DONE = "<b>Готово</b>\nУспешно: {ok}\nОшибок: {fail}"

BULK_AVATAR_BATCH_NO_TOKENS = "В этом батче нет токенов для аватарки."





def format_bot_create_success(name: str, username: str, token: str) -> str:

    return "\n".join(

        [

            "<b>Токен создан</b>",

            f"Имя: {escape(name)}",

            f"Username: @{escape(username)}",

            f"Token: <code>{escape(token)}</code>",

        ]

    )





def format_bot_create_error(error: str) -> str:

    return f"<b>Не удалось создать токены</b>\n\n{escape(error)}"





def format_token_edit_menu(created_bot: CreatedBot) -> str:

    return "\n".join(

        [

            "<b>Редактирование бота</b>",

            f"Имя: {escape(created_bot.name)}",

            f"Username: @{escape(created_bot.username)}",

        ]

    )





def format_token_edit_wait(text: str) -> str:

    return f"<b>{escape(text)}</b>"





def format_token_edit_success(text: str) -> str:

    return f"<b>{escape(text)}</b>"





def format_token_edit_error(error: str) -> str:

    return f"<b>Не удалось изменить бота</b>\n\n{escape(error)}"





def format_token_create_queued(amount: int, account_count: int) -> str:

    return "\n".join(

        [

            "<b>Создание токенов</b>",

            "",

            f"Аккаунтов: <code>{account_count}</code>",

            "Создано ботов: <code>0</code>",

            "Ошибок: <code>0</code>",

            "В работе: <code>0</code>",

            f"Осталось: <code>{amount}</code>",

            f"Всего: <code>{amount}</code>",

        ]

    )





def format_token_create_progress(progress: "BotBatchProgress") -> str:

    rows = [

        "<b>Создание токенов</b>",

        "",

        f"Аккаунтов: <code>{progress.accounts_total}</code>",

    ]

    if progress.accounts_active != progress.accounts_total:

        rows.append(f"Рабочих сейчас: <code>{progress.accounts_active}</code>")

    rows.extend(

        [

            f"Создано ботов: <code>{progress.created}</code>",

            f"Ошибок: <code>{progress.failed}</code>",

            f"В работе: <code>{progress.in_progress}</code>",

            f"Ждут паузу: <code>{progress.waiting_accounts}</code>",

            f"Осталось: <code>{progress.remaining}</code>",

            f"Всего: <code>{progress.requested}</code>",

        ]

    )

    if progress.wait_remaining_seconds is not None:

        if progress.wait_reason:

            rows.append(

                f"{escape(progress.wait_reason)}: <code>{progress.wait_remaining_seconds} сек.</code>"

            )

        else:

            rows.append(

                f"Пауза перед следующим: <code>{progress.wait_remaining_seconds} сек.</code>"

            )

    if progress.current_account_title:

        rows.append(f"Аккаунт: {escape(progress.current_account_title)}")

    return "\n".join(rows)





def format_bot_batch_report(result: "BotBatchCreateResult") -> str:

    rows = [

        "<b>Создание токенов завершено</b>",

        f"Запрошено: <code>{result.requested}</code>",

        f"Создано: <code>{result.created}</code>",

        f"Ошибок: <code>{result.failed}</code>",

    ]

    errors = [item for item in result.items if not item.ok][:10]

    if errors:

        rows.extend(["", "<b>Ошибки</b>"])

        for item in errors:

            account = escape(item.account_title)

            error = escape(item.error or "ошибка")

            rows.append(f"{item.index}. {account}: {error}")

    if result.failed > len(errors):

        rows.append(f"...и ещё {result.failed - len(errors)}")

    return "\n".join(rows)





def format_token_batch_page(

    batch: TokenCreateBatch,

    items: Sequence[TokenCreateBatchItem],

    page: int,

    per_page: int,

    errors: Sequence[TokenCreateBatchItem] = (),

) -> str:

    total_pages = max(1, (batch.created_count + per_page - 1) // per_page)

    title = {

        "stopped": "Создание остановлено",

        "failed": "Создание завершилось с ошибкой",

    }.get(batch.status, "Создание завершено")

    rows = [

        f"<b>{title}</b>",

        f"Запрошено: <code>{batch.requested_count}</code>",

        f"Создано: <code>{batch.created_count}</code>",

        f"Ошибок: <code>{batch.failed_count}</code>",

    ]

    if batch.created_count == 0:

        rows.extend(["", "Токены не созданы."])

        _append_token_batch_errors(rows, batch, errors)

        return "\n".join(rows)



    rows.extend(["", f"Страница {page + 1} из {total_pages}", ""])

    for item in items:

        username = f"@{escape(item.username)}" if item.username else "-"

        token = escape(item.token or "")

        account = escape(item.account_title)

        rows.append(f"{item.position}. {username} - <code>{token}</code>")

        rows.append(f"Аккаунт: {account}")

    if page == 0:

        _append_token_batch_errors(rows, batch, errors)

    return "\n".join(rows)





def _append_token_batch_errors(

    rows: list[str],

    batch: TokenCreateBatch,

    errors: Sequence[TokenCreateBatchItem],

) -> None:

    if not errors:

        return

    rows.extend(["", "<b>Ошибки</b>"])

    for item in errors:

        account = escape(item.account_title)

        error = escape(item.error or "ошибка")

        rows.append(f"{item.position}. {account}: {error}")

    if batch.failed_count > len(errors):

        rows.append(f"...и ещё {batch.failed_count - len(errors)}")





def format_my_tokens_list(created_bots: Sequence[CreatedBot], page: int) -> str:

    if not created_bots and page == 0:

        return "<b>Мои токены</b>\n\nТокенов пока нет."

    if not created_bots:

        return "<b>Мои токены</b>\n\nНа этой странице токенов нет."

    return f"<b>Мои токены</b>\n\nСтраница {page + 1}"





def format_created_bot_button(created_bot: CreatedBot) -> str:

    return f"@{created_bot.username}"





def format_created_bot_card(created_bot: CreatedBot) -> str:

    return "\n".join(

        [

            "<b>Бот</b>",

            f"Имя: {escape(created_bot.name)}",

            f"Username: @{escape(created_bot.username)}",

            f"Token: <code>{escape(created_bot.token)}</code>",

            f"Создан: <code>{created_bot.created_at:%d.%m.%Y %H:%M}</code>",

        ]

    )

