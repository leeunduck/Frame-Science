from sqlalchemy import BigInteger, Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class UserAccount(Base):
    __tablename__ = 'user_account'
    __table_args__ = (CheckConstraint("role IN ('STUDENT', 'PARENT', 'STAFF')", name='ck_account_role'),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    phone: Mapped[str] = mapped_column(String(11), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
