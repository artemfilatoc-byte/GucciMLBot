import asyncio

import logging

from collections.abc import Awaitable



logger = logging.getLogger(__name__)

_tasks: set[asyncio.Task[None]] = set()





def spawn_background_task(coro: Awaitable[None]) -> None:

    task = asyncio.create_task(coro)

    _tasks.add(task)



    def _done(done_task: asyncio.Task[None]) -> None:

        _tasks.discard(done_task)

        try:

            done_task.result()

        except asyncio.CancelledError:

            raise

        except Exception:

            logger.exception("Background task failed")



    task.add_done_callback(_done)

