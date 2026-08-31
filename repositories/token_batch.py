from collections.abc import Sequence

from dataclasses import dataclass

import json

from typing import Literal



import asyncio



from sqlalchemy import func, select, update



from core.db import Session, insert, now_msk

from models import TokenCreateBatch, TokenCreateBatchItem



TokenBatchStatus = Literal["running", "stopping", "stopped", "completed", "failed"]



_batch_write_lock = asyncio.Lock()





@dataclass(frozen=True)

class TokenBatchItemPayload:

    position: int

    ok: bool

    account_title: str

    name: str

    created_bot_id: int | None

    account_id: int | None

    username: str | None

    token: str | None

    error: str | None





@dataclass(frozen=True)

class TokenBatchCreatePayload:

    owner_user_id: int

    requested_count: int

    name: str

    base_username: str

    base_usernames: Sequence[str]

    extra_usernames: Sequence[str]

    account_limit: int | None

    set_avatars: bool

    chat_id: int

    progress_message_id: int





async def create_running_token_batch(payload: TokenBatchCreatePayload) -> TokenCreateBatch:

    now = now_msk()

    async with Session() as session:

        batch = TokenCreateBatch(

            owner_user_id=payload.owner_user_id,

            requested_count=payload.requested_count,

            created_count=0,

            failed_count=0,

            status="running",

            name=payload.name,

            base_username=payload.base_username,

            base_usernames=json.dumps(list(payload.base_usernames), ensure_ascii=False),

            extra_usernames=json.dumps(list(payload.extra_usernames), ensure_ascii=False),

            account_limit=payload.account_limit,

            set_avatars=payload.set_avatars,

            chat_id=payload.chat_id,

            progress_message_id=payload.progress_message_id,

            updated_at=now,

        )

        session.add(batch)

        await session.commit()

        return batch





async def upsert_token_batch_item(batch_id: int, item: TokenBatchItemPayload) -> None:

    stmt = insert(TokenCreateBatchItem).values(

        batch_id=batch_id,

        created_bot_id=item.created_bot_id,

        account_id=item.account_id,

        position=item.position,

        ok=item.ok,

        account_title=item.account_title,

        name=item.name,

        username=item.username,

        token=item.token,

        error=item.error,

    )

    stmt = stmt.on_conflict_do_update(

        index_elements=[

            TokenCreateBatchItem.batch_id,

            TokenCreateBatchItem.position,

        ],

        set_={

            "created_bot_id": item.created_bot_id,

            "account_id": item.account_id,

            "ok": item.ok,

            "account_title": item.account_title,

            "name": item.name,

            "username": item.username,

            "token": item.token,

            "error": item.error,

        },

    )

    async with _batch_write_lock:

        async with Session() as session:

            await session.execute(stmt)

            await _refresh_batch_counts(session, batch_id)

            await session.commit()





async def request_stop_token_batch(owner_user_id: int, batch_id: int) -> bool:

    async with Session() as session:

        result = await session.execute(

            update(TokenCreateBatch)

            .where(

                TokenCreateBatch.owner_user_id == owner_user_id,

                TokenCreateBatch.id == batch_id,

                TokenCreateBatch.status == "running",

            )

            .values(status="stopping", updated_at=now_msk())

        )

        await session.commit()

        return bool(result.rowcount)





async def is_token_batch_stop_requested(batch_id: int) -> bool:

    async with Session() as session:

        status = await session.scalar(

            select(TokenCreateBatch.status).where(TokenCreateBatch.id == batch_id)

        )

        return status in {"stopping", "stopped"}





async def finish_token_batch(batch_id: int, status: TokenBatchStatus) -> TokenCreateBatch:

    async with Session() as session:

        await _refresh_batch_counts(session, batch_id)

        batch = await session.scalar(

            select(TokenCreateBatch).where(TokenCreateBatch.id == batch_id)

        )

        if batch is None:

            raise RuntimeError("Token batch was not found")

        batch.status = status

        batch.updated_at = now_msk()

        batch.finished_at = batch.updated_at

        await session.commit()

        return batch





async def list_resumable_token_batches() -> list[TokenCreateBatch]:

    async with Session() as session:

        return list(

            await session.scalars(

                select(TokenCreateBatch)

                .where(TokenCreateBatch.status.in_(("running", "stopping")))

                .order_by(TokenCreateBatch.created_at.asc(), TokenCreateBatch.id.asc())

            )

        )





def decode_batch_extra_usernames(batch: TokenCreateBatch) -> list[str]:

    if not batch.extra_usernames:

        return []

    try:

        values = json.loads(batch.extra_usernames)

    except json.JSONDecodeError:

        return []

    return [value for value in values if isinstance(value, str)]





