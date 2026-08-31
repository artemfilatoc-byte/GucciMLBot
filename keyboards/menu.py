from collections.abc import Sequence



from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



MENU = "menu"

PROFILE = "profile"

ACCOUNTS = "accounts"

CREATE_TOKENS = "create_tokens"

MY_TOKENS = "my_tokens"

ACCOUNT_IMPORT = "accounts:import"

ACCOUNT_IMPORT_CANCEL = "accounts:import_cancel"

ACCOUNTS_PROXY_UPLOAD = "accounts:proxy:upload"

ACCOUNTS_PROXY_CANCEL = "accounts:proxy:cancel"

ACCOUNTS_PAGE_PREFIX = "accounts:page:"

ACCOUNT_OPEN_PREFIX = "accounts:open:"

ACCOUNT_DELETE_PREFIX = "accounts:delete:"

ACCOUNT_DELETE_ALL_CONFIRM = "accounts:delete_all_confirm"

ACCOUNT_DELETE_ALL = "accounts:delete_all"

TOKEN_CREATE_CANCEL = "tokens:create:cancel"

TOKEN_CREATE_AVATAR_YES = "tokens:create:avatar:yes"

TOKEN_CREATE_AVATAR_NO = "tokens:create:avatar:no"

MY_TOKENS_PAGE_PREFIX = "tokens:list:page:"

MY_TOKEN_OPEN_PREFIX = "tokens:open:"

MY_TOKENS_EXPORT = "tokens:list:export"

MY_TOKEN_DELETE_PREFIX = "tokens:delete:"

MY_TOKENS_DELETE_ALL_CONFIRM = "tokens:delete_all_confirm"

MY_TOKENS_DELETE_ALL = "tokens:delete_all"

TOKEN_BATCH_PAGE_PREFIX = "tokens:batch:page:"

TOKEN_BATCH_EXPORT_PREFIX = "tokens:batch:export:"

TOKEN_BATCH_STOP_PREFIX = "tokens:batch:stop:"

MY_TOKEN_EDIT_PREFIX = "tokens:edit:open:"

TOKEN_EDIT_AVATAR_PREFIX = "tokens:edit:avatar:"

TOKEN_EDIT_NAME_PREFIX = "tokens:edit:name:"

TOKEN_EDIT_DESCRIPTION_PREFIX = "tokens:edit:desc:"

TOKEN_EDIT_SHORT_DESCRIPTION_PREFIX = "tokens:edit:short:"

TOKEN_EDIT_MENU_BUTTON_PREFIX = "tokens:edit:menu:"

BULK_AVATAR = "tokens:bulk_avatar"

BULK_AVATAR_BATCH_PREFIX = "tokens:bulk_avatar:batch:"

BULK_AVATAR_CANCEL = "tokens:bulk_avatar:cancel"

ACCOUNTS_CHECK = "accounts:check"





PROFILE = "profile"

PROFILE_RATING = "profile:rating"



def menu_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Профиль", callback_data=PROFILE)],

            [InlineKeyboardButton(text="Аккаунты", callback_data=ACCOUNTS)],

            [InlineKeyboardButton(text="Создать токены", callback_data=CREATE_TOKENS)],

            [InlineKeyboardButton(text="Мои токены", callback_data=MY_TOKENS)],

        ]

    )





def profile_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Рейтинг", callback_data=PROFILE_RATING)],

            [InlineKeyboardButton(text="Назад", callback_data=MENU)],

        ]

    )





def back_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Назад", callback_data=MENU)],

        ]

    )





