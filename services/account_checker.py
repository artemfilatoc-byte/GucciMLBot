import asyncio

from dataclasses import dataclass



from telethon.sessions import StringSession



from core.config import TELETHON_IMPORT_CONCURRENCY

from repositories.account import delete_account, list_all_accounts

from services.telegram_client import build_telegram_client



_checker_sem = asyncio.Semaphore(TELETHON_IMPORT_CONCURRENCY)





@dataclass(frozen=True)

class AccountCheckResult:

    total: int

    valid: int

    deleted: int

    failed: int

    details: list[tuple[int, str, bool, str | None]]                                





def _account_title(phone: str | None, username: str | None, telegram_id: int) -> str:

    if phone:

        return f"+{phone.lstrip('+')}"

    if username:

        return f"@{username}"

    return str(telegram_id)





async def check_accounts_and_cleanup(owner_user_id: int) -> AccountCheckResult:

    accounts = await list_all_accounts(owner_user_id)

    total = len(accounts)

    if total == 0:

        return AccountCheckResult(0, 0, 0, 0, [])



    async def _check_one(account) -> tuple[int, str, bool, str | None]:

        async with _checker_sem:

            title = _account_title(account.phone, account.username, account.telegram_id)

            client = build_telegram_client(

                StringSession(account.session_string),

                getattr(account, "proxy_url", None),

            )

            try:

                try:

                    await asyncio.wait_for(client.connect(), timeout=20)

                except asyncio.TimeoutError:

                    return (account.id, title, False, "таймаут подключения")

                try:

                    authorized = await asyncio.wait_for(client.is_user_authorized(), timeout=10)

                except asyncio.TimeoutError:

                    return (account.id, title, False, "таймаут проверки")

                if not authorized:

                    await delete_account(owner_user_id, account.id)

                    return (account.id, title, False, "сессия не авторизована — удалён")

                try:

                    me = await asyncio.wait_for(client.get_me(), timeout=10)

                except asyncio.TimeoutError:

                    return (account.id, title, False, "не отвечает")

                if me is None:

                    return (account.id, title, False, "не удалось получить профиль")

                return (account.id, title, True, None)

            except Exception as exc:

                name = exc.__class__.__name__

                msg = str(exc).lower()

                invalid_markers = (

                    "authkey",

                    "unauthorized",

                    "sessionrevoked",

                    "sessionexpired",

                    "userdeactivated",

                    "deactivated",

                    "unregistered",

                )

                if any(m in msg or m in name.lower() for m in invalid_markers):

                    try:

                        await delete_account(owner_user_id, account.id)

                    except Exception:

                        pass

                    return (account.id, title, False, f"{name} — удалён")

                return (account.id, title, False, name)

            finally:

                try:

                    await client.disconnect()

                except Exception:

                    pass



    results = await asyncio.gather(*[_check_one(a) for a in accounts])

    valid = sum(1 for _, _, ok, _ in results if ok)

    deleted = sum(1 for _, _, ok, err in results if not ok and err and "удалён" in err)

    failed = total - valid - deleted

                                                                         

                                                        

                                             

    failed = sum(1 for _, _, ok, err in results if not ok and (not err or "удалён" not in err))

    return AccountCheckResult(total, valid, deleted, failed, list(results))

