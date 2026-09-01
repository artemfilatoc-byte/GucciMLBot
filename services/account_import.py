import asyncio

import shutil

import zipfile

from collections.abc import Awaitable, Callable

from dataclasses import dataclass

from pathlib import Path



from aiogram import Bot

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from aiogram.types import Document

from telethon import TelegramClient

from telethon.errors import RPCError

from telethon.sessions import SQLiteSession, StringSession



from core.config import (

    ACCOUNT_IMPORT_MAX_ARCHIVE_FILES,

    ACCOUNT_IMPORT_MAX_FILE_SIZE_MB,

    ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB,

    TELETHON_IMPORT_CONCURRENCY,

)

from core.temp_files import app_temp_dir

from repositories.account import TelegramAccountPayload, upsert_account

from services.telegram_client import build_telegram_client

from texts.accounts import format_import_error, format_import_progress, format_import_report



_semaphore = asyncio.Semaphore(TELETHON_IMPORT_CONCURRENCY)

_session_suffixes = {".session", ".txt"}

AccountImportProgressCallback = Callable[["AccountImportProgress"], Awaitable[None]]





@dataclass(frozen=True)

class SessionSource:

    filename: str

    path: Path

    is_string: bool

    error: str | None = None





@dataclass(frozen=True)

class AccountCheck:

    filename: str

    ok: bool

    created: bool = False

    duplicate: bool = False

    invalid: bool = False

    account_title: str | None = None

    error: str | None = None





@dataclass(frozen=True)

class AccountImportProgress:

    stage: str

    total: int

    processed: int

    created: int

    updated: int

    failed: int

    invalid: int

    in_progress: int

    current_file: str | None = None



    @property

    def remaining(self) -> int:

        return max(self.total - self.processed, 0)





async def import_account_document(

    bot: Bot,

    chat_id: int,

    owner_user_id: int,

    document: Document,

    progress_message_id: int | None = None,

) -> None:

    async def update_progress(progress: AccountImportProgress) -> None:

        await _edit_import_progress(bot, chat_id, progress_message_id, progress)



    try:

        results = await _import_account_document(

            bot,

            owner_user_id,

            document,

            update_progress,

        )

        await _edit_or_send_message(

            bot,

            chat_id,

            progress_message_id,

            format_import_report(results),

        )

    except Exception as exc:

        await _edit_or_send_message(

            bot,

            chat_id,

            progress_message_id,

            format_import_error(str(exc)),

        )





async def _import_account_document(

    bot: Bot,

    owner_user_id: int,

    document: Document,

    progress_callback: AccountImportProgressCallback | None,

) -> list[AccountCheck]:

    if document.file_size and document.file_size > _max_upload_bytes():

        raise RuntimeError(f"файл больше {ACCOUNT_IMPORT_MAX_FILE_SIZE_MB} МБ")



    await _emit_import_progress(

        progress_callback,

        AccountImportProgress(

            stage="Скачиваю файл",

            total=0,

            processed=0,

            created=0,

            updated=0,

            failed=0,

            invalid=0,

            in_progress=0,

            current_file=document.file_name,

        ),

    )



    with app_temp_dir("filya_accounts_") as temp_dir:

        upload_path = temp_dir / _safe_filename(document.file_name or "upload.session")

        await bot.download(document, destination=upload_path)

        await _emit_import_progress(

            progress_callback,

            AccountImportProgress(

                stage="Распаковываю файл",

                total=0,

                processed=0,

                created=0,

                updated=0,

                failed=0,

                invalid=0,

                in_progress=0,

                current_file=document.file_name,

            ),

        )

        sources = await asyncio.to_thread(_collect_sources, upload_path, temp_dir)

        if not sources:

            raise RuntimeError("внутри нет .session или .txt файлов")

        return await _check_sources(owner_user_id, sources, progress_callback)





