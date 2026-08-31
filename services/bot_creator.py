import asyncio

import logging

import random

import re

from collections.abc import Awaitable, Callable, Iterator, Sequence

from contextlib import suppress

from dataclasses import dataclass, field

from typing import Protocol, TypeVar, cast



from telethon import TelegramClient

from telethon import errors as telethon_errors

from telethon.errors import RPCError

from telethon.sessions import StringSession

from telethon.tl.functions import account as account_funcs

from telethon.tl.functions import bots



from core.config import (

    BOT_CREATE_CONCURRENCY,

    BOT_CREATE_DELAY_MAX_SECONDS,

    BOT_CREATE_DELAY_MIN_SECONDS,

    BOT_CREATE_MAX_COUNT,

    BOT_USERNAME_MAX_ATTEMPTS,

    BOTFATHER_RETRY_MAX_SECONDS,

    BOTFATHER_TIMEOUT_SECONDS,

    BOTFATHER_USERNAME,

)

from models import TelegramAccount

from repositories.account import get_account, list_all_accounts

from repositories.created_bot import CreatedBotPayload, upsert_created_bot

from services.avatar_assets import set_random_created_bot_avatar

from services.telegram_client import build_telegram_client



logger = logging.getLogger(__name__)



_final_username_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]*[Bb][Oo][Tt]$")

_base_username_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]{1,27}$")

_extra_username_pattern = re.compile(r"^[A-Za-z0-9_]{1,32}$")

_bot_token_pattern = re.compile(r"\b\d{5,}:[A-Za-z0-9_-]{20,}\b")

_botfather_retry_after_pattern = re.compile(

    r"try\s+again\s+in\s+(\d+)\s+seconds?",

    re.IGNORECASE,

)

_semaphore = asyncio.Semaphore(BOT_CREATE_CONCURRENCY)

_account_locks: dict[int, asyncio.Lock] = {}

_db_write_lock = asyncio.Lock()

_BOT_BATCH_ITEM_TIMEOUT = 180

_ACCOUNT_CONNECT_TIMEOUT = 30

_LONG_BOTFATHER_RETRY_SECONDS = 60

_account_unavailable_errors = {

    "AuthKeyDuplicatedError",

    "AuthKeyError",

    "AuthKeyInvalidError",

    "AuthKeyNotFound",

    "AuthKeyPermEmptyError",

    "AuthKeyUnregisteredError",

    "InputUserDeactivatedError",

    "SessionExpiredError",

    "SessionRevokedError",

    "UnauthorizedError",

    "UserDeactivatedBanError",

    "UserDeactivatedError",

}

_username_unavailable_errors = {

    "UsernameInvalidError",

    "UsernameOccupiedError",

    "UsernameSuffixMissingError",

}

_botfather_username_error_markers = (

    "already taken",

    "invalid",

    "not available",

    "occupied",

    "sorry, this username",

    "taken",

)

_botfather_limit_error_markers = (

    "create too many bots",

    "created too many bots",

    "limit",

    "too many",

)

_bot_name_extra_words_per_bot = 4

_account_unavailable_message = "аккаунт стал нерабочий, создание токена отменено"

_T = TypeVar("_T")

BotBatchProgressCallback = Callable[["BotBatchProgress"], Awaitable[None]]

BotBatchItemCallback = Callable[["BotBatchItem"], Awaitable[None]]

BotBatchShouldStopCallback = Callable[[], Awaitable[bool]]

BotFatherWaitCallback = Callable[[int], Awaitable[None]]





class BotFatherConversation(Protocol):

    async def send_message(self, message: str) -> object:

        ...



    async def get_response(

        self,

        message: object | None = None,

        *,

        timeout: int | None = None,

    ) -> object:

        ...





class AccountUnavailableError(RuntimeError):

    pass





class UsernameUnavailableError(RuntimeError):

    pass





class BotFatherRetryAfterError(RuntimeError):

    def __init__(self, seconds: int) -> None:

        super().__init__(f"BotFather просит подождать {seconds} сек.")

        self.seconds = seconds





class AccountCreateLimitedError(RuntimeError):

    def __init__(self, seconds: int) -> None:

        super().__init__(

            f"BotFather просит подождать {seconds} сек., аккаунт пропущен"

        )

        self.seconds = seconds





class BatchStoppedError(RuntimeError):

    pass





@dataclass(frozen=True)

class BotCreateResult:

    created_bot_id: int

    name: str

    username: str

    token: str





@dataclass(frozen=True)

class BotBatchProgress:

    accounts_total: int

    accounts_active: int

    requested: int

    processed: int

    created: int

    failed: int

    in_progress: int

    waiting_accounts: int = 0

    current_account_title: str | None = None

    wait_remaining_seconds: int | None = None

    wait_reason: str | None = None



    @property

    def remaining(self) -> int:

        return max(self.requested - self.processed - self.in_progress, 0)





