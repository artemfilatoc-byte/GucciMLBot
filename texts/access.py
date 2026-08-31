from repositories.access import AccessStats



ACCESS_REQUIRED_MESSAGE = (

    "Доступ закрыт.\n"

    "Отправь ключ активации или открой бота по ссылке с ключом."

)

ACCESS_REQUIRED_ALERT = "Нужен ключ доступа."

ACCESS_KEY_PROMPT = "Отправь ключ после команды: /key КЛЮЧ"

ACCESS_KEY_ACTIVATED = "Доступ активирован."

ACCESS_KEY_ALREADY_ACTIVE = "Доступ уже активирован."

ACCESS_KEY_INVALID = "Ключ неверный."

ACCESS_KEY_USED = "Ключ уже активирован другим пользователем."

ADMIN_DENIED = "Нет доступа к админке."





def format_admin_panel(stats: AccessStats) -> str:

    return (

        "<b>Админка</b>\n\n"

        f"Пользователей: <code>{stats.users_total}</code>\n"

        f"С доступом: <code>{stats.users_with_access}</code>\n"

        f"Ключей всего: <code>{stats.keys_total}</code>\n"

        f"Свободных ключей: <code>{stats.keys_unused}</code>\n"

        f"Активированных ключей: <code>{stats.keys_used}</code>\n"

        f"Аккаунтов всего: <code>{stats.accounts_total}</code>"

    )





def format_access_key_created(key: str) -> str:

    return (

        "<b>Ключ создан</b>\n\n"

        f"<code>{key}</code>\n\n"

        "Пользователь может отправить этот ключ в бот или открыть:\n"

        f"<code>/start {key}</code>"

    )





def format_keys_list(page: int, has_keys: bool) -> str:

    if not has_keys and page == 0:

        return "<b>Ключи</b>\n\nКлючей пока нет."

    if not has_keys:

        return "<b>Ключи</b>\n\nНа этой странице ключей нет."

    return f"<b>Ключи</b>\n\nСтраница {page+1}\nНажми на ключ чтобы удалить/отозвать."





def format_key_card(key) -> str:

    status = "активен" if key.is_active else "деактивирован"

    activated = f" | активирован {key.activated_by_telegram_id}" if key.activated_by_telegram_id else ""

    return (

        f"<b>Ключ #{key.id}</b>\n"

        f"Статус: <code>{status}{activated}</code>\n"

        f"Превью: <code>…{key.key_preview}</code>\n"

        f"Создан: <code>{key.created_at:%d.%m.%Y %H:%M}</code>"

    )





def format_users_list(page: int, has_users: bool) -> str:

    if not has_users and page == 0:

        return "<b>Пользователи с доступом</b>\n\nНикого нет."

    if not has_users:

        return "<b>Пользователи с доступом</b>\n\nНа этой странице пусто."

    return f"<b>Пользователи с доступом</b>\n\nСтраница {page+1}\nНажми на пользователя чтобы отозвать доступ."





def format_user_card(user) -> str:

    uname = f"@{user.username}" if user.username else "-"

    return (

        f"<b>Пользователь</b>\n"

        f"ID: <code>{user.telegram_id}</code>\n"

        f"Username: {uname}\n"

        f"Имя: {user.full_name or '-'}\n"

        f"Доступ выдан: <code>{user.access_granted_at:%d.%m.%Y %H:%M}</code>"

        if user.access_granted_at

        else f"<b>Пользователь</b>\nID: <code>{user.telegram_id}</code>"

    )





ADMIN_BROADCAST_PROMPT = "<b>Рассылка</b>\n\nОтправь текст для рассылки всем пользователям с доступом.\nПоддерживается HTML."

ADMIN_BROADCAST_CANCELLED = "Рассылка отменена."

ADMIN_BROADCAST_EMPTY = "Текст пустой."

ADMIN_BROADCAST_STARTED = "Начинаю рассылку..."





def format_broadcast_done(stats: dict) -> str:

    return (

        "<b>Рассылка завершена</b>\n"

        f"Всего: <code>{stats['total']}</code>\n"

        f"Отправлено: <code>{stats['sent']}</code>\n"

        f"Заблокировали: <code>{stats['blocked']}</code>\n"

        f"Ошибок: <code>{stats['failed']}</code>"

    )

