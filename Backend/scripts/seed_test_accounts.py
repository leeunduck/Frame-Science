"""Run from Backend: python -m scripts.seed_test_accounts"""
from sqlalchemy.dialects.postgresql import insert
from app.config import get_settings
from app.database import SessionLocal
from app.auth.models import UserAccount
from app.auth.security import hash_password

def main():
    if get_settings().app_env != 'local':
        raise SystemExit('Seed is available only in APP_ENV=local')
    with SessionLocal.begin() as db:
        for phone, role in [('01012345678', 'STUDENT'), ('01023456789', 'PARENT'), ('01034567890', 'STAFF')]:
            result = db.execute(insert(UserAccount).values(phone=phone, role=role, password_hash=hash_password(phone[-4:]), is_active=True).on_conflict_do_nothing(index_elements=['phone']).returning(UserAccount.id)).scalar_one_or_none()
            print(f'{role}: {phone} / initial password: {phone[-4:]}' if result is not None else f'{role}: {phone} already exists (unchanged)')

if __name__ == '__main__':
    main()