@dataclass(frozen=True)

class BotBatchItem:

    index: int

    ok: bool

    account_title: str

    name: str

    created_bot_id: int | None = None

    account_id: int | None = None

    username: str | None = None

    token: str | None = None

    error: str | None = None





@dataclass(frozen=True)

class BotBatchCreateResult:

    requested: int

    items: Sequence[BotBatchItem]



    @property

    def created(self) -> int:

        return sum(1 for item in self.items if item.ok)



    @property

    def failed(self) -> int:

        return sum(1 for item in self.items if not item.ok)





@dataclass

class _BatchRuntimeState:

    accounts_total: int

    requested: int

    base_bot_name: str

    extra_usernames: tuple[str, ...]

    items: list[BotBatchItem]

    active_account_ids: set[int]

    in_progress: int = 0

    waiting_accounts: dict[int, tuple[str, int, str | None]] = field(default_factory=dict)

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)





class UsernameCandidateSelector:

    def __init__(

        self,

        base_usernames: Sequence[str],

        extra_usernames: Sequence[str],

    ) -> None:

        self._candidates = _iter_username_candidates(base_usernames, extra_usernames)

        self._reserved: set[str] = set()

        self._lock = asyncio.Lock()



    async def next_available(self, client: TelegramClient) -> str:

        async with self._lock:

            attempts = 0

            while attempts < BOT_USERNAME_MAX_ATTEMPTS:

                candidate = next(self._candidates)

                key = candidate.casefold()

                if key in self._reserved:

                    continue

                attempts += 1

                if await _check_username_available(client, candidate):

                    self._reserved.add(key)

                    return candidate

            raise RuntimeError("не удалось подобрать свободный username")



    def reserve(self, username: str) -> None:

        self._reserved.add(username.casefold())





async def create_bot_via_botfather(

    owner_user_id: int,

    account_id: int,

    name: str,

    username: str,

) -> BotCreateResult:

    async with _semaphore:

        return await _create_bot_via_botfather(

            owner_user_id,

            account_id,

            name,

            username,

        )





async def create_bots_via_botfather(

    owner_user_id: int,

    name: str,

    base_username: str | Sequence[str],

    amount: int,

    extra_usernames: Sequence[str],

    account_limit: int | None = None,

    set_avatars: bool = False,

    initial_items: Sequence["BotBatchItem"] = (),

    progress_callback: BotBatchProgressCallback | None = None,

    item_callback: BotBatchItemCallback | None = None,

    should_stop_callback: BotBatchShouldStopCallback | None = None,

) -> BotBatchCreateResult:

    async with _semaphore:

        return await _create_bots_via_botfather(

            owner_user_id,

            name,

            base_username,

            amount,

            extra_usernames,

            account_limit,

            set_avatars,

            initial_items,

            progress_callback,

            item_callback,

            should_stop_callback,

        )





async def _create_bot_via_botfather(

    owner_user_id: int,

    account_id: int,

    name: str,

    username: str,

) -> BotCreateResult:

    account = await get_account(owner_user_id, account_id)

    if account is None:

        raise RuntimeError("аккаунт не найден")



    bot_name = normalize_bot_name(name)

    bot_username = normalize_bot_username(username)

    user_client = build_telegram_client(

        StringSession(account.session_string), getattr(account, "proxy_url", None)

    )



    try:

        async with _get_account_lock(account.id):

            await _ensure_account_available(user_client)

            if not await _check_username_available(user_client, bot_username):

                raise RuntimeError("username занят или недоступен")

            return await _create_bot_with_username(

                owner_user_id,

                account,

                user_client,

                bot_name,

                bot_username,

            )

    except AccountUnavailableError as exc:

        raise RuntimeError(_account_unavailable_message) from exc

    except UsernameUnavailableError as exc:

        raise RuntimeError("username занят или недоступен") from exc

    except RPCError as exc:

        raise RuntimeError(_format_rpc_error(exc)) from exc

    finally:

        await user_client.disconnect()





