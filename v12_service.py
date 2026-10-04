import datetime
import os
import uuid
from zoneinfo import ZoneInfo
from sqlalchemy import func
from sqlalchemy.orm import Session
import models

BANGKOK = ZoneInfo("Asia/Bangkok")


def today_bangkok():
    return datetime.datetime.now(BANGKOK).date()


def now_utc_naive():
    return datetime.datetime.utcnow()


def ensure_plans(db: Session):
    free = db.query(models.Plan).filter(models.Plan.name == "Free").first()
    if not free:
        free = models.Plan(name="Free", price=0, duration_days=1, usage_limit=int(os.getenv("FREE_DAILY_USAGE", "2")), is_active=True)
        db.add(free)
    paid = db.query(models.Plan).filter(models.Plan.name == "Pro").first()
    if not paid:
        paid = models.Plan(name="Pro", price=float(os.getenv("PRO_PLAN_PRICE", "99")), duration_days=int(os.getenv("PRO_PLAN_DAYS", "30")), usage_limit=int(os.getenv("PRO_DAILY_USAGE", "30")), is_active=True)
        db.add(paid)
    db.commit()
    return free, paid


def get_free_plan(db):
    free, _ = ensure_plans(db)
    return free


def get_effective_subscription(db, user_id):
    sub = (db.query(models.Subscription)
           .filter(models.Subscription.user_id == user_id, models.Subscription.status == "active")
           .order_by(models.Subscription.expire_date.desc()).first())
    now = now_utc_naive()
    if sub and sub.expire_date > now:
        return sub
    if sub:
        sub.status = "expired"
        db.commit()
    free = get_free_plan(db)
    return models.Subscription(id=None, user_id=user_id, plan_id=free.id, status="active", start_date=now, expire_date=now + datetime.timedelta(days=1), plan=free)


def ensure_free_subscription(db, user_id):
    sub = (db.query(models.Subscription).filter(models.Subscription.user_id == user_id, models.Subscription.status == "active").order_by(models.Subscription.expire_date.desc()).first())
    if sub and sub.expire_date > now_utc_naive():
        return sub
    if sub:
        sub.status = "expired"
    free = get_free_plan(db)
    now = now_utc_naive()
    sub = models.Subscription(user_id=user_id, plan_id=free.id, status="active", start_date=now, expire_date=now + datetime.timedelta(days=1))
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def usage_status(db, user_id):
    sub = ensure_free_subscription(db, user_id)
    # refresh effective plan if subscription expired between calls
    if sub.expire_date <= now_utc_naive():
        sub.status = "expired"
        db.commit()
        sub = ensure_free_subscription(db, user_id)
    plan = db.query(models.Plan).filter(models.Plan.id == sub.plan_id).first()
    day = today_bangkok()
    row = db.query(models.UsageDaily).filter_by(user_id=user_id, usage_date=day).first()
    used = row.used if row else 0
    return {"plan": plan, "subscription": sub, "used": used, "limit": plan.usage_limit, "remaining": max(plan.usage_limit - used, 0), "date": day}


def increment_usage(db, user_id):
    day = today_bangkok()
    row = db.query(models.UsageDaily).filter_by(user_id=user_id, usage_date=day).first()
    if not row:
        # กัน race: request พร้อมกันที่สร้างแถววันนี้ครั้งแรก (unique user_id+date) ให้ใช้แถวที่อีกฝั่งสร้างแทน
        from sqlalchemy.exc import IntegrityError
        try:
            with db.begin_nested():
                row = models.UsageDaily(user_id=user_id, usage_date=day, used=0)
                db.add(row)
                db.flush()
        except IntegrityError:
            row = db.query(models.UsageDaily).filter_by(user_id=user_id, usage_date=day).first()
    row.used += 1
    db.flush()
    return row.used


def activate_subscription(db, payment):
    now = now_utc_naive()
    # expire prior active subscription, then create paid subscription
    prior = db.query(models.Subscription).filter(models.Subscription.user_id == payment.user_id, models.Subscription.status == "active").all()
    for s in prior:
        s.status = "expired"
    plan = db.query(models.Plan).filter(models.Plan.id == payment.plan_id).first()
    sub = models.Subscription(user_id=payment.user_id, plan_id=plan.id, status="active", start_date=now, expire_date=now + datetime.timedelta(days=plan.duration_days))
    db.add(sub)
    payment.status = "success"
    payment.paid_at = now
    payment.provider_reference = payment.provider_reference or f"SANDBOX-{uuid.uuid4().hex[:12].upper()}"
    db.commit()
    db.refresh(sub)
    return sub