def accounts_kb(

    accounts: Sequence[tuple[int, str]],

    page: int,

    has_prev: bool,

    has_next: bool,

    can_delete_all: bool,

) -> InlineKeyboardMarkup:

    rows: list[list[InlineKeyboardButton]] = []

    if can_delete_all:

        rows.append(

            [

                InlineKeyboardButton(

                    text="Проверить аккаунты",

                    callback_data=ACCOUNTS_CHECK,

                )

            ]

        )

        rows.append(

            [

                InlineKeyboardButton(

                    text="Удалить все аккаунты",

                    callback_data=ACCOUNT_DELETE_ALL_CONFIRM,

                )

            ]

        )

    rows.extend(

        [

            InlineKeyboardButton(

                text=title,

                callback_data=f"{ACCOUNT_OPEN_PREFIX}{account_id}:{page}",

            )

        ]

        for account_id, title in accounts

    )

    rows.append(

        [InlineKeyboardButton(text="Добавить аккаунты", callback_data=ACCOUNT_IMPORT)]

    )

    rows.append(

        [InlineKeyboardButton(text="Загрузить прокси", callback_data=ACCOUNTS_PROXY_UPLOAD)]

    )



    nav = []

    if has_prev:

        nav.append(

            InlineKeyboardButton(

                text="<",

                callback_data=f"{ACCOUNTS_PAGE_PREFIX}{page - 1}",

            )

        )

    nav.append(

        InlineKeyboardButton(

            text=f"{page + 1}",

            callback_data=f"{ACCOUNTS_PAGE_PREFIX}{page}",

        )

    )

    if has_next:

        nav.append(

            InlineKeyboardButton(

                text=">",

                callback_data=f"{ACCOUNTS_PAGE_PREFIX}{page + 1}",

            )

        )

    if has_prev or has_next:

        rows.append(nav)



    rows.append([InlineKeyboardButton(text="Назад", callback_data=MENU)])

    return InlineKeyboardMarkup(inline_keyboard=rows)





def account_card_kb(account_id: int, page: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Удалить",

                    callback_data=f"{ACCOUNT_DELETE_PREFIX}{account_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Назад",

                    callback_data=f"{ACCOUNTS_PAGE_PREFIX}{page}",

                )

            ],

        ]

    )





def account_import_cancel_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Отмена", callback_data=ACCOUNT_IMPORT_CANCEL)],

        ]

    )





def account_proxy_cancel_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Отмена", callback_data=ACCOUNTS_PROXY_CANCEL)],

        ]

    )





def account_delete_all_confirm_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Да, удалить все",

                    callback_data=ACCOUNT_DELETE_ALL,

                )

            ],

            [InlineKeyboardButton(text="Отмена", callback_data=ACCOUNTS)],

        ]

    )





def token_create_cancel_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Отмена", callback_data=TOKEN_CREATE_CANCEL)],

        ]

    )





def token_create_avatar_choice_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Да",

                    callback_data=TOKEN_CREATE_AVATAR_YES,

                ),

                InlineKeyboardButton(

                    text="Нет",

                    callback_data=TOKEN_CREATE_AVATAR_NO,

                ),

            ],

            [InlineKeyboardButton(text="Отмена", callback_data=TOKEN_CREATE_CANCEL)],

        ]

    )





def token_create_progress_kb(batch_id: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Стоп",

                    callback_data=f"{TOKEN_BATCH_STOP_PREFIX}{batch_id}",

                )

            ],

        ]

    )





def my_tokens_kb(

    created_bots: Sequence[tuple[int, str]],

    page: int,

    has_prev: bool,

    has_next: bool,

    can_delete_all: bool,

) -> InlineKeyboardMarkup:

    rows = [[InlineKeyboardButton(text="Выгрузить .txt", callback_data=MY_TOKENS_EXPORT)]]

    if can_delete_all:

        rows.append(

            [

                InlineKeyboardButton(

                    text="Поставить аватарку всем",

                    callback_data=BULK_AVATAR,

                )

            ]

        )

        rows.append(

            [

                InlineKeyboardButton(

                    text="Удалить все токены",

                    callback_data=MY_TOKENS_DELETE_ALL_CONFIRM,

                )

            ]

        )

    rows.extend(

        [

            InlineKeyboardButton(

                text=title,

                callback_data=f"{MY_TOKEN_OPEN_PREFIX}{created_bot_id}:{page}",

            )

        ]

        for created_bot_id, title in created_bots

    )



    nav = []

    if has_prev:

        nav.append(

            InlineKeyboardButton(

                text="<",

                callback_data=f"{MY_TOKENS_PAGE_PREFIX}{page - 1}",

            )

        )

    nav.append(

        InlineKeyboardButton(

            text=f"{page + 1}",

            callback_data=f"{MY_TOKENS_PAGE_PREFIX}{page}",

        )

    )

    if has_next:

        nav.append(

            InlineKeyboardButton(

                text=">",

                callback_data=f"{MY_TOKENS_PAGE_PREFIX}{page + 1}",

            )

        )

    if has_prev or has_next:

        rows.append(nav)



    rows.append([InlineKeyboardButton(text="Назад", callback_data=MENU)])

    return InlineKeyboardMarkup(inline_keyboard=rows)