async def _check_sources(

    owner_user_id: int,

    sources: list[SessionSource],

    progress_callback: AccountImportProgressCallback | None,

) -> list[AccountCheck]:

    results: list[AccountCheck] = []

    total = len(sources)

    await _emit_import_progress(

        progress_callback,

        _build_import_progress("Проверяю аккаунты", total, results),

    )

    tasks = [

        asyncio.create_task(_check_and_save(owner_user_id, source))

        for source in sources

    ]

    for task in asyncio.as_completed(tasks):

        result = await task

        results.append(result)

        await _emit_import_progress(

            progress_callback,

            _build_import_progress(

                "Проверяю аккаунты",

                total,

                results,

                result.filename,

            ),

        )

    return results





async def _check_and_save(owner_user_id: int, source: SessionSource) -> AccountCheck:

    async with _semaphore:

        if source.error is not None:

            return AccountCheck(filename=source.filename, ok=False, error=source.error)

        try:

            payload = await _read_account(source)

            save_status = await upsert_account(owner_user_id, payload)

            if save_status == "duplicate":

                return AccountCheck(

                    filename=source.filename,

                    ok=False,

                    duplicate=True,

                    account_title=_account_title(payload),

                    error="аккаунт уже есть в базе",

                )

            return AccountCheck(

                filename=source.filename,

                ok=True,

                created=save_status == "created",

                account_title=_account_title(payload),

            )

        except Exception as exc:

            return AccountCheck(

                filename=source.filename,

                ok=False,

                invalid=_is_invalid_account_error(exc),

                error=str(exc),

            )





async def _read_account(source: SessionSource) -> TelegramAccountPayload:

    session = _build_session(source)

    client: TelegramClient = build_telegram_client(session)

    try:

        await client.connect()

        if not await client.is_user_authorized():

            raise RuntimeError("сессия не авторизована")

        me = await client.get_me()

        if me is None:

            raise RuntimeError("не удалось получить профиль")

        session_string = StringSession.save(client.session)

        if not session_string:

            raise RuntimeError("не удалось сохранить строковую сессию")

        return TelegramAccountPayload(

            telegram_id=int(me.id),

            phone=getattr(me, "phone", None),

            username=getattr(me, "username", None),

            first_name=getattr(me, "first_name", None),

            last_name=getattr(me, "last_name", None),

            session_string=session_string,

            dc_id=getattr(client.session, "dc_id", None),

        )

    except RPCError as exc:

        raise RuntimeError(exc.__class__.__name__) from exc

    finally:

        await client.disconnect()





def _build_session(source: SessionSource) -> SQLiteSession | StringSession:

    if source.is_string:

        value = source.path.read_text(encoding="utf-8").strip()

        if not value:

            raise RuntimeError("пустая строковая сессия")

        return StringSession(value)

    return SQLiteSession(str(source.path))





def _collect_sources(upload_path: Path, temp_dir: Path) -> list[SessionSource]:

    suffix = upload_path.suffix.lower()

    if suffix == ".zip":

        return _extract_zip(upload_path, temp_dir / "archive")

    return [_plain_source(upload_path)]





def _extract_zip(archive_path: Path, target_dir: Path) -> list[SessionSource]:

    try:

        archive = zipfile.ZipFile(archive_path)

    except zipfile.BadZipFile as exc:

        raise RuntimeError("архив повреждён или не является zip") from exc



    sources: list[SessionSource] = []

    target_dir.mkdir(parents=True, exist_ok=True)

    with archive:

        for info in archive.infolist():

            if info.is_dir():

                continue

            filename = _safe_filename(info.filename)

            if Path(filename).suffix.lower() not in _session_suffixes:

                continue

            if len(sources) >= ACCOUNT_IMPORT_MAX_ARCHIVE_FILES:

                raise RuntimeError(

                    f"в архиве больше {ACCOUNT_IMPORT_MAX_ARCHIVE_FILES} файлов"

                )

            if info.file_size > _max_session_bytes():

                sources.append(

                    SessionSource(

                        filename=filename,

                        path=archive_path,

                        is_string=False,

                        error=f"файл больше {ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB} МБ",

                    )

                )

                continue

            target = target_dir / f"{len(sources)}_{filename}"

            with archive.open(info) as source_file, target.open("wb") as target_file:

                shutil.copyfileobj(source_file, target_file)

            sources.append(_plain_source(target, filename=filename))

    return sources





