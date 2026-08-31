from core.config import ADMIN_IDS

from repositories.user import has_user_access





def is_admin_id(telegram_id: int) -> bool:

    return telegram_id in ADMIN_IDS





async def can_use_bot(telegram_id: int) -> bool:

    return is_admin_id(telegram_id) or await has_user_access(telegram_id)