async def _create_bots_via_botfather(

    owner_user_id: int,

    name: str,

    base_username: str | Sequence[str],

    amount: int,

    extra_usernames: Sequence[str],

    account_limit: int | None,

    set_avatars: bool,

    initial_items: Sequence[BotBatchItem],

    progress_callback: BotBatchProgressCallback | None,

    item_callback: BotBatchItemCallback | None,

    should_stop_callback: BotBatchShouldStopCallback | None,

) -> BotBatchCreateResult:

    bot_count = normalize_bot_count(amount)

    extras = tuple(normalize_extra_usernames(extra_usernames))

    base_bot_name = normalize_bot_name(name)

    for index in range(1, bot_count + 1):

        build_bot_display_name(base_bot_name, extras, index)

    normalized_base_usernames = normalize_base_usernames(base_username)

    accounts = await list_all_accounts(owner_user_id)

    if not accounts:

        await _emit_batch_progress(

            progress_callback,

            _build_batch_progress(0, 0, bot_count, [], 0),

        )

        raise RuntimeError("сначала добавь рабочие аккаунты")

    if account_limit is not None:

        accounts = accounts[:normalize_account_use_count(account_limit, len(accounts))]



    selector = UsernameCandidateSelector(normalized_base_usernames, extras)

    work_queue: asyncio.Queue[int] = asyncio.Queue()

    existing_positions = {item.index for item in initial_items}

    for index in range(1, bot_count + 1):

        if index not in existing_positions:

            work_queue.put_nowait(index)

    state = _BatchRuntimeState(

        accounts_total=len(accounts),

        requested=bot_count,

        base_bot_name=base_bot_name,

        extra_usernames=extras,

        items=list(initial_items),

        active_account_ids={account.id for account in accounts},

    )

    await _emit_runtime_progress(progress_callback, state)



    workers = [

        asyncio.create_task(

            _run_account_batch_worker(

                owner_user_id,

                account,

                selector,

                state,

                work_queue,

                set_avatars,

                progress_callback,

                item_callback,

                should_stop_callback,

            )

        )

        for account in accounts

    ]

    await asyncio.gather(*workers)



    return BotBatchCreateResult(

        requested=bot_count,

        items=sorted(state.items, key=lambda item: item.index),

    )





async def _run_account_batch_worker(

    owner_user_id: int,

    account: TelegramAccount,

    selector: UsernameCandidateSelector,

    state: _BatchRuntimeState,

    work_queue: asyncio.Queue[int],

    set_avatars: bool,

    progress_callback: BotBatchProgressCallback | None,

    item_callback: BotBatchItemCallback | None,

    should_stop_callback: BotBatchShouldStopCallback | None,

) -> None:

    account_title = _account_title(account)

    cooldown_until = 0.0

    while True:

        if should_stop_callback is not None and await should_stop_callback():

            return

        index = await _get_next_batch_index(work_queue, state)

        if index is None:

            return

        if should_stop_callback is not None and await should_stop_callback():

            work_queue.put_nowait(index)

            return

        wait_seconds = cooldown_until - asyncio.get_running_loop().time()

        if wait_seconds > 0:

            work_queue.put_nowait(index)

            await _sleep_before_next_account_bot(

                progress_callback,

                state,

                work_queue,

                account.id,

                account_title,

                int(wait_seconds) + 1,

            )

            continue

        async def update_botfather_wait(remaining_seconds: int) -> None:

            await _set_account_wait(

                progress_callback,

                state,

                account.id,

                account_title,

                remaining_seconds,

                "BotFather просит подождать",

            )

            if (

                remaining_seconds > 0

                and should_stop_callback is not None

                and await should_stop_callback()

            ):

                raise BatchStoppedError



        bot_name = build_bot_display_name(

            state.base_bot_name,

            state.extra_usernames,

            index,

        )

        await _mark_batch_item_started(progress_callback, state, account_title)

        try:

            item = await _create_batch_item(

                owner_user_id,

                account,

                selector,

                bot_name,

                index,

                set_avatars,

                update_botfather_wait,

            )

        except BatchStoppedError:

            await _mark_batch_item_cancelled(progress_callback, state, account.id)

            return

        except AccountUnavailableError:

            await _drop_batch_account(

                progress_callback,

                item_callback,

                state,

                work_queue,

                account,

                index,

                _account_unavailable_message,

            )

            return

        except AccountCreateLimitedError as exc:

            await _drop_batch_account(

                progress_callback,

                item_callback,

                state,

                work_queue,

                account,

                index,

                str(exc),

            )

            return

        except RPCError as exc:

            await _append_batch_item(

                progress_callback,

                item_callback,

                state,

                BotBatchItem(

                    index=index,

                    ok=False,

                    account_title=account_title,

                    name=bot_name,

                    account_id=account.id,

                    error=_format_rpc_error(exc),

                ),

            )

        except Exception as exc:

            await _append_batch_item(

                progress_callback,

                item_callback,

                state,

                BotBatchItem(

                    index=index,

                    ok=False,

                    account_title=account_title,

                    name=bot_name,

                    account_id=account.id,

                    error=str(exc),

                ),

            )

        else:

            await _append_batch_item(progress_callback, item_callback, state, item)

        cooldown_until = asyncio.get_running_loop().time() + _next_create_delay()





