from collections.abc import Sequence

from html import escape

from typing import TYPE_CHECKING



from models import TelegramAccount



if TYPE_CHECKING:

    from services.account_import import AccountCheck, AccountImportProgress



ACCOUNT_IMPORT_PROMPT = (

    "Отправь один .session файл Telethon или .zip архив с такими файлами."

)

ACCOUNT_IMPORT_STARTED = "Файл принят. Проверяю аккаунты в фоне и пришлю результат."

ACCOUNT_IMPORT_INVALID_FILE = "Нужен файл .session, .txt или .zip."

ACCOUNT_IMPORT_SINGLE_FILE_ONLY = "Одиночный .session можно отправить только одним файлом. Для нескольких аккаунтов отправь .zip архив."

ACCOUNT_NOT_FOUND = "Аккаунт не найден."

ACCOUNTS_DELETED = "Аккаунт удалён."

ACCOUNTS_DELETE_ALL_CONFIRM = "Удалить все аккаунты из базы?"

ACCOUNTS_DELETE_ALL_EMPTY = "Аккаунтов для удаления нет."

ACCOUNTS_CHECK_STARTED = "Проверяю аккаунты... Это займет до минуты."

ACCOUNTS_CHECK_EMPTY = "Аккаунтов нет."

ACCOUNTS_OPEN_ERROR = "Не удалось открыть аккаунты. Попробуй ещё раз."

ACCOUNTS_CHECK_PROGRESS = "<b>Проверка аккаунтов</b>\n{done}/{total} — валидных: {valid}, удалено: {deleted}"

PROXY_UPLOAD_PROMPT = (

    "<b>Прокси</b>\n\nОтправь .txt файл с прокси (1 прокси = 1 строка, формат http://user:pass@host:port).\n"

    "Раздам рандомно по 1 прокси на аккаунт (ротация 30м). Можно перезалить позже."

)

PROXY_UPLOAD_INVALID = "Нужен .txt файл с прокси."

PROXY_UPLOAD_EMPTY = "В файле нет валидных прокси."

PROXY_UPLOAD_DONE = "<b>Прокси назначены</b>\nАккаунтов: <code>{accounts}</code>\nПрокси в файле: <code>{proxies}</code>\nНазначено: <code>{assigned}</code>"





def format_import_progress(progress: "AccountImportProgress") -> str:

    rows = [

        "<b>Добавление аккаунтов</b>",

        "",

        f"Этап: {escape(progress.stage)}",

    ]

    if progress.total:

        rows.extend(

            [

                f"Найдено файлов: <code>{progress.total}</code>",

                f"Проверено: <code>{progress.processed}</code>",

                f"Добавлено: <code>{progress.created}</code>",

                f"Обновлено: <code>{progress.updated}</code>",

                f"Отклонено: <code>{progress.failed}</code>",

                f"Невалидных: <code>{progress.invalid}</code>",

                f"В работе: <code>{progress.in_progress}</code>",

                f"Осталось: <code>{progress.remaining}</code>",

            ]

        )

    if progress.current_file:

        rows.append(f"Файл: {escape(progress.current_file)}")

    return "\n".join(rows)





def format_import_error(error: str) -> str:

    return f"<b>Не удалось обработать файл</b>\n\n{escape(error)}"





def format_accounts_list(accounts: Sequence[TelegramAccount], page: int) -> str:

    if not accounts and page == 0:

        return "<b>Аккаунты</b>\n\nАккаунтов пока нет."

    if not accounts:

        return "<b>Аккаунты</b>\n\nНа этой странице аккаунтов нет."

    return f"<b>Аккаунты</b>\n\nСтраница {page + 1}"





def format_account_button(account: TelegramAccount, used: bool = False) -> str:

    title = _account_title(

        phone=account.phone,

        username=account.username,

        first_name=account.first_name,

        last_name=account.last_name,

        telegram_id=account.telegram_id,

    )

    if used:

        short_title = title if len(title) <= 34 else f"{title[:31]}..."

        return f"{short_title} ✅"

    return title if len(title) <= 36 else f"{title[:33]}..."





def format_account_card(account: TelegramAccount) -> str:

    rows = [

        "<b>Аккаунт</b>",

        f"ID: <code>{account.telegram_id}</code>",

    ]

    if account.phone:

        rows.append(f"Телефон: <code>+{escape(account.phone.lstrip('+'))}</code>")

    if account.username:

        rows.append(f"Username: @{escape(account.username)}")

    name = " ".join(filter(None, [account.first_name, account.last_name]))

    if name:

        rows.append(f"Имя: {escape(name)}")

    if account.dc_id is not None:

        rows.append(f"DC: <code>{account.dc_id}</code>")

    if getattr(account, "proxy_url", None):

                    

        proxy = account.proxy_url

        try:

            from urllib.parse import urlparse



            p = urlparse(proxy)

            host = p.hostname or "-"

            rows.append(f"Прокси: <code>{escape(host)}:{p.port}</code>")

        except Exception:

            rows.append("Прокси: <code>есть</code>")

    else:

        rows.append("Прокси: <code>нет</code>")

    rows.append(f"Проверен: <code>{account.last_checked_at:%d.%m.%Y %H:%M}</code>")

    return "\n".join(rows)





def format_import_report(results: Sequence["AccountCheck"]) -> str:

    created = sum(1 for result in results if result.ok and result.created)

    updated = sum(1 for result in results if result.ok and not result.created)

    failed = sum(1 for result in results if not result.ok)

    invalid = sum(1 for result in results if result.invalid)

    duplicate = sum(1 for result in results if result.duplicate)

    rows = [

        "<b>Импорт аккаунтов</b>",

        f"Проверено: <code>{len(results)}</code>",

        f"Добавлено: <code>{created}</code>",

        f"Обновлено: <code>{updated}</code>",

        f"Отклонено: <code>{failed}</code>",

        f"Невалидных: <code>{invalid}</code>",

    ]

    if duplicate:

        rows.append(f"Дубликатов: <code>{duplicate}</code>")

    rejected = [result for result in results if not result.ok]

    if rejected:

        rows.append("")

        rows.append("<b>Причины отклонения:</b>")

        for result in rejected[:10]:

            title = result.account_title or result.filename

            reason = result.error or "неизвестная ошибка"

            rows.append(f"{escape(title)} — {escape(reason)}")

        if len(rejected) > 10:

            rows.append(f"...и ещё {len(rejected) - 10}")

    return "\n".join(

        rows

    )





def format_accounts_check_report(result) -> str:

    rows = [

        "<b>Проверка завершена</b>",

        f"Всего: <code>{result.total}</code>",

        f"Валидных: <code>{result.valid}</code>",

        f"Удалено невалидных: <code>{result.deleted}</code>",

    ]

    if result.failed:

        rows.append(f"Ошибок: <code>{result.failed}</code>")

    if result.details and result.deleted:

        rows.append("")

        rows.append("<b>Удалены:</b>")

        for _, title, ok, err in result.details[:10]:

            if not ok and err and "удалён" in err:

                rows.append(f"{escape(title)} — {escape(err)}")

        if result.deleted > 10:

            rows.append(f"...и ещё {result.deleted - 10}")

    return "\n".join(rows)





def _account_title(

    phone: str | None,

    username: str | None,

    first_name: str | None,

    last_name: str | None,

    telegram_id: int,

) -> str:

    if phone:

        return f"+{phone.lstrip('+')}"

    if username:

        return f"@{username}"

    name = " ".join(filter(None, [first_name, last_name]))

    return name or str(telegram_id)

