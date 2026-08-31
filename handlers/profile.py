from datetime import timedelta



from aiogram import F, Router

from aiogram.types import CallbackQuery



from core.db import now_msk

from handlers.utils import upsert_callback_user

from keyboards.menu import PROFILE, PROFILE_RATING, menu_kb, profile_kb

from repositories.account import count_accounts

from repositories.created_bot import (

    count_created_bots_by_owner,

    count_created_bots_by_owner_since,

    count_created_bots_since,

    count_created_bots_total,

    get_top_owners,

)

from texts.profile import format_profile, format_rating





def _day_start():

    now = now_msk()

    return now.replace(hour=0, minute=0, second=0, microsecond=0)





def _week_start():

    now = now_msk()

                     

    start = now - timedelta(days=now.weekday())

    return start.replace(hour=0, minute=0, second=0, microsecond=0)





async def open_profile(callback: CallbackQuery) -> None:

    owner = await upsert_callback_user(callback)

    my_total = await count_created_bots_by_owner(owner.id)

    my_day = await count_created_bots_by_owner_since(owner.id, _day_start())

    my_week = await count_created_bots_by_owner_since(owner.id, _week_start())

    my_accounts = await count_accounts(owner.id)

    global_total = await count_created_bots_total()

    global_day = await count_created_bots_since(_day_start())

    global_week = await count_created_bots_since(_week_start())

    text = format_profile(

        owner.username,

        owner.full_name,

        owner.telegram_id,

        my_total,

        my_day,

        my_week,

        my_accounts,

        global_total,

        global_day,

        global_week,

    )

    await callback.answer()

    if callback.message:

        try:

            await callback.message.edit_text(text, reply_markup=profile_kb())

        except Exception:

            await callback.message.answer(text, reply_markup=profile_kb())





async def open_rating(callback: CallbackQuery) -> None:

    top = await get_top_owners(10)

    text = format_rating(top)

    await callback.answer()

    if callback.message:

        try:

            await callback.message.edit_text(text, reply_markup=profile_kb())

        except Exception:

            await callback.message.answer(text, reply_markup=profile_kb())





def get_router() -> Router:

    router = Router(name="profile")

    router.callback_query.register(open_profile, F.data == PROFILE)

    router.callback_query.register(open_rating, F.data == PROFILE_RATING)

    return router

