from dataclasses import dataclass

from typing import Literal



from sqlalchemy import delete, func, select



from core.db import Session, insert, now_msk

from models import TelegramAccount



AccountSaveResult = Literal["created", "duplicate"]





@dataclass(frozen=True)

class TelegramAccountPayload:

    telegram_id: int

    phone: str | None

    username: str | None

    first_name: str | None

    last_name: str | None

    session_string: str

    dc_id: int | None

    proxy_url: str | None = None





async def upsert_account(

    owner_user_id: int,

    payload: TelegramAccountPayload,

) -> AccountSaveResult:

    async with Session() as session:

        existing_id = await session.scalar(

            select(TelegramAccount.id).where(

                TelegramAccount.telegram_id == payload.telegram_id,

            )

        )

        if existing_id is not None:

            return "duplicate"



        checked_at = now_msk()

        values = {

            "owner_user_id": owner_user_id,

            "telegram_id": payload.telegram_id,

            "phone": payload.phone,

            "username": payload.username,

            "first_name": payload.first_name,

            "last_name": payload.last_name,

            "session_string": payload.session_string,

            "dc_id": payload.dc_id,

            "proxy_url": payload.proxy_url,

            "last_checked_at": checked_at,

            "updated_at": checked_at,

        }

        stmt = insert(TelegramAccount).values(**values)

        stmt = stmt.on_conflict_do_nothing(

            index_elements=[

                TelegramAccount.owner_user_id,

                TelegramAccount.telegram_id,

            ],

        )

        result = await session.execute(stmt)

        await session.commit()

        return "created" if result.rowcount else "duplicate"





async def list_accounts(

    owner_user_id: int,

    page: int,

    per_page: int,

) -> tuple[list[TelegramAccount], bool]:

    offset = max(page, 0) * per_page

    async with Session() as session:

        accounts = list(

            await session.scalars(

                select(TelegramAccount)

                .where(TelegramAccount.owner_user_id == owner_user_id)

                .order_by(TelegramAccount.created_at.desc(), TelegramAccount.id.desc())

                .offset(offset)

                .limit(per_page + 1)

            )

        )

    return accounts[:per_page], len(accounts) > per_page





async def list_all_accounts(owner_user_id: int) -> list[TelegramAccount]:

    async with Session() as session:

        return list(

            await session.scalars(

                select(TelegramAccount)

                .where(TelegramAccount.owner_user_id == owner_user_id)

                .order_by(TelegramAccount.created_at.asc(), TelegramAccount.id.asc())

            )

        )





async def count_accounts(owner_user_id: int) -> int:

    async with Session() as session:

        return int(

            await session.scalar(

                select(func.count())

                .select_from(TelegramAccount)

                .where(TelegramAccount.owner_user_id == owner_user_id)

            )

            or 0

        )





async def count_all_accounts() -> int:

    async with Session() as session:

        return int(await session.scalar(select(func.count()).select_from(TelegramAccount)) or 0)





async def list_all_accounts_global() -> list[TelegramAccount]:

    async with Session() as session:

        return list(await session.scalars(select(TelegramAccount).order_by(TelegramAccount.created_at.desc())))





async def get_account(

    owner_user_id: int,

    account_id: int,

) -> TelegramAccount | None:

    async with Session() as session:

        return await session.scalar(

            select(TelegramAccount).where(

                TelegramAccount.owner_user_id == owner_user_id,

                TelegramAccount.id == account_id,

            )

        )





async def delete_account(owner_user_id: int, account_id: int) -> bool:

    async with Session() as session:

        result = await session.execute(

            delete(TelegramAccount).where(

                TelegramAccount.owner_user_id == owner_user_id,

                TelegramAccount.id == account_id,

            )

        )

        await session.commit()

        return bool(result.rowcount)





async def delete_all_accounts(owner_user_id: int) -> int:

    async with Session() as session:

        result = await session.execute(

            delete(TelegramAccount).where(

                TelegramAccount.owner_user_id == owner_user_id,

            )

        )

        await session.commit()

        return int(result.rowcount or 0)





async def set_account_proxy(

    owner_user_id: int, account_id: int, proxy_url: str | None

) -> bool:

    from sqlalchemy import update



    async with Session() as session:

        result = await session.execute(

            update(TelegramAccount)

            .where(

                TelegramAccount.owner_user_id == owner_user_id,

                TelegramAccount.id == account_id,

            )

            .values(proxy_url=proxy_url, updated_at=now_msk())

        )

        await session.commit()

        return bool(result.rowcount)





async def bulk_assign_proxies(

    owner_user_id: int, proxy_urls: list[str]

) -> int:

    if not proxy_urls:

        return 0

    import random



    accounts = await list_all_accounts(owner_user_id)

    if not accounts:

        return 0

                                            

    random.shuffle(proxy_urls)

    assigned = 0

    for idx, acc in enumerate(accounts):

        proxy = proxy_urls[idx % len(proxy_urls)]

        await set_account_proxy(owner_user_id, acc.id, proxy)

        assigned += 1

    return assigned