async def _create_batch_item(

    owner_user_id: int,

    account: TelegramAccount,

    selector: UsernameCandidateSelector,

    bot_name: str,

    index: int,

    set_avatars: bool,

    botfather_wait_callback: BotFatherWaitCallback | None = None,

) -> BotBatchItem:

    user_client = build_telegram_client(

        StringSession(account.session_string), getattr(account, "proxy_url", None)

    )

    try:

        async with _get_account_lock(account.id):

            try:

                await asyncio.wait_for(

                    _ensure_account_available(user_client),

                    timeout=_ACCOUNT_CONNECT_TIMEOUT + 10,

                )

            except asyncio.TimeoutError as exc:

                raise AccountUnavailableError from exc

            for _ in range(10):

                try:

                    bot_username = await asyncio.wait_for(

                        selector.next_available(user_client),

                        timeout=30,

                    )

                except asyncio.TimeoutError as exc:

                    raise RuntimeError("таймаут подбора username") from exc

                try:

                    result = await asyncio.wait_for(

                        _create_bot_with_username(

                            owner_user_id,

                            account,

                            user_client,

                            bot_name,

                            bot_username,

                            set_avatars,

                            botfather_wait_callback,

                        ),

                        timeout=_BOT_BATCH_ITEM_TIMEOUT,

                    )

                    return BotBatchItem(

                        index=index,

                        ok=True,

                        account_title=_account_title(account),

                        name=result.name,

                        created_bot_id=result.created_bot_id,

                        account_id=account.id,

                        username=result.username,

                        token=result.token,

                    )

                except asyncio.TimeoutError as exc:

                    raise RuntimeError("таймаут создания бота через BotFather") from exc

                except UsernameUnavailableError:

                    selector.reserve(bot_username)

            raise RuntimeError("не удалось подобрать свободный username")

    finally:

        with suppress(Exception):

            await user_client.disconnect()





async def _create_bot_with_username(

    owner_user_id: int,

    account: TelegramAccount,

    user_client: TelegramClient,

    bot_name: str,

    bot_username: str,

    set_avatars: bool = False,

    botfather_wait_callback: BotFatherWaitCallback | None = None,

) -> BotCreateResult:

    try:

        token = await _request_bot_token_from_botfather(

            user_client,

            bot_name,

            bot_username,

            botfather_wait_callback,

        )

    except UsernameUnavailableError:

        raise

    except Exception as exc:

        if _is_account_unavailable_error(exc):

            raise AccountUnavailableError from exc

        raise



    created_bot = await upsert_created_bot(

        owner_user_id,

        CreatedBotPayload(

            account_id=account.id,

            bot_telegram_id=_bot_id_from_token(token),

            name=bot_name,

            username=bot_username,

            token=token,

            manager_bot_id=None,

        ),

    )

    await _set_created_bot_avatar_if_needed(token, set_avatars)

    return BotCreateResult(

        created_bot_id=created_bot.id,

        name=bot_name,

        username=bot_username,

        token=token,

    )





async def _set_created_bot_avatar_if_needed(bot_token: str, set_avatars: bool) -> None:

    if not set_avatars:

        return

    try:

        await set_random_created_bot_avatar(bot_token)

    except Exception:

        logger.warning("Failed to set random bot avatar", exc_info=True)





async def _request_bot_token_from_botfather(

    client: TelegramClient,

    bot_name: str,

    bot_username: str,

    wait_callback: BotFatherWaitCallback | None = None,

) -> str:

    while True:

        try:

            return await asyncio.wait_for(

                _request_bot_token_from_botfather_once(

                    client,

                    bot_name,

                    bot_username,

                ),

                timeout=BOTFATHER_TIMEOUT_SECONDS + 30,

            )

        except BotFatherRetryAfterError as exc:

            if exc.seconds > BOTFATHER_RETRY_MAX_SECONDS or exc.seconds > _LONG_BOTFATHER_RETRY_SECONDS:

                raise AccountCreateLimitedError(exc.seconds) from exc

            await _sleep_botfather_retry(wait_callback, exc.seconds)

        except asyncio.TimeoutError as exc:

            raise RuntimeError("BotFather не ответил вовремя") from exc





async def _sleep_botfather_retry(

    wait_callback: BotFatherWaitCallback | None,

    delay_seconds: int,

) -> None:

    remaining = max(delay_seconds, 1)

    while remaining > 0:

        if wait_callback is not None:

            await wait_callback(remaining)

        sleep_seconds = min(5, remaining)

        await asyncio.sleep(sleep_seconds)

        remaining -= sleep_seconds

    if wait_callback is not None:

        await wait_callback(0)





async def _request_bot_token_from_botfather_once(

    client: TelegramClient,

    bot_name: str,

    bot_username: str,

) -> str:

    try:

        async with client.conversation(

            f"@{BOTFATHER_USERNAME}",

            timeout=BOTFATHER_TIMEOUT_SECONDS,

            exclusive=False,

        ) as conversation:

            dialog = cast(BotFatherConversation, conversation)

            await _send_and_wait_botfather(dialog, "/start")

            await _cancel_botfather(dialog)

            await _sleep_botfather_step()

            newbot_response = await _send_and_wait_botfather(dialog, "/newbot")

            _raise_if_botfather_limit(newbot_response)

            await _sleep_botfather_step()

            name_response = await _send_and_wait_botfather(dialog, bot_name)

            _raise_if_botfather_limit(name_response)

            await _sleep_botfather_step()

            username_response = await _send_and_wait_botfather(dialog, bot_username)

            _raise_if_botfather_limit(username_response)

            token = _extract_bot_token(username_response)

            if token is None:

                await _cancel_botfather(dialog)

                if _is_botfather_username_error(username_response):

                    raise UsernameUnavailableError(username_response)

                raise RuntimeError(

                    "BotFather не вернул токен: "

                    f"{_compact_botfather_response(username_response)}"

                )

            return token

    except asyncio.TimeoutError as exc:

        raise RuntimeError("BotFather не ответил вовремя") from exc





