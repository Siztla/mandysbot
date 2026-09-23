from database import db


async def is_admin(user_id: int) -> bool:
    admin_ids = await db.get_admin_ids()
    return user_id in admin_ids