def my_token_card_kb(created_bot_id: int, page: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Редактировать",

                    callback_data=f"{MY_TOKEN_EDIT_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Удалить",

                    callback_data=f"{MY_TOKEN_DELETE_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    callback_data=f"{MY_TOKENS_PAGE_PREFIX}{page}",

                    text="Назад",

                )

            ],

        ]

    )





def my_tokens_delete_all_confirm_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Да, удалить все",

                    callback_data=MY_TOKENS_DELETE_ALL,

                )

            ],

            [InlineKeyboardButton(text="Отмена", callback_data=MY_TOKENS)],

        ]

    )





def token_edit_kb(created_bot_id: int, page: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Сменить аватар",

                    callback_data=f"{TOKEN_EDIT_AVATAR_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Сменить имя",

                    callback_data=f"{TOKEN_EDIT_NAME_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Сменить описание",

                    callback_data=f"{TOKEN_EDIT_DESCRIPTION_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Сменить короткое описание",

                    callback_data=f"{TOKEN_EDIT_SHORT_DESCRIPTION_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Установить Menu Button",

                    callback_data=f"{TOKEN_EDIT_MENU_BUTTON_PREFIX}{created_bot_id}:{page}",

                )

            ],

            [

                InlineKeyboardButton(

                    text="Назад",

                    callback_data=f"{MY_TOKEN_OPEN_PREFIX}{created_bot_id}:{page}",

                )

            ],

        ]

    )





def token_edit_back_kb(created_bot_id: int, page: int) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="Назад",

                    callback_data=f"{MY_TOKEN_EDIT_PREFIX}{created_bot_id}:{page}",

                )

            ],

        ]

    )





def bulk_avatar_cancel_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [InlineKeyboardButton(text="Отмена", callback_data=BULK_AVATAR_CANCEL)],

        ]

    )





def token_batch_result_kb(

    batch_id: int,

    page: int,

    has_prev: bool,

    has_next: bool,

    can_export: bool,

) -> InlineKeyboardMarkup:

    rows: list[list[InlineKeyboardButton]] = []

    if can_export:

        rows.append(

            [

                InlineKeyboardButton(

                    text="Выгрузить .txt",

                    callback_data=f"{TOKEN_BATCH_EXPORT_PREFIX}{batch_id}",

                )

            ]

        )

        rows.append(

            [

                InlineKeyboardButton(

                    text="Поставить аватарку всем (батч)",

                    callback_data=f"{BULK_AVATAR_BATCH_PREFIX}{batch_id}",

                )

            ]

        )



    nav = []

    if has_prev:

        nav.append(

            InlineKeyboardButton(

                text="<",

                callback_data=f"{TOKEN_BATCH_PAGE_PREFIX}{batch_id}:{page - 1}",

            )

        )

    nav.append(

        InlineKeyboardButton(

            text=f"{page + 1}",

            callback_data=f"{TOKEN_BATCH_PAGE_PREFIX}{batch_id}:{page}",

        )

    )

    if has_next:

        nav.append(

            InlineKeyboardButton(

                text=">",

                callback_data=f"{TOKEN_BATCH_PAGE_PREFIX}{batch_id}:{page + 1}",

            )

        )

    if has_prev or has_next:

        rows.append(nav)



    rows.append([InlineKeyboardButton(text="Мои токены", callback_data=MY_TOKENS)])

    rows.append([InlineKeyboardButton(text="Назад", callback_data=MENU)])

    return InlineKeyboardMarkup(inline_keyboard=rows)