async def _cancel_botfather(dialog: BotFatherConversation) -> None:

    await dialog.send_message("/cancel")

    with suppress(asyncio.TimeoutError):

        await dialog.get_response(timeout=min(BOTFATHER_TIMEOUT_SECONDS, 5))





async def _send_and_wait_botfather(

    dialog: BotFatherConversation,

    message: str,

) -> str:

    await dialog.send_message(message)

    return _message_text(await dialog.get_response())





async def _sleep_botfather_step() -> None:

    await asyncio.sleep(random.uniform(0.8, 2.2))





async def _ensure_account_available(client: TelegramClient) -> None:

    try:

        await asyncio.wait_for(client.connect(), timeout=_ACCOUNT_CONNECT_TIMEOUT)

        authorized = await asyncio.wait_for(

            client.is_user_authorized(), timeout=10

        )

        if not authorized:

            raise AccountUnavailableError

    except asyncio.TimeoutError as exc:

        raise AccountUnavailableError from exc

    except AccountUnavailableError:

        raise

    except Exception as exc:

        if _is_account_unavailable_error(exc):

            raise AccountUnavailableError from exc

        raise





async def _run_account_step(step: Awaitable[_T]) -> _T:

    try:

        return await step

    except Exception as exc:

        if _is_account_unavailable_error(exc):

            raise AccountUnavailableError from exc

        raise





async def _check_username_available(client: TelegramClient, username: str) -> bool:

                                                                                           

                                                                                      

                                                                                                               

    if not _is_valid_final_username(username):

        return False

    return True





def normalize_bot_name(name: str) -> str:

    normalized = " ".join(name.strip().split())

    if not 1 <= len(normalized) <= 64:

        raise RuntimeError("имя бота должно быть от 1 до 64 символов")

    return normalized





_BOT_NAME_EMOJIS: tuple[str, ...] = ("❗️", "🥵", "🤭", "😘", "🥰", "😍")





def build_bot_display_name(

    name: str,

    extra_usernames: Sequence[str],

    index: int = 1,

) -> str:

    _ = index

    base_name = normalize_bot_name(name)

    emoji = random.choice(_BOT_NAME_EMOJIS)

    wrapped_base = f"{emoji}{base_name}{emoji}"

    suffix = " ".join(_select_bot_name_extra_words(wrapped_base, extra_usernames))

    display_name = f"{wrapped_base} {suffix}" if suffix else wrapped_base

    if len(display_name) > 64:

        raise RuntimeError("итоговое имя бота длиннее 64 символов: убери смайл/сократи имя")

    return display_name





def normalize_base_username(username: str) -> str:

    normalized = username.strip().removeprefix("@")

    if not _base_username_pattern.fullmatch(normalized):

        raise RuntimeError(

            "основной username: латиница/цифры/_, 2-28 символов, начинается с буквы"

        )

    return normalized





def normalize_base_usernames(usernames: str | Sequence[str]) -> list[str]:

    raw_values = usernames.split() if isinstance(usernames, str) else list(usernames)

    result: list[str] = []

    seen: set[str] = set()

    invalid: list[str] = []

    for raw_value in raw_values:

        value = raw_value.strip().strip(",;").removeprefix("@")

        if not value:

            continue

        try:

            normalized = normalize_base_username(value)

        except RuntimeError:

            invalid.append(value)

            continue

        key = normalized.casefold()

        if key not in seen:

            seen.add(key)

            result.append(normalized)

    if result:

        return result

    raise RuntimeError(

        "основной username: одно слово или список через пробел, "

        "латиница/цифры/_, 2-28 символов, начинается с буквы"

    )





def normalize_bot_username(username: str) -> str:

    normalized = username.strip().removeprefix("@")

    if not _is_valid_final_username(normalized):

        raise RuntimeError(

            "username должен быть 5-32 символа, латиница/цифры/_, и заканчиваться на bot"

        )

    return normalized





def normalize_bot_count(amount: int) -> int:

    if amount < 1:

        raise RuntimeError("количество токенов должно быть больше 0")

    if amount > BOT_CREATE_MAX_COUNT:

        raise RuntimeError(f"за раз можно создать максимум {BOT_CREATE_MAX_COUNT}")

    return amount





