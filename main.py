import math
import time
import datetime
import os
import uuid
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from sqlalchemy import text, func

import models
import schemas
import auth
import ai_service
import v12_service
import routes_v13
from database import engine, get_db

# สร้างตารางในฐานข้อมูลอัตโนมัติตอน start (ถ้ายังไม่มี)
# ตอนรัน docker compose ครั้งแรก Postgres ใช้เวลาตั้งต้นสักพัก ถ้า API ยิงเข้าไปก่อนจะได้ "Connection refused"
# จึงลองต่อใหม่ซ้ำ ๆ (สูงสุด ~60 วินาที) แทนที่จะปิดตัวเองทันที
def _init_db(retries: int = 30, delay: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            models.Base.metadata.create_all(bind=engine)
            return
        except OperationalError as e:
            if attempt == retries:
                raise
            print(f"[startup] ฐานข้อมูลยังไม่พร้อม (ครั้งที่ {attempt}/{retries}) รอ {delay:.0f} วินาที...", flush=True)
            time.sleep(delay)


_init_db()

app = FastAPI(
    title="CookAI API",
    description="REST API ของ CookAI: Authentication, User Management และ AI Food Analysis (Gemini)",
    version="1.3.0",
)
app.include_router(routes_v13.router)

# เปิด CORS ให้ frontend (CookAI_Frontend.html) เรียก API จากเบราว์เซอร์ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ใน production ควรระบุ domain จริงแทน "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "CookAI API"}


# เสิร์ฟหน้าเว็บ login/frontend ตรง ๆ จาก backend ตัวเดียวกัน
# (เข้า URL หลักของ Render แล้วจะเจอหน้านี้ทันที แทนที่จะเจอแค่ JSON)
@app.get("/", tags=["Health"])
def serve_frontend():
    return FileResponse("CookAI_login.html")


# ==================== 1. Authentication ====================

@app.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="username นี้ถูกใช้ไปแล้ว")

    if payload.email:
        existing_email = db.query(models.User).filter(models.User.email == payload.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="email นี้ถูกใช้ไปแล้ว")

    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
    )
    # ความปลอดภัย: สมัครเองได้เป็น user ปกติเท่านั้น ห้ามได้ role admin จากการตั้งชื่อ
    # ถ้าจะตั้ง admin ให้รัน:  python make_admin.py <username>
    db.add(user)
    db.commit()
    db.refresh(user)
    v12_service.ensure_free_subscription(db, user.id)
    return user


@app.post("/login", response_model=schemas.TokenResponse, tags=["Authentication"])
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not auth.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="username หรือ password ไม่ถูกต้อง")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="บัญชีนี้ถูกระงับการใช้งาน")

    token = auth.create_access_token(data={"sub": user.username})
    return schemas.TokenResponse(access_token=token)