def decode_batch_base_usernames(batch: TokenCreateBatch) -> list[str]:

    if batch.base_usernames:

        try:

            values = json.loads(batch.base_usernames)

        except json.JSONDecodeError:

            values = []

        result = [value for value in values if isinstance(value, str)]

        if result:

            return result

    return [batch.base_username] if batch.base_username else []





async def get_token_batch(

    owner_user_id: int,

    batch_id: int,

) -> TokenCreateBatch | None:

    async with Session() as session:

        return await session.scalar(

            select(TokenCreateBatch).where(

                TokenCreateBatch.owner_user_id == owner_user_id,

                TokenCreateBatch.id == batch_id,

            )

        )





async def list_token_batch_created_items(

    owner_user_id: int,

    batch_id: int,

    page: int,

    per_page: int,

) -> tuple[list[TokenCreateBatchItem], bool]:

    offset = max(page, 0) * per_page

    async with Session() as session:

        items = list(

            await session.scalars(

                select(TokenCreateBatchItem)

                .join(

                    TokenCreateBatch,

                    TokenCreateBatch.id == TokenCreateBatchItem.batch_id,

                )

                .where(

                    TokenCreateBatch.owner_user_id == owner_user_id,

                    TokenCreateBatchItem.batch_id == batch_id,

                    TokenCreateBatchItem.ok.is_(True),

                    TokenCreateBatchItem.token.is_not(None),

                )

                .order_by(TokenCreateBatchItem.position.asc())

                .offset(offset)

                .limit(per_page + 1)

            )

        )

    return items[:per_page], len(items) > per_page





async def list_token_batch_failed_items(

    owner_user_id: int,

    batch_id: int,

    limit: int,

) -> list[TokenCreateBatchItem]:

    async with Session() as session:

        return list(

            await session.scalars(

                select(TokenCreateBatchItem)

                .join(

                    TokenCreateBatch,

                    TokenCreateBatch.id == TokenCreateBatchItem.batch_id,

                )

                .where(

                    TokenCreateBatch.owner_user_id == owner_user_id,

                    TokenCreateBatchItem.batch_id == batch_id,

                    TokenCreateBatchItem.ok.is_(False),

                )

                .order_by(TokenCreateBatchItem.position.asc())

                .limit(limit)

            )

        )





async def list_token_batch_items(

    owner_user_id: int,

    batch_id: int,

) -> list[TokenCreateBatchItem]:

    async with Session() as session:

        return list(

            await session.scalars(

                select(TokenCreateBatchItem)

                .join(

                    TokenCreateBatch,

                    TokenCreateBatch.id == TokenCreateBatchItem.batch_id,

                )

                .where(

                    TokenCreateBatch.owner_user_id == owner_user_id,

                    TokenCreateBatchItem.batch_id == batch_id,

                )

                .order_by(TokenCreateBatchItem.position.asc())

            )

        )





async def list_token_batch_tokens(

    owner_user_id: int,

    batch_id: int,

) -> list[str]:

    async with Session() as session:

        rows = await session.scalars(

            select(TokenCreateBatchItem.token)

            .join(

                TokenCreateBatch,

                TokenCreateBatch.id == TokenCreateBatchItem.batch_id,

            )

            .where(

                TokenCreateBatch.owner_user_id == owner_user_id,

                TokenCreateBatchItem.batch_id == batch_id,

                TokenCreateBatchItem.ok.is_(True),

                TokenCreateBatchItem.token.is_not(None),

            )

            .order_by(TokenCreateBatchItem.position.asc())

        )

        return [token for token in rows if token is not None]





async def _refresh_batch_counts(session, batch_id: int) -> None:

    created_count = int(

        await session.scalar(

            select(func.count())

            .select_from(TokenCreateBatchItem)

            .where(

                TokenCreateBatchItem.batch_id == batch_id,

                TokenCreateBatchItem.ok.is_(True),

                TokenCreateBatchItem.token.is_not(None),

            )

        )

        or 0

    )

    failed_count = int(

        await session.scalar(

            select(func.count())

            .select_from(TokenCreateBatchItem)

            .where(

                TokenCreateBatchItem.batch_id == batch_id,

                TokenCreateBatchItem.ok.is_(False),

            )

        )

        or 0

    )

    await session.execute(

        update(TokenCreateBatch)

        .where(TokenCreateBatch.id == batch_id)

        .values(

            created_count=created_count,

            failed_count=failed_count,

            updated_at=now_msk(),

        )

    )

