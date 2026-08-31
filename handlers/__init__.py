from aiogram import Router



from handlers.accounts import get_router as get_accounts_router

from handlers.admin import get_router as get_admin_router

from handlers.profile import get_router as get_profile_router

from handlers.start import get_router as get_start_router

from handlers.tokens import get_router as get_tokens_router

from middlewares.access import AccessMiddleware





def get_router() -> Router:

    router = Router(name="root")

    router.message.middleware(AccessMiddleware())

    router.callback_query.middleware(AccessMiddleware())

    router.include_router(get_start_router())

    router.include_router(get_admin_router())

    router.include_router(get_profile_router())

    router.include_router(get_accounts_router())

    router.include_router(get_tokens_router())

    return router

