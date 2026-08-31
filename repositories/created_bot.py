from collections.abc import Sequence

from dataclasses import dataclass



from sqlalchemy import delete, select



from core.db import Session, insert, now_msk

from models import CreatedBot





@dataclass(frozen=True)

class CreatedBotPayload:

    account_id: int

    bot_telegram_id: int

    name: str

    username: str

    token: str

    manager_bot_id: int | None





async def upsert_created_bot(

    owner_user_id: int,

    payload: CreatedBotPayload,

) -> CreatedBot:

    checked_at = now_msk()

    values = {

        "owner_user_id": owner_user_id,

        "account_id": payload.account_id,

        "bot_telegram_id": payload.bot_telegram_id,

        "name": payload.name,

        "username": payload.username,

        "token": payload.token,

        "manager_bot_id": payload.manager_bot_id,

        "updated_at": checked_at,

    }

    stmt = insert(CreatedBot).values(**values)

    stmt = stmt.on_conflict_do_update(

        index_elements=[

            CreatedBot.owner_user_id,

            CreatedBot.bot_telegram_id,

        ],

        set_={

            "account_id": payload.account_id,

            "name": payload.name,

            "username": payload.username,

            "token": payload.token,

            "manager_bot_id": payload.manager_bot_id,

            "updated_at": checked_at,

        },

    )

    async with Session() as session:

        await session.execute(stmt)

        await session.commit()

        bot = await session.scalar(

            select(CreatedBot).where(

                CreatedBot.owner_user_id == owner_user_id,

                CreatedBot.bot_telegram_id == payload.bot_telegram_id,

            )

        )

        if bot is None:

            raise RuntimeError("Bot token was not saved")

        return bot





async def list_created_bots(

    owner_user_id: int,

    page: int,

    per_page: int,

) -> tuple[list[CreatedBot], bool]:

    offset = max(page, 0) * per_page

    async with Session() as session:

        bots = list(

            await session.scalars(

                select(CreatedBot)

                .where(CreatedBot.owner_user_id == owner_user_id)

                .order_by(CreatedBot.created_at.desc(), CreatedBot.id.desc())

                .offset(offset)

                .limit(per_page + 1)

            )

        )

    return bots[:per_page], len(bots) > per_page





async def list_created_bot_tokens(owner_user_id: int) -> list[str]:

    async with Session() as session:

        tokens = await session.scalars(

            select(CreatedBot.token)

            .where(CreatedBot.owner_user_id == owner_user_id)

            .order_by(CreatedBot.created_at.desc(), CreatedBot.id.desc())

        )

        return list(tokens)





async def list_account_ids_with_created_bots(

    owner_user_id: int,

    account_ids: Sequence[int],

) -> set[int]:

    if not account_ids:

        return set()

    async with Session() as session:

        used_account_ids = await session.scalars(

            select(CreatedBot.account_id)

            .where(

                CreatedBot.owner_user_id == owner_user_id,

                CreatedBot.account_id.in_(account_ids),

            )

            .distinct()

        )

        return {account_id for account_id in used_account_ids if account_id is not None}





async def get_created_bot(

    owner_user_id: int,

    created_bot_id: int,

) -> CreatedBot | None:

    async with Session() as session:

        return await session.scalar(

            select(CreatedBot).where(

                CreatedBot.owner_user_id == owner_user_id,

                CreatedBot.id == created_bot_id,

            )

        )





async def delete_created_bot(owner_user_id: int, created_bot_id: int) -> bool:

    async with Session() as session:

        result = await session.execute(

            delete(CreatedBot).where(

                CreatedBot.owner_user_id == owner_user_id,

                CreatedBot.id == created_bot_id,

            )

        )

        await session.commit()

        return bool(result.rowcount)





async def delete_all_created_bots(owner_user_id: int) -> int:

    async with Session() as session:

        result = await session.execute(

            delete(CreatedBot).where(CreatedBot.owner_user_id == owner_user_id)

        )

        await session.commit()

        return int(result.rowcount or 0)





async def update_created_bot_name(

    owner_user_id: int,

    created_bot_id: int,

    name: str,

) -> bool:

    async with Session() as session:

        bot = await session.scalar(

            select(CreatedBot).where(

                CreatedBot.owner_user_id == owner_user_id,

                CreatedBot.id == created_bot_id,

            )

        )

        if bot is None:

            return False

        bot.name = name

        bot.updated_at = now_msk()

        await session.commit()

        return True





async def count_created_bots_total() -> int:

    from sqlalchemy import func



    async with Session() as session:

        return int(await session.scalar(select(func.count()).select_from(CreatedBot)) or 0)





async def count_created_bots_by_owner(owner_user_id: int) -> int:

    from sqlalchemy import func



    async with Session() as session:

        return int(

            await session.scalar(

                select(func.count()).select_from(CreatedBot).where(CreatedBot.owner_user_id == owner_user_id)

            )

            or 0

        )





async def count_created_bots_by_owner_since(owner_user_id: int, since) -> int:

    from sqlalchemy import func



    async with Session() as session:

        return int(

            await session.scalar(

                select(func.count())

                .select_from(CreatedBot)

                .where(CreatedBot.owner_user_id == owner_user_id, CreatedBot.created_at >= since)

            )

            or 0

        )





async def count_created_bots_since(since) -> int:

    from sqlalchemy import func



    async with Session() as session:

        return int(

            await session.scalar(select(func.count()).select_from(CreatedBot).where(CreatedBot.created_at >= since))

            or 0

        )





async def get_top_owners(limit: int = 10) -> list[tuple[int, str | None, str | None, int]]:

    from sqlalchemy import func



    from models import User



    async with Session() as session:

        rows = await session.execute(

            select(User.telegram_id, User.username, User.full_name, func.count(CreatedBot.id).label("cnt"))

            .join(CreatedBot, CreatedBot.owner_user_id == User.id)

            .group_by(User.id)

            .order_by(func.count(CreatedBot.id).desc())

            .limit(limit)

        )

        return [(r[0], r[1], r[2], r[3]) for r in rows.all()]

