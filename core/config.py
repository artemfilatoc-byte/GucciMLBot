import os

from dataclasses import dataclass

from pathlib import Path



from dotenv import load_dotenv



BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")



BOT_TOKEN = os.environ["BOT_TOKEN"]





def _optional_int_set(name: str) -> frozenset[int]:

    raw_value = os.environ.get(name, "")

    values: set[int] = set()

    for part in raw_value.replace(";", ",").split(","):

        value = part.strip()

        if not value:

            continue

        try:

            values.add(int(value))

        except ValueError as exc:

            raise RuntimeError(f"{name} must contain integer Telegram IDs") from exc

    return frozenset(values)





def _optional_int(name: str, default: int) -> int:

    value = os.environ.get(name)

    if value is None:

        return default

    try:

        return int(value)

    except ValueError as exc:

        raise RuntimeError(f"{name} must be an integer") from exc



def _optional_path(name: str, default: Path) -> Path:

    value = os.environ.get(name)

    if value is None:

        return default.resolve()

    path = Path(value).expanduser()

    return path.resolve() if path.is_absolute() else (BASE_DIR / path).resolve()



APP_TEMP_DIR = _optional_path("APP_TEMP_DIR", BASE_DIR / ".runtime" / "tmp")



def get_app_temp_dir() -> Path:

    APP_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    return APP_TEMP_DIR





@dataclass(frozen=True)

class TelethonCredentials:

    api_id: int

    api_hash: str

    device_model: str

    system_version: str

    app_version: str

    lang_code: str

    system_lang_code: str





TELETHON_API_ID = (

    os.environ.get("TG_API_ID")

    or os.environ.get("TELETHON_API_ID")

    or os.environ.get("TELEGRAM_API_ID")

)

TELETHON_API_HASH = (

    os.environ.get("TG_API_HASH")

    or os.environ.get("TELETHON_API_HASH")

    or os.environ.get("TELEGRAM_API_HASH")

)

TG_DEVICE_MODEL = os.environ.get("TG_DEVICE_MODEL", "Desktop")

TG_SYSTEM_VERSION = os.environ.get("TG_SYSTEM_VERSION", "Windows")

TG_APP_VERSION = os.environ.get("TG_APP_VERSION", "1.0")

TG_LANG_CODE = os.environ.get("TG_LANG_CODE", "en")

TG_SYSTEM_LANG_CODE = os.environ.get("TG_SYSTEM_LANG_CODE", TG_LANG_CODE)

TELETHON_CONNECT_TIMEOUT = _optional_int("TELETHON_CONNECT_TIMEOUT", 20)

TELETHON_IMPORT_CONCURRENCY = _optional_int("TELETHON_IMPORT_CONCURRENCY", 3)

ACCOUNT_IMPORT_MAX_FILE_SIZE_MB = _optional_int("ACCOUNT_IMPORT_MAX_FILE_SIZE_MB", 50)

ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB = _optional_int(

    "ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB", 20

)

ACCOUNT_IMPORT_MAX_ARCHIVE_FILES = _optional_int("ACCOUNT_IMPORT_MAX_ARCHIVE_FILES", 50)

BOT_CREATE_CONCURRENCY = _optional_int("BOT_CREATE_CONCURRENCY", 2)

BOT_CREATE_MAX_COUNT = _optional_int("BOT_CREATE_MAX_COUNT", 50)

BOT_USERNAME_MAX_ATTEMPTS = _optional_int("BOT_USERNAME_MAX_ATTEMPTS", 300)

BOT_CREATE_DELAY_MIN_SECONDS = _optional_int("BOT_CREATE_DELAY_MIN_SECONDS", 15)

BOT_CREATE_DELAY_MAX_SECONDS = _optional_int("BOT_CREATE_DELAY_MAX_SECONDS", 25)

BOTFATHER_RETRY_MAX_SECONDS = _optional_int("BOTFATHER_RETRY_MAX_SECONDS", 1000)

BOTFATHER_USERNAME = (

    os.environ.get("BOTFATHER_USERNAME", "BotFather").strip().removeprefix("@")

    or "BotFather"

)

BOTFATHER_TIMEOUT_SECONDS = _optional_int("BOTFATHER_TIMEOUT_SECONDS", 120)

ADMIN_IDS = _optional_int_set("ADMIN_IDS")





def get_telethon_credentials() -> TelethonCredentials:

    if not TELETHON_API_ID or not TELETHON_API_HASH:

        raise RuntimeError("TG_API_ID and TG_API_HASH are required")

    try:

        api_id = int(TELETHON_API_ID)

    except ValueError as exc:

        raise RuntimeError("TG_API_ID must be an integer") from exc

    return TelethonCredentials(

        api_id=api_id,

        api_hash=TELETHON_API_HASH,

        device_model=TG_DEVICE_MODEL,

        system_version=TG_SYSTEM_VERSION,

        app_version=TG_APP_VERSION,

        lang_code=TG_LANG_CODE,

        system_lang_code=TG_SYSTEM_LANG_CODE,

    )



_database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

_sqlite_prefix = "sqlite+aiosqlite:///"

_sqlite_path = _database_url.removeprefix(_sqlite_prefix)

DATABASE_URL = (

    f"{_sqlite_prefix}{(BASE_DIR / _sqlite_path).resolve().as_posix()}"

    if _database_url.startswith(_sqlite_prefix)

    and _sqlite_path != ":memory:"

    and not Path(_sqlite_path).is_absolute()

    else _database_url

)