@app.post("/token", include_in_schema=False)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(
        models.User.username == form_data.username
    ).first()

    if not user or not auth.verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="username หรือ password ไม่ถูกต้อง",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="บัญชีนี้ถูกระงับการใช้งาน"
        )

    token = auth.create_access_token(
        data={"sub": user.username}
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/logout", response_model=schemas.MessageResponse, tags=["Authentication"])
def logout(
    token: str = Depends(auth.oauth2_scheme),
    current_user: models.User = Depends(auth.get_current_user),
):
    auth.token_blacklist.add(token)
    return schemas.MessageResponse(message="ออกจากระบบสำเร็จ")


@app.post("/change-password", response_model=schemas.MessageResponse, tags=["Authentication"])
def change_password(
    payload: schemas.ChangePasswordRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not auth.verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="รหัสผ่านเดิมไม่ถูกต้อง")

    current_user.hashed_password = auth.hash_password(payload.new_password)
    db.commit()
    return schemas.MessageResponse(message="เปลี่ยนรหัสผ่านสำเร็จ")


@app.post("/forgot-password", response_model=schemas.ForgotPasswordResponse, tags=["Authentication"])
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    ขอ reset password ด้วย username

    หมายเหตุสำคัญ: โปรเจกต์นี้ยังไม่มีระบบส่งอีเมลจริง (ต้องใช้บริการอย่าง SendGrid/SMTP
    ซึ่งนอกเหนือขอบเขตวิชานี้) จึงส่ง reset_token กลับมาใน response ตรง ๆ เพื่อให้ทดสอบ
    flow ได้ครบ ในระบบจริงห้ามทำแบบนี้เด็ดขาด — ต้องส่ง token ไปทางอีเมลของเจ้าของบัญชีเท่านั้น
    ไม่ใช่ตอบกลับใน API response ตรง ๆ เพราะใครก็เดา/ยิง username เข้ามาแล้วได้ token ไปเปลี่ยน
    รหัสผ่านคนอื่นได้ทันที
    """
    user = db.query(models.User).filter(models.User.username == payload.username).first()

    # ไม่บอกตรง ๆ ว่า username นี้มีอยู่จริงไหม (กัน user enumeration) แต่ตอบข้อความเดียวกันเสมอ
    generic_message = "ถ้ามีบัญชีนี้อยู่ในระบบ จะสามารถใช้ reset token ด้านล่างเพื่อตั้งรหัสผ่านใหม่ได้"

    if not user:
        return schemas.ForgotPasswordResponse(message=generic_message, reset_token=None)

    token = auth.generate_reset_token()
    user.reset_token = token
    user.reset_token_expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    db.commit()

    return schemas.ForgotPasswordResponse(message=generic_message, reset_token=token)


@app.post("/reset-password", response_model=schemas.MessageResponse, tags=["Authentication"])
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.reset_token == payload.reset_token).first()

    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="reset token ไม่ถูกต้องหรือหมดอายุแล้ว กรุณาขอใหม่")

    user.hashed_password = auth.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return schemas.MessageResponse(message="ตั้งรหัสผ่านใหม่สำเร็จ กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่")


# ==================== 2. User Management ====================

@app.get("/me", response_model=schemas.UserOut, tags=["User Management"])
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.get("/users", response_model=schemas.PaginatedUsers, tags=["User Management"])
def list_users(
    page: int = 1,
    limit: int = 10,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ Admin")
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10

    total = db.query(models.User).count()
    items = (
        db.query(models.User)
        .order_by(models.User.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return schemas.PaginatedUsers(total=total, page=page, limit=limit, items=items)


@app.get("/users/{user_id}", response_model=schemas.UserOut, tags=["User Management"])
def get_user(
    user_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if user_id != current_user.id and getattr(current_user, "role", "user") != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ดูข้อมูลของผู้ใช้คนอื่น")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบ user นี้")
    return user


@app.put("/users/{user_id}", response_model=schemas.UserOut, tags=["User Management"])
def update_user(
    user_id: int,
    payload: schemas.UserUpdateRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบ user นี้")

    # อนุญาตให้แก้ไขได้เฉพาะข้อมูลของตัวเอง (จำกัดสิทธิ์ง่าย ๆ)
    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์แก้ไขข้อมูลของผู้ใช้คนอื่น")

    if payload.email is not None:
        user.email = payload.email
    if payload.is_active is not None:
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}", response_model=schemas.MessageResponse, tags=["User Management"])
def delete_user(
    user_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="ไม่พบ user นี้")

    if user.id != current_user.id:
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ลบข้อมูลของผู้ใช้คนอื่น")

    db.delete(user)
    db.commit()
    return schemas.MessageResponse(message="ลบ user สำเร็จ")


@app.get("/check-username/{username}", response_model=schemas.UsernameAvailability, tags=["User Management"])
def check_username(username: str, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == username).first()
    return schemas.UsernameAvailability(username=username, available=existing is None)


# ==================== 3. AI Food Analysis ====================

@app.post("/analyze-food", response_model=schemas.AnalyzeFoodResponse, tags=["AI"])
def analyze_food(
    payload: schemas.AnalyzeFoodRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """V1.2: check usage first, charge only after successful AI result."""
    usage = v12_service.usage_status(db, current_user.id)
    if usage["remaining"] <= 0:
        raise HTTPException(status_code=429, detail="โควตา AI วันนี้หมดแล้ว กรุณารอ Daily Reset หรืออัปเกรด Plan")
    try:
        result = ai_service.analyze(payload)
        # Only successful AI result consumes one usage.
        v12_service.increment_usage(db, current_user.id)
        db.commit()
        return result
    except ai_service.AIError as e:
        db.rollback()
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ==================== 4. V1.2 Usage / Subscription / Payment ====================

def _admin_only(current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์ Admin")
    return current_user


@app.get("/usage", response_model=schemas.UsageOut, tags=["Usage"])
def get_usage(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    u = v12_service.usage_status(db, current_user.id)
    return schemas.UsageOut(plan_name=u["plan"].name, subscription_status=u["subscription"].status,
                             usage_date=u["date"], used=u["used"], limit=u["limit"], remaining=u["remaining"])


@app.get("/subscription/plans", response_model=list[schemas.PlanOut], tags=["Subscription"])
def get_plans(db: Session = Depends(get_db)):
    v12_service.ensure_plans(db)
    return db.query(models.Plan).filter(models.Plan.is_active == True).order_by(models.Plan.price).all()


@app.get("/subscription", response_model=schemas.SubscriptionOut, tags=["Subscription"])
def get_subscription(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    u = v12_service.usage_status(db, current_user.id)
    plan = u["plan"]
    sub = u["subscription"]
    return schemas.SubscriptionOut(plan=plan, status=sub.status, start_date=sub.start_date, expire_date=sub.expire_date)


@app.post("/subscription/subscribe", response_model=schemas.SubscriptionOut, tags=["Subscription"])
def subscribe(payload: schemas.SubscribeRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    raise HTTPException(status_code=402, detail="ต้องชำระผ่าน Payment ก่อนจึงจะเปิด Paid Subscription ได้")


@app.post("/subscription/cancel", response_model=schemas.MessageResponse, tags=["Subscription"])
def cancel_subscription(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    sub = db.query(models.Subscription).filter(models.Subscription.user_id == current_user.id, models.Subscription.status == "active").order_by(models.Subscription.expire_date.desc()).first()
    if not sub:
        raise HTTPException(status_code=404, detail="ไม่พบ Subscription ที่ใช้งานอยู่")
    sub.status = "cancelled"
    db.commit()
    return schemas.MessageResponse(message="ยกเลิก Subscription แล้ว สิทธิ์ปัจจุบันจะไม่ต่ออายุอัตโนมัติ")


@app.post("/payment/create", response_model=schemas.PaymentOut, tags=["Payment"])
def create_payment(payload: schemas.PaymentCreateRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    v12_service.ensure_plans(db)
    plan = db.query(models.Plan).filter(models.Plan.id == payload.plan_id, models.Plan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="ไม่พบ Plan")
    if plan.price <= 0:
        raise HTTPException(status_code=400, detail="Free Plan ไม่ต้องชำระเงิน")
    tx = models.Payment(transaction_id=f"TX-{uuid.uuid4().hex[:16].upper()}", user_id=current_user.id, plan_id=plan.id, amount=plan.price, status="pending", provider="sandbox")
    db.add(tx)
    db.commit(); db.refresh(tx)
    return tx


@app.get("/payment/status/{payment_id}", response_model=schemas.PaymentOut, tags=["Payment"])
def payment_status(payment_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    p = db.query(models.Payment).filter(models.Payment.id == payment_id, models.Payment.user_id == current_user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบ Payment")
    return p


@app.post("/payment/webhook", response_model=schemas.PaymentOut, tags=["Payment"])
def payment_webhook(payment_id: int, success: bool = True, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """Sandbox provider callback simulator. Production must verify provider signature."""
    p = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="ไม่พบ Payment")
    if p.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="ไม่มีสิทธิ์")
    if p.status == "success":
        return p
    if success:
        v12_service.activate_subscription(db, p)
    else:
        p.status = "failed"
        db.commit(); db.refresh(p)
    return p


@app.get("/dashboard", response_model=schemas.DashboardOut, tags=["Dashboard"])
def dashboard(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    u = v12_service.usage_status(db, current_user.id)
    plan = u["plan"]; sub = u["subscription"]
    payments = db.query(models.Payment).filter(models.Payment.user_id == current_user.id).order_by(models.Payment.created_at.desc()).limit(10).all()
    sub_out = schemas.SubscriptionOut(plan=plan, status=sub.status, start_date=sub.start_date, expire_date=sub.expire_date)
    usage_out = schemas.UsageOut(plan_name=plan.name, subscription_status=sub.status, usage_date=u["date"], used=u["used"], limit=u["limit"], remaining=u["remaining"])
    return schemas.DashboardOut(username=current_user.username, plan=plan, subscription=sub_out, usage=usage_out, recent_payments=payments)


@app.get("/admin/dashboard", response_model=schemas.AdminDashboardOut, tags=["Admin"])
def admin_dashboard(current_user: models.User = Depends(_admin_only), db: Session = Depends(get_db)):
    today = v12_service.today_bangkok()
    month_start = today.replace(day=1)
    total = db.query(models.User).count()
    free = db.query(models.User).join(models.Subscription, models.Subscription.user_id == models.User.id).join(models.Plan, models.Plan.id == models.Subscription.plan_id).filter(models.Subscription.status == "active", models.Plan.name == "Free").count()
    paid = db.query(models.User).join(models.Subscription, models.Subscription.user_id == models.User.id).join(models.Plan, models.Plan.id == models.Subscription.plan_id).filter(models.Subscription.status == "active", models.Plan.name != "Free").count()
    active = db.query(models.Subscription).filter(models.Subscription.status == "active", models.Subscription.expire_date > datetime.datetime.utcnow()).count()
    expired = db.query(models.Subscription).filter((models.Subscription.status == "expired") | (models.Subscription.expire_date <= datetime.datetime.utcnow())).count()
    usage_today = db.query(func.coalesce(func.sum(models.UsageDaily.used), 0)).filter(models.UsageDaily.usage_date == today).scalar() or 0
    usage_month = db.query(func.coalesce(func.sum(models.UsageDaily.used), 0)).filter(models.UsageDaily.usage_date >= month_start).scalar() or 0
    cost_per = float(os.getenv("AI_COST_PER_USAGE_THB", "1.0"))
    revenue = db.query(func.coalesce(func.sum(models.Payment.amount), 0)).filter(models.Payment.status == "success").scalar() or 0
    return schemas.AdminDashboardOut(total_users=total, free_users=free, paid_users=paid, active_subscriptions=active, expired_subscriptions=expired,
        ai_usage_today=int(usage_today), ai_usage_this_month=int(usage_month), estimated_ai_cost=round(float(usage_month) * cost_per, 2),
        subscription_revenue=round(float(revenue), 2), cost_note="ค่าประมาณจาก AI_COST_PER_USAGE_THB ไม่ใช่ระบบบัญชีเต็มรูปแบบ", revenue_note="ยอดจาก Payment record ในระบบ ไม่ใช่ระบบบัญชีเต็มรูปแบบ")


def _admin_users(db):
    users = db.query(models.User).order_by(models.User.id).all()
    out=[]
    today=v12_service.today_bangkok()
    for user in users:
        u=v12_service.usage_status(db,user.id)
        out.append(schemas.AdminUserOut(id=user.id, username=user.username, email=user.email, role=user.role, is_active=user.is_active,
            plan_name=u["plan"].name, subscription_status=u["subscription"].status, usage_used=u["used"], usage_limit=u["limit"]))
    return out

@app.get("/admin/users", response_model=list[schemas.AdminUserOut], tags=["Admin"])
def admin_users(current_user: models.User = Depends(_admin_only), db: Session = Depends(get_db)):
    return _admin_users(db)

@app.get("/admin/usage", tags=["Admin"])
def admin_usage(current_user: models.User = Depends(_admin_only), db: Session = Depends(get_db)):
    rows=db.query(models.UsageDaily).order_by(models.UsageDaily.usage_date.desc()).limit(100).all()
    return [{"user_id":r.user_id,"usage_date":r.usage_date,"used":r.used} for r in rows]

@app.get("/admin/subscriptions", tags=["Admin"])
def admin_subscriptions(current_user: models.User = Depends(_admin_only), db: Session = Depends(get_db)):
    rows=db.query(models.Subscription).order_by(models.Subscription.expire_date.desc()).limit(100).all()
    return [{"id":r.id,"user_id":r.user_id,"plan_id":r.plan_id,"status":r.status,"start_date":r.start_date,"expire_date":r.expire_date} for r in rows]

@app.get("/admin/payments", response_model=list[schemas.PaymentOut], tags=["Admin"])
def admin_payments(current_user: models.User = Depends(_admin_only), db: Session = Depends(get_db)):
    return db.query(models.Payment).order_by(models.Payment.created_at.desc()).limit(100).all()
