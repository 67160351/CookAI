import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Date, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    reset_token = Column(String(64), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    price = Column(Float, default=0.0, nullable=False)
    duration_days = Column(Integer, default=30, nullable=False)
    usage_limit = Column(Integer, default=2, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    status = Column(String(20), default="active", nullable=False)
    start_date = Column(DateTime, nullable=False)
    expire_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    plan = relationship("Plan")


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    usage_date = Column(Date, nullable=False, index=True)
    used = Column(Integer, default=0, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_usage_user_date"),)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(80), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    provider = Column(String(30), default="sandbox", nullable=False)
    provider_reference = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User")
    plan = relationship("Plan")
