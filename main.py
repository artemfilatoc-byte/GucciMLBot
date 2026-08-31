import asyncio

import logging



from aiogram import Bot, Dispatcher

from aiogram.client.default import DefaultBotProperties

from aiogram.enums import ParseMode

from aiogram.fsm.storage.memory import MemoryStorage



from core.config import BOT_TOKEN

from core.db import init_db

from handlers import get_router

from handlers.tokens import resume_pending_token_batches





async def main() -> None:

    logging.basicConfig(level=logging.INFO)



    await init_db()



    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dispatcher = Dispatcher(storage=MemoryStorage())

    dispatcher.include_router(get_router())

    await resume_pending_token_batches(bot)



    await bot.delete_webhook(drop_pending_updates=True)

    await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())





if __name__ == "__main__":

    asyncio.run(main())