def _plain_source(path: Path, filename: str | None = None) -> SessionSource:

    if path.stat().st_size > _max_session_bytes():

        raise RuntimeError(

            f"{path.name}: файл больше {ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB} МБ"

        )

    suffix = path.suffix.lower()

    if suffix not in _session_suffixes:

        raise RuntimeError(f"{path.name}: нужен .session, .txt или .zip")

    return SessionSource(

        filename=filename or path.name,

        path=path,

        is_string=suffix == ".txt",

    )





def _account_title(payload: TelegramAccountPayload) -> str:

    if payload.phone:

        return f"+{payload.phone.lstrip('+')}"

    if payload.username:

        return f"@{payload.username}"

    name = " ".join(filter(None, [payload.first_name, payload.last_name]))

    return name or str(payload.telegram_id)





async def _emit_import_progress(

    progress_callback: AccountImportProgressCallback | None,

    progress: AccountImportProgress,

) -> None:

    if progress_callback is not None:

        await progress_callback(progress)





def _build_import_progress(

    stage: str,

    total: int,

    results: list[AccountCheck],

    current_file: str | None = None,

) -> AccountImportProgress:

    processed = len(results)

    remaining = max(total - processed, 0)

    return AccountImportProgress(

        stage=stage,

        total=total,

        processed=processed,

        created=sum(1 for result in results if result.ok and result.created),

        updated=sum(1 for result in results if result.ok and not result.created),

        failed=sum(1 for result in results if not result.ok),

        invalid=sum(1 for result in results if result.invalid),

        in_progress=min(remaining, TELETHON_IMPORT_CONCURRENCY),

        current_file=current_file,

    )





def _is_invalid_account_error(exc: Exception) -> bool:

    message = str(exc).casefold()

    name = exc.__class__.__name__.casefold()

    markers = (

        "сессия не авторизована",

        "пустая строковая сессия",

        "authkey",

        "unauthorized",

        "sessionrevoked",

        "sessionexpired",

        "userdeactivated",

    )

    return any(marker in message or marker in name for marker in markers)





async def _edit_import_progress(

    bot: Bot,

    chat_id: int,

    message_id: int | None,

    progress: AccountImportProgress,

) -> None:

    if message_id is None:

        return

    try:

        await bot.edit_message_text(

            chat_id=chat_id,

            message_id=message_id,

            text=format_import_progress(progress),

        )

    except (TelegramBadRequest, TelegramRetryAfter):

        return





async def _edit_or_send_message(

    bot: Bot,

    chat_id: int,

    message_id: int | None,

    text: str,

) -> None:

    if message_id is None:

        await bot.send_message(chat_id, text)

        return

    try:

        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)

        return

    except TelegramRetryAfter as exc:

        await asyncio.sleep(exc.retry_after)

        try:

            await bot.edit_message_text(

                chat_id=chat_id,

                message_id=message_id,

                text=text,

            )

            return

        except TelegramBadRequest as retry_exc:

            if "message is not modified" in str(retry_exc).casefold():

                return

            return

        except TelegramRetryAfter:

            return

    except TelegramBadRequest as exc:

        if "message is not modified" in str(exc).casefold():

            return

        return

    await bot.send_message(chat_id, text)





def _safe_filename(filename: str) -> str:

    clean = Path(filename.replace("\\", "/")).name

    return clean or "session.session"





def _max_upload_bytes() -> int:

    return ACCOUNT_IMPORT_MAX_FILE_SIZE_MB * 1024 * 1024





def _max_session_bytes() -> int:

    return ACCOUNT_IMPORT_MAX_SESSION_FILE_SIZE_MB * 1024 * 1024

