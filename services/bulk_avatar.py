import asyncio

from collections.abc import Awaitable, Callable



from repositories.created_bot import list_created_bots, list_created_bot_tokens

from repositories.token_batch import list_token_batch_tokens

from services.bot_editor import set_created_bot_avatar



BulkAvatarProgressCallback = Callable[[int, int, int, int], Awaitable[None]]





async def bulk_set_avatar_for_tokens(

    tokens: list[str],

    photo_bytes: bytes,

    progress_callback: BulkAvatarProgressCallback | None = None,

    concurrency: int = 3,

) -> tuple[int, int]:

    sem = asyncio.Semaphore(concurrency)

    ok = 0

    fail = 0

    total = len(tokens)

    done = 0



    async def _set_one(token: str) -> bool:

        async with sem:

            try:

                await asyncio.wait_for(

                    set_created_bot_avatar(token, photo_bytes),

                    timeout=30,

                )

                return True

            except Exception:

                return False



    async def _wrapper(token: str) -> None:

        nonlocal ok, fail, done

        res = await _set_one(token)

        if res:

            ok += 1

        else:

            fail += 1

        done += 1

        if progress_callback:

            try:

                await progress_callback(done, total, ok, fail)

            except Exception:

                pass



    tasks = [asyncio.create_task(_wrapper(t)) for t in tokens]

    if tasks:

        await asyncio.gather(*tasks)

    return ok, fail

