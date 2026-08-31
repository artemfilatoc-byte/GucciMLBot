import asyncio

import logging



from aiogram import Bot

from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest



from repositories.user import list_all_access_user_ids

from core.config import ADMIN_IDS



logger = logging.getLogger(__name__)





async def broadcast_to_all(bot: Bot, text: str, admin_telegram_id: int | None = None) -> dict:

    user_ids = await list_all_access_user_ids()

                                                                                                                                          

                                                                                        

    all_ids = set(user_ids) | set(ADMIN_IDS)

                                   

    total = len(all_ids)

    sent = 0

    failed = 0

    blocked = 0



    sem = asyncio.Semaphore(20)



    async def _send_one(uid: int):

        nonlocal sent, failed, blocked

        async with sem:

            try:

                await bot.send_message(uid, text)

                sent += 1

            except TelegramRetryAfter as exc:

                await asyncio.sleep(exc.retry_after)

                try:

                    await bot.send_message(uid, text)

                    sent += 1

                except Exception as e:

                    logger.warning("broadcast retry failed %s: %s", uid, e)

                    failed += 1

            except (TelegramForbiddenError, TelegramBadRequest) as exc:

                                               

                if "blocked" in str(exc).lower() or "forbidden" in str(exc).lower():

                    blocked += 1

                else:

                    failed += 1

            except Exception as exc:

                logger.warning("broadcast failed %s: %s", uid, exc)

                failed += 1

                                        

            await asyncio.sleep(0.05)



    tasks = [asyncio.create_task(_send_one(uid)) for uid in all_ids]

    if tasks:

        await asyncio.gather(*tasks)



    return {"total": total, "sent": sent, "failed": failed, "blocked": blocked}

