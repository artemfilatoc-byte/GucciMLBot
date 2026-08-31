from collections.abc import Awaitable, Callable, Sequence

from io import BytesIO

from urllib.parse import urlparse



from aiogram import Bot

from aiogram.types import MenuButtonWebApp, WebAppInfo

from telethon.sessions import MemorySession

from telethon.tl.functions.photos import UploadProfilePhotoRequest



from services.telegram_client import build_telegram_client



_DEFAULT_LANGUAGE_CODES: tuple[str | None, ...] = (None, "ru", "en")





async def set_created_bot_name(

    bot_token: str,

    name: str,

    language_codes: Sequence[str | None] = _DEFAULT_LANGUAGE_CODES,

) -> str:

    normalized = normalize_created_bot_name(name)

    await _run_bot_api_for_languages(

        bot_token,

        language_codes,

        lambda target_bot, language_code: target_bot.set_my_name(

            name=normalized,

            language_code=language_code,

        ),

    )

    return normalized





def normalize_created_bot_name(name: str) -> str:

    normalized = " ".join(name.strip().split())

    if not 1 <= len(normalized) <= 64:

        raise RuntimeError("имя бота должно быть от 1 до 64 символов")

    return normalized





async def set_created_bot_description(

    bot_token: str,

    description: str,

    language_codes: Sequence[str | None] = _DEFAULT_LANGUAGE_CODES,

) -> None:

    value = description.strip()

    if not value:

        raise RuntimeError("описание не может быть пустым")

    if len(value) > 512:

        raise RuntimeError("описание не может быть длиннее 512 символов")



    await _run_bot_api_for_languages(

        bot_token,

        language_codes,

        lambda target_bot, language_code: target_bot.set_my_description(

            description=value,

            language_code=language_code,

        ),

    )





async def set_created_bot_short_description(

    bot_token: str,

    short_description: str,

    language_codes: Sequence[str | None] = _DEFAULT_LANGUAGE_CODES,

) -> None:

    value = short_description.strip()

    if not value:

        raise RuntimeError("короткое описание не может быть пустым")

    if len(value) > 120:

        raise RuntimeError("короткое описание не может быть длиннее 120 символов")



    await _run_bot_api_for_languages(

        bot_token,

        language_codes,

        lambda target_bot, language_code: target_bot.set_my_short_description(

            short_description=value,

            language_code=language_code,

        ),

    )





async def set_created_bot_menu_button(

    bot_token: str,

    text: str,

    url: str,

) -> None:

    button_text = " ".join(text.strip().split())

    webapp_url = url.strip()

    if not 1 <= len(button_text) <= 64:

        raise RuntimeError("текст кнопки должен быть от 1 до 64 символов")

    if not _is_https_url(webapp_url):

        raise RuntimeError("URL должен начинаться с https://")



    target_bot = Bot(bot_token)

    try:

        ok = await target_bot.set_chat_menu_button(

            menu_button=MenuButtonWebApp(

                text=button_text,

                web_app=WebAppInfo(url=webapp_url),

            )

        )

        if not ok:

            raise RuntimeError("Telegram не принял Menu Button")

    finally:

        await target_bot.session.close()





async def set_created_bot_avatar(

    bot_token: str,

    photo: bytes,

    file_name: str = "avatar.jpg",

) -> None:

    if not photo:

        raise RuntimeError("фото пустое")



    client = build_telegram_client(MemorySession())

    try:

        await client.start(bot_token=bot_token)

        uploaded_file = await client.upload_file(

            BytesIO(photo),

            file_name=file_name,

        )

        await client(UploadProfilePhotoRequest(file=uploaded_file))

    finally:

        await client.disconnect()





async def _run_bot_api_for_languages(

    bot_token: str,

    language_codes: Sequence[str | None],

    method: Callable[[Bot, str | None], Awaitable[bool]],

) -> None:

    target_bot = Bot(bot_token)

    try:

        for language_code in language_codes:

            ok = await method(target_bot, language_code)

            if not ok:

                raise RuntimeError("Telegram не принял изменение")

    finally:

        await target_bot.session.close()





def parse_menu_button_input(value: str) -> tuple[str, str]:

    parts = value.strip().split()

    if len(parts) < 2:

        raise RuntimeError("отправь текст кнопки и URL через пробел")

    url = parts[-1]

    text = " ".join(parts[:-1])

    return text, url





def _is_https_url(value: str) -> bool:

    parsed = urlparse(value)

    return parsed.scheme == "https" and bool(parsed.netloc)

