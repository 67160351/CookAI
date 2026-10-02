import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # สำหรับระบบลืมรหัสผ่าน: เก็บ token ชั่วคราว + เวลาหมดอายุ
    reset_token = Column(String(64), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)
