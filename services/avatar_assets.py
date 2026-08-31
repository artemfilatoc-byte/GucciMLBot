import random

from pathlib import Path



from core.config import BASE_DIR

from services.bot_editor import set_created_bot_avatar



AVATAR_ASSETS_DIR = BASE_DIR / "assets" / "emoji_avatars"

_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}





def list_avatar_asset_paths() -> list[Path]:

    if not AVATAR_ASSETS_DIR.exists():

        return []

    return [

        path

        for path in AVATAR_ASSETS_DIR.iterdir()

        if path.is_file() and path.suffix.lower() in _SUPPORTED_SUFFIXES

    ]





async def set_random_created_bot_avatar(bot_token: str) -> None:

    paths = list_avatar_asset_paths()

    if not paths:

        raise RuntimeError("папка с аватарками пустая")

    path = random.choice(paths)

    await set_created_bot_avatar(

        bot_token,

        path.read_bytes(),

        file_name=f"avatar{path.suffix.lower()}",

    )

