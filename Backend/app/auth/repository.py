from sqlalchemy import select
from .models import UserAccount

def by_phone(db, phone, lock=False):
    statement = select(UserAccount).where(UserAccount.phone == phone)
    return db.scalar(statement.with_for_update() if lock else statement)

def by_id(db, user_id, lock=False):
    statement = select(UserAccount).where(UserAccount.id == user_id)
    return db.scalar(statement.with_for_update() if lock else statement)