def normalize_account_use_count(amount: int, available_accounts: int) -> int:

    if amount < 1:

        raise RuntimeError("количество аккаунтов должно быть больше 0")

    if amount > available_accounts:

        raise RuntimeError(f"доступно только {available_accounts} аккаунтов")

    return amount





def normalize_extra_usernames(extra_usernames: Sequence[str]) -> list[str]:

    result: list[str] = []

    seen: set[str] = set()

    for raw_value in extra_usernames:

        value = raw_value.strip().strip(",;").removeprefix("@")

        if not value:

            continue

        if value.casefold() in {"-", "нет", "no", "skip"}:

            continue

        if not _extra_username_pattern.fullmatch(value):

            raise RuntimeError(

                "дополнительные usernames: только латиница, цифры и _, до 32 символов"

            )

        key = value.casefold()

        if key not in seen:

            seen.add(key)

            result.append(value)

    return result





def _select_bot_name_extra_words(

    base_name: str,

    extra_usernames: Sequence[str],

) -> tuple[str, ...]:

    if not extra_usernames:

        return ()

    if len(extra_usernames) < _bot_name_extra_words_per_bot:

        raise RuntimeError(

            "дополнительных usernames должно быть минимум 4 или отправь -"

        )

    words = tuple(extra_usernames)

    for _ in range(200):

        selected = tuple(random.sample(words, _bot_name_extra_words_per_bot))

        if _is_valid_bot_display_name(base_name, selected):

            return selected



    shortest = tuple(

        sorted(words, key=len)[:_bot_name_extra_words_per_bot]

    )

    if _is_valid_bot_display_name(base_name, shortest):

        return shortest

    raise RuntimeError(

        "итоговое имя бота длиннее 64 символов: нужны слова короче"

    )





def _is_valid_bot_display_name(base_name: str, words: Sequence[str]) -> bool:

    suffix = " ".join(words)

    display_name = f"{base_name} {suffix}" if suffix else base_name

    return len(display_name) <= 64





def _iter_username_candidates(

    base_usernames: Sequence[str],

    extra_usernames: Sequence[str],

) -> Iterator[str]:

    _ = extra_usernames

    normalized_bases = tuple(normalize_base_usernames(base_usernames))

    yielded: set[str] = set()

    static_candidate_groups = tuple(

        tuple(_iter_static_username_candidates(base_username))

        for base_username in normalized_bases

    )



    for offset in range(max(len(group) for group in static_candidate_groups)):

        for candidates in static_candidate_groups:

            if offset >= len(candidates):

                continue

            candidate = candidates[offset]

            unique_candidate = _unique_username_candidate(candidate, yielded)

            if unique_candidate is not None:

                yield unique_candidate



    for number in range(2, 1000):

        for base_username in normalized_bases:

            stem = _username_stem(base_username)

            for candidate in (f"{stem}{number}bot", f"{stem}_{number}bot"):

                unique_candidate = _unique_username_candidate(candidate, yielded)

                if unique_candidate is not None:

                    yield unique_candidate



    letters = "abcdefghijklmnopqrstuvwxyz"

    while True:

        for letter in letters:

            for base_username in normalized_bases:

                stem = _username_stem(base_username)

                for candidate in (f"{stem}{letter}bot", f"{stem}_{letter}bot"):

                    unique_candidate = _unique_username_candidate(candidate, yielded)

                    if unique_candidate is not None:

                        yield unique_candidate





def _iter_static_username_candidates(base_username: str) -> Iterator[str]:

    stem = _username_stem(base_username)

    candidates = []

    if base_username.casefold().endswith("bot"):

        candidates.append(base_username)

    candidates.extend([

        f"{stem}bot",

        f"{stem}_bot",

        f"{stem}Rbot",

        f"{stem}Lbot",

        f"{stem}Robot",

        f"{stem}1bot",

        f"{stem}_rbot",

        f"{stem}_lbot",

        f"{stem}_robot",

        f"{stem}robot",

    ])

    yield from candidates





def _username_stem(base_username: str) -> str:

    return (

        base_username[:-3]

        if base_username.casefold().endswith("bot") and len(base_username) > 4

        else base_username

    )





def _unique_username_candidate(

    candidate: str,

    yielded: set[str],

) -> str | None:

    if not candidate or not _is_valid_final_username(candidate):

        return None

    key = candidate.casefold()

    if key in yielded:

        return None

    yielded.add(key)

    return candidate





def _account_title(account: TelegramAccount) -> str:

    if account.phone:

        return f"+{account.phone.lstrip('+')}"

    if account.username:

        return f"@{account.username}"

    return str(account.telegram_id)





def _message_text(message: object) -> str:

    raw_text = getattr(message, "raw_text", None)

    if isinstance(raw_text, str):

        return raw_text

    text = getattr(message, "message", None)

    return text if isinstance(text, str) else ""





