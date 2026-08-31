from sqlalchemy import select



from core.db import Session, insert, now_msk

from models import User





async def upsert_user(

    telegram_id: int, username: str | None, full_name: str | None

) -> User:

    stmt = insert(User).values(

        telegram_id=telegram_id,

        username=username,

        full_name=full_name,

    )

    stmt = stmt.on_conflict_do_update(

        index_elements=[User.telegram_id],

        set_={"username": username, "full_name": full_name},

    )

    async with Session() as session:

        await session.execute(stmt)

        await session.commit()

        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

        if user is None:

            raise RuntimeError("User was not saved")

        return user





async def has_user_access(telegram_id: int) -> bool:

    async with Session() as session:

        access_granted_at = await session.scalar(

            select(User.access_granted_at).where(User.telegram_id == telegram_id)

        )

        return access_granted_at is not None





async def grant_user_access(telegram_id: int) -> bool:

    async with Session() as session:

        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

        if user is None:

            return False

        if user.access_granted_at is None:

            user.access_granted_at = now_msk()

        await session.commit()

        return True





async def list_users_with_access(

    page: int, per_page: int

) -> tuple[list[User], bool]:

    offset = max(page, 0) * per_page

    async with Session() as session:

        rows = list(

            await session.scalars(

                select(User)

                .where(User.access_granted_at.is_not(None))

                .order_by(User.access_granted_at.desc(), User.id.desc())

                .offset(offset)

                .limit(per_page + 1)

            )

        )

    return rows[:per_page], len(rows) > per_page





async def list_all_access_user_ids() -> list[int]:

    async with Session() as session:

        rows = await session.scalars(

            select(User.telegram_id).where(User.access_granted_at.is_not(None))

        )

        return list(rows)





async def get_user_by_telegram_id(telegram_id: int) -> User | None:

    async with Session() as session:

        return await session.scalar(select(User).where(User.telegram_id == telegram_id))





async def revoke_user_access(telegram_id: int) -> bool:

    from models import AccessKey



    async with Session() as session:

        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

        if user is None or user.access_granted_at is None:

            return False

        user.access_granted_at = None

                                                

        keys = await session.scalars(

            select(AccessKey).where(

                AccessKey.activated_by_telegram_id == telegram_id,

                AccessKey.is_active.is_(True),

            )

        )

        for key in keys:

            key.is_active = False

                         

        keys2 = await session.scalars(

            select(AccessKey).where(

                AccessKey.activated_by_user_id == user.id,

                AccessKey.is_active.is_(True),

            )

        )

        for key in keys2:

            key.is_active = False

        await session.commit()

        return True

