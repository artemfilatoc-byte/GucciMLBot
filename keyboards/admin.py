from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



ADMIN_CREATE_KEY = "admin:keys:create"

ADMIN_REFRESH = "admin:refresh"

ADMIN_KEYS_LIST = "admin:keys:list"

ADMIN_KEYS_PAGE_PREFIX = "admin:keys:page:"

ADMIN_KEY_DELETE_PREFIX = "admin:keys:delete:"

ADMIN_USERS_LIST = "admin:users:list"

ADMIN_USERS_PAGE_PREFIX = "admin:users:page:"

ADMIN_USER_REVOKE_PREFIX = "admin:users:revoke:"

ADMIN_BROADCAST = "admin:broadcast"

ADMIN_BROADCAST_CANCEL = "admin:broadcast:cancel"





def admin_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Создать ключ", callback_data=ADMIN_CREATE_KEY)],

            [InlineKeyboardButton(text="Список ключей", callback_data=ADMIN_KEYS_LIST)],

            [InlineKeyboardButton(text="Пользователи", callback_data=ADMIN_USERS_LIST)],

            [InlineKeyboardButton(text="Рассылка", callback_data=ADMIN_BROADCAST)],

            [InlineKeyboardButton(text="Обновить", callback_data=ADMIN_REFRESH)],

        ]

    )





def admin_keys_kb(keys, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:

    rows: list[list[InlineKeyboardButton]] = []

    for key in keys:

        status = "✅" if key.is_active and key.activated_at is None else ("🔑" if key.is_active else "❌")

        preview = key.key_preview or key.key_hash[:4]

        title = f"{status} #{key.id} …{preview}"

        if key.activated_by_telegram_id:

            title += f" -> {key.activated_by_telegram_id}"

        rows.append([InlineKeyboardButton(text=title, callback_data=f"{ADMIN_KEY_DELETE_PREFIX}{key.id}:{page}")])

    nav: list[InlineKeyboardButton] = []

    if has_prev:

        nav.append(InlineKeyboardButton(text="<", callback_data=f"{ADMIN_KEYS_PAGE_PREFIX}{page-1}"))

    nav.append(InlineKeyboardButton(text=f"{page+1}", callback_data=f"{ADMIN_KEYS_PAGE_PREFIX}{page}"))

    if has_next:

        nav.append(InlineKeyboardButton(text=">", callback_data=f"{ADMIN_KEYS_PAGE_PREFIX}{page+1}"))

    if has_prev or has_next:

        rows.append(nav)

    rows.append([InlineKeyboardButton(text="Назад", callback_data=ADMIN_REFRESH)])

    return InlineKeyboardMarkup(inline_keyboard=rows)





def admin_key_delete_confirm_kb(key_id: int, page: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Удалить/Отозвать", callback_data=f"{ADMIN_KEY_DELETE_PREFIX}{key_id}:{page}:confirm")],

            [InlineKeyboardButton(text="Отмена", callback_data=f"{ADMIN_KEYS_PAGE_PREFIX}{page}")],

        ]

    )





def admin_users_kb(users, page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:

    rows: list[list[InlineKeyboardButton]] = []

    for user in users:

        title = f"@{user.username}" if user.username else (user.full_name or str(user.telegram_id))

        title = title[:32]

        rows.append([InlineKeyboardButton(text=f"{title} ({user.telegram_id})", callback_data=f"{ADMIN_USER_REVOKE_PREFIX}{user.telegram_id}:{page}")])

    nav: list[InlineKeyboardButton] = []

    if has_prev:

        nav.append(InlineKeyboardButton(text="<", callback_data=f"{ADMIN_USERS_PAGE_PREFIX}{page-1}"))

    nav.append(InlineKeyboardButton(text=f"{page+1}", callback_data=f"{ADMIN_USERS_PAGE_PREFIX}{page}"))

    if has_next:

        nav.append(InlineKeyboardButton(text=">", callback_data=f"{ADMIN_USERS_PAGE_PREFIX}{page+1}"))

    if has_prev or has_next:

        rows.append(nav)

    rows.append([InlineKeyboardButton(text="Назад", callback_data=ADMIN_REFRESH)])

    return InlineKeyboardMarkup(inline_keyboard=rows)





def admin_user_revoke_confirm_kb(telegram_id: int, page: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Отозвать доступ", callback_data=f"{ADMIN_USER_REVOKE_PREFIX}{telegram_id}:{page}:confirm")],

            [InlineKeyboardButton(text="Отмена", callback_data=f"{ADMIN_USERS_PAGE_PREFIX}{page}")],

        ]

    )





def admin_broadcast_cancel_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[[InlineKeyboardButton(text="Отмена", callback_data=ADMIN_BROADCAST_CANCEL)]]

    )