def _extract_bot_token(text: str) -> str | None:

    match = _bot_token_pattern.search(text)

    return match.group(0) if match else None





def _bot_id_from_token(token: str) -> int:

    bot_id, _, _ = token.partition(":")

    return int(bot_id)





def _compact_botfather_response(text: str) -> str:

    compact = " ".join(text.split())

    return compact[:250] if len(compact) > 250 else compact





def _raise_if_botfather_limit(text: str) -> None:

    retry_after_seconds = _extract_botfather_retry_after_seconds(text)

    if retry_after_seconds is not None:

        raise BotFatherRetryAfterError(retry_after_seconds)

    lowered = text.casefold()

    if any(marker in lowered for marker in _botfather_limit_error_markers):

        raise RuntimeError("лимит создания ботов на аккаунте исчерпан")





def _extract_botfather_retry_after_seconds(text: str) -> int | None:

    match = _botfather_retry_after_pattern.search(text)

    return int(match.group(1)) if match else None





def _is_botfather_username_error(text: str) -> bool:

    lowered = text.casefold()

    return any(marker in lowered for marker in _botfather_username_error_markers)





def _format_rpc_error(exc: RPCError) -> str:

    name = exc.__class__.__name__

    if name == "BotCreateLimitExceededError":

        return "лимит создания ботов на аккаунте исчерпан"

    if name == "BotMethodInvalidError":

        return "метод Telegram недоступен для этого аккаунта"

    if name == "FloodWaitError":

        seconds = getattr(exc, "seconds", None)

        if isinstance(seconds, int) and seconds > 0:

            return f"Telegram попросил подождать {seconds} сек."

        return "Telegram попросил подождать перед созданием"

    if name == "PeerFloodError":

        return "Telegram временно ограничил действия аккаунта"

    if name == "UserIsBlockedError":

        return "на аккаунте заблокирован BotFather"

    if name == "UsernameOccupiedError":

        return "username уже занят"

    if name == "UsernameInvalidError":

        return "username некорректный"

    if name == "UsernameSuffixMissingError":

        return "username должен заканчиваться на bot"

    if name == "NameInvalidError":

        return "имя бота некорректное"

    return name





def _is_account_unavailable_error(exc: Exception) -> bool:

    return (

        exc.__class__.__name__ in _account_unavailable_errors

        or isinstance(exc, telethon_errors.UnauthorizedError)

    )





def _is_username_unavailable_error(exc: Exception) -> bool:

    return exc.__class__.__name__ in _username_unavailable_errors





def _is_valid_final_username(username: str) -> bool:

    return 5 <= len(username) <= 32 and bool(_final_username_pattern.fullmatch(username))





async def _emit_batch_progress(

    progress_callback: BotBatchProgressCallback | None,

    progress: BotBatchProgress,

) -> None:

    if progress_callback is not None:

        await progress_callback(progress)





async def _get_next_batch_index(

    work_queue: asyncio.Queue[int],

    state: _BatchRuntimeState,

) -> int | None:

    while True:

        try:

            return work_queue.get_nowait()

        except asyncio.QueueEmpty:

            async with state.lock:

                if state.in_progress == 0:

                    return None

            await asyncio.sleep(0.5)





async def _mark_batch_item_started(

    progress_callback: BotBatchProgressCallback | None,

    state: _BatchRuntimeState,

    account_title: str,

) -> None:

    async with state.lock:

        state.in_progress += 1

    await _emit_runtime_progress(progress_callback, state, account_title)





async def _append_batch_item(

    progress_callback: BotBatchProgressCallback | None,

    item_callback: BotBatchItemCallback | None,

    state: _BatchRuntimeState,

    item: BotBatchItem,

) -> None:

    if item_callback is not None:

        await item_callback(item)

    async with state.lock:

        state.in_progress = max(state.in_progress - 1, 0)

        if item.account_id is not None:

            state.waiting_accounts.pop(item.account_id, None)

        state.items.append(item)

    await _emit_runtime_progress(progress_callback, state)





async def _mark_batch_item_cancelled(

    progress_callback: BotBatchProgressCallback | None,

    state: _BatchRuntimeState,

    account_id: int,

) -> None:

    async with state.lock:

        state.in_progress = max(state.in_progress - 1, 0)

        state.waiting_accounts.pop(account_id, None)

    await _emit_runtime_progress(progress_callback, state)





