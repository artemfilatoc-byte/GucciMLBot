from html import escape





def format_profile(

    username: str | None,

    full_name: str | None,

    telegram_id: int,

    my_total: int,

    my_day: int,

    my_week: int,

    my_accounts: int,

    global_total: int,

    global_day: int,

    global_week: int,

) -> str:

    uname = f"@{escape(username)}" if username else "—"

    name = escape(full_name) if full_name else "—"

    return "\n".join(

        [

            "<b>Профиль</b>",

            f"ID: <code>{telegram_id}</code>",

            f"Username: {uname}",

            f"Имя: {name}",

            "",

            "<b>Твои токены</b>",

            f"Всего: <code>{my_total}</code>",

            f"За день: <code>{my_day}</code>",

            f"За неделю: <code>{my_week}</code>",

            f"Аккаунтов: <code>{my_accounts}</code>",

            "",

            "<b>Всего в боте</b>",

            f"Токенов: <code>{global_total}</code>",

            f"За день: <code>{global_day}</code>",

            f"За неделю: <code>{global_week}</code>",

        ]

    )





def format_rating(top: list[tuple[int, str | None, str | None, int]]) -> str:

    if not top:

        return "<b>Рейтинг</b>\n\nПока никто не создал токенов."

    rows = ["<b>Рейтинг по токенам</b>", ""]

    for idx, (tid, username, full_name, cnt) in enumerate(top, 1):

        if username:

            title = f"@{escape(username)}"

        elif full_name:

            title = escape(full_name)

        else:

            title = str(tid)

        rows.append(f"{idx}. {title} — <code>{cnt}</code>")

    return "\n".join(rows)

