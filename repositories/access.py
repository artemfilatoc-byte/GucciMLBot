import hashlib

import re

import secrets

from dataclasses import dataclass

from typing import Literal



from sqlalchemy import func, select, update



from core.db import Session, now_msk

from models import AccessKey, User



KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

ACCESS_KEY_PATTERN = re.compile(

    r"^[A-Z2-9]{4}(?:[-\s]?[A-Z2-9]{4}){3}$",

    re.IGNORECASE,

)



ActivationStatus = Literal["activated", "already_has_access", "invalid", "used"]





@dataclass(frozen=True)

class AccessKeyCreateResult:

    key: str

    key_id: int





@dataclass(frozen=True)

class AccessKeyActivationResult:

    status: ActivationStatus





@dataclass(frozen=True)

class AccessStats:

    users_total: int

    users_with_access: int

    keys_total: int

    keys_unused: int

    keys_used: int

    accounts_total: int = 0





def normalize_access_key(value: str) -> str:

    return re.sub(r"[\s-]+", "", value.strip().upper())





def is_access_key_like(value: str | None) -> bool:

    return bool(value and ACCESS_KEY_PATTERN.fullmatch(value.strip()))





def _format_access_key(value: str) -> str:

    return "-".join(value[index : index + 4] for index in range(0, len(value), 4))





def _hash_access_key(value: str) -> str:

    return hashlib.sha256(normalize_access_key(value).encode()).hexdigest()





def _generate_access_key() -> str:

    raw = "".join(secrets.choice(KEY_ALPHABET) for _ in range(16))

    return _format_access_key(raw)





async def create_access_key(admin_telegram_id: int) -> AccessKeyCreateResult:

    async with Session() as session:

        for _ in range(10):

            key = _generate_access_key()

            key_hash = _hash_access_key(key)

            exists = await session.scalar(

                select(AccessKey.id).where(AccessKey.key_hash == key_hash)

            )

            if exists is not None:

                continue

            access_key = AccessKey(

                key_hash=key_hash,

                key_preview=key[-4:],

                created_by_telegram_id=admin_telegram_id,

            )

            session.add(access_key)

            await session.commit()

            await session.refresh(access_key)

            return AccessKeyCreateResult(key=key, key_id=access_key.id)

    raise RuntimeError("Не удалось создать уникальный ключ")





async def activate_access_key(

    telegram_id: int,

    username: str | None,

    full_name: str | None,

    raw_key: str,

) -> AccessKeyActivationResult:

    key_hash = _hash_access_key(raw_key)

    async with Session() as session:

        access_key = await session.scalar(

            select(AccessKey).where(

                AccessKey.key_hash == key_hash,

                AccessKey.is_active.is_(True),

            )

        )

        if access_key is None:

            return AccessKeyActivationResult(status="invalid")

        if (

            access_key.activated_at is not None

            or access_key.activated_by_user_id is not None

        ):

            return AccessKeyActivationResult(status="used")



        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

        if user is not None and user.access_granted_at is not None:

            return AccessKeyActivationResult(status="already_has_access")



        if user is None:

            user = User(

                telegram_id=telegram_id,

                username=username,

                full_name=full_name,

            )

            session.add(user)

            await session.flush()

        else:

            user.username = username

            user.full_name = full_name



        activated_at = now_msk()

        result = await session.execute(

            update(AccessKey)

            .where(

                AccessKey.id == access_key.id,

                AccessKey.is_active.is_(True),

                AccessKey.activated_at.is_(None),

                AccessKey.activated_by_user_id.is_(None),

            )

            .values(

                activated_by_user_id=user.id,

                activated_by_telegram_id=telegram_id,

                activated_at=activated_at,

            )

        )

        if not result.rowcount:

            await session.commit()

            return AccessKeyActivationResult(status="used")



        user.access_granted_at = activated_at

        await session.commit()

        return AccessKeyActivationResult(status="activated")





async def list_access_keys(

    page: int, per_page: int

) -> tuple[list[AccessKey], bool]:

    offset = max(page, 0) * per_page

    async with Session() as session:

        rows = list(

            await session.scalars(

                select(AccessKey)

                .order_by(AccessKey.created_at.desc(), AccessKey.id.desc())

                .offset(offset)

                .limit(per_page + 1)

            )

        )

    return rows[:per_page], len(rows) > per_page





async def get_access_key(key_id: int) -> AccessKey | None:

    async with Session() as session:

        return await session.scalar(select(AccessKey).where(AccessKey.id == key_id))





async def deactivate_access_key(key_id: int) -> bool:

    async with Session() as session:

        key = await session.scalar(select(AccessKey).where(AccessKey.id == key_id))

        if key is None or not key.is_active:

            return False

        key.is_active = False

                                                  

        if key.activated_by_user_id is not None:

            user = await session.scalar(

                select(User).where(User.id == key.activated_by_user_id)

            )

            if user is not None:

                user.access_granted_at = None

        elif key.activated_by_telegram_id is not None:

            user = await session.scalar(

                select(User).where(User.telegram_id == key.activated_by_telegram_id)

            )

            if user is not None:

                user.access_granted_at = None

        await session.commit()

        return True





async def delete_access_key(key_id: int) -> bool:

                                                                

    async with Session() as session:

        key = await session.scalar(select(AccessKey).where(AccessKey.id == key_id))

        if key is None:

            return False

        if key.activated_at is not None or key.activated_by_user_id is not None:

                                                   

            if not key.is_active:

                return False

            key.is_active = False

            if key.activated_by_user_id is not None:

                user = await session.scalar(

                    select(User).where(User.id == key.activated_by_user_id)

                )

                if user is not None:

                    user.access_granted_at = None

            await session.commit()

            return True

        await session.delete(key)

        await session.commit()

        return True





async def get_access_stats() -> AccessStats:

    async with Session() as session:

        users_total = int(await session.scalar(select(func.count()).select_from(User)) or 0)

        users_with_access = int(

            await session.scalar(

                select(func.count())

                .select_from(User)

                .where(User.access_granted_at.is_not(None))

            )

            or 0

        )

        keys_total = int(

            await session.scalar(select(func.count()).select_from(AccessKey)) or 0

        )

        keys_unused = int(

            await session.scalar(

                select(func.count())

                .select_from(AccessKey)

                .where(

                    AccessKey.is_active.is_(True),

                    AccessKey.activated_at.is_(None),

                )

            )

            or 0

        )

        from models import TelegramAccount



        accounts_total = int(

            await session.scalar(select(func.count()).select_from(TelegramAccount)) or 0

        )

    return AccessStats(

        users_total=users_total,

        users_with_access=users_with_access,

        keys_total=keys_total,

        keys_unused=keys_unused,

        keys_used=max(keys_total - keys_unused, 0),

        accounts_total=accounts_total,

    )