async def _drop_batch_account(

    progress_callback: BotBatchProgressCallback | None,

    item_callback: BotBatchItemCallback | None,

    state: _BatchRuntimeState,

    work_queue: asyncio.Queue[int],

    account: TelegramAccount,

    index: int,

    error: str,

) -> None:

    failed_items: list[BotBatchItem] = []

    async with state.lock:

        state.in_progress = max(state.in_progress - 1, 0)

        state.waiting_accounts.pop(account.id, None)

        state.active_account_ids.discard(account.id)

        if state.active_account_ids:

            work_queue.put_nowait(index)

        else:

            failed_items.append(

                BotBatchItem(

                    index=index,

                    ok=False,

                    account_title=_account_title(account),

                    name=build_bot_display_name(

                        state.base_bot_name,

                        state.extra_usernames,

                        index,

                    ),

                    account_id=account.id,

                    error=error,

                )

            )

            while True:

                try:

                    pending_index = work_queue.get_nowait()

                except asyncio.QueueEmpty:

                    break

                failed_items.append(

                    BotBatchItem(

                        index=pending_index,

                        ok=False,

                        account_title="нет аккаунта",

                        name=build_bot_display_name(

                            state.base_bot_name,

                            state.extra_usernames,

                            pending_index,

                        ),

                        error=error,

                    )

                )

            state.items.extend(failed_items)

    if item_callback is not None:

        for item in failed_items:

            await item_callback(item)

    await _emit_runtime_progress(progress_callback, state)





async def _emit_runtime_progress(

    progress_callback: BotBatchProgressCallback | None,

    state: _BatchRuntimeState,

    current_account_title: str | None = None,

) -> None:

    await _emit_batch_progress(

        progress_callback,

        await _snapshot_batch_progress(state, current_account_title),

    )





async def _set_account_wait(

    progress_callback: BotBatchProgressCallback | None,

    state: _BatchRuntimeState,

    account_id: int,

    account_title: str,

    remaining_seconds: int,

    reason: str | None,

) -> None:

    async with state.lock:

        if remaining_seconds > 0:

            state.waiting_accounts[account_id] = (

                account_title,

                remaining_seconds,

                reason,

            )

        else:

            state.waiting_accounts.pop(account_id, None)

    await _emit_runtime_progress(progress_callback, state, account_title)





async def _snapshot_batch_progress(

    state: _BatchRuntimeState,

    current_account_title: str | None = None,

) -> BotBatchProgress:

    async with state.lock:

        wait_remaining_seconds: int | None = None

        wait_reason: str | None = None

        display_account_title = current_account_title

        if state.waiting_accounts:

            waiting_account_title, wait_remaining_seconds, wait_reason = min(

                state.waiting_accounts.values(),

                key=lambda item: item[1],

            )

            if display_account_title is None:

                display_account_title = waiting_account_title

        return _build_batch_progress(

            state.accounts_total,

            len(state.active_account_ids),

            state.requested,

            tuple(state.items),

            state.in_progress,

            current_account_title=display_account_title,

            wait_remaining_seconds=wait_remaining_seconds,

            wait_reason=wait_reason,

            waiting_accounts=len(state.waiting_accounts),

        )





async def _has_batch_work_remaining(

    state: _BatchRuntimeState,

    work_queue: asyncio.Queue[int],

) -> bool:

    if not work_queue.empty():

        return True

    async with state.lock:

        return state.in_progress > 0





def _build_batch_progress(

    accounts_total: int,

    accounts_active: int,

    requested: int,

    items: Sequence[BotBatchItem],

    in_progress: int,

    current_account_title: str | None = None,

    wait_remaining_seconds: int | None = None,

    wait_reason: str | None = None,

    waiting_accounts: int = 0,

) -> BotBatchProgress:

    return BotBatchProgress(

        accounts_total=accounts_total,

        accounts_active=accounts_active,

        requested=requested,

        processed=len(items),

        created=sum(1 for item in items if item.ok),

        failed=sum(1 for item in items if not item.ok),

        in_progress=in_progress,

        waiting_accounts=waiting_accounts,

        current_account_title=current_account_title,

        wait_remaining_seconds=wait_remaining_seconds,

        wait_reason=wait_reason,

    )





async def _sleep_before_next_account_bot(

    progress_callback: BotBatchProgressCallback | None,

    state: _BatchRuntimeState,

    work_queue: asyncio.Queue[int],

    account_id: int,

    account_title: str,

    delay_seconds: int,

) -> None:

    remaining = max(delay_seconds, 0)

    while remaining > 0:

        if not await _has_batch_work_remaining(state, work_queue):

            break

        await _set_account_wait(

            progress_callback,

            state,

            account_id,

            account_title,

            remaining,

            None,

        )

        sleep_seconds = min(5, remaining)

        await asyncio.sleep(sleep_seconds)

        remaining -= sleep_seconds

    await _set_account_wait(progress_callback, state, account_id, account_title, 0, None)





def _next_create_delay() -> int:

    min_delay = max(BOT_CREATE_DELAY_MIN_SECONDS, 0)

    max_delay = max(BOT_CREATE_DELAY_MAX_SECONDS, min_delay)

    return random.randint(min_delay, max_delay)





def _get_account_lock(account_id: int) -> asyncio.Lock:

    lock = _account_locks.get(account_id)

    if lock is None:

        lock = asyncio.Lock()

        _account_locks[account_id] = lock

    return lock

