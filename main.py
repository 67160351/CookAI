import math
import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models
import schemas
import auth
from database import engine, get_db

# สร้างตารางในฐานข้อมูลอัตโนมัติตอน start (ถ้ายังไม่มี)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CookAI API",
    description="REST API สำหรับระบบ Authentication และ User Management ของโปรเจกต์ CookAI",
    version="1.0.0",
)

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
    db.add(user)
    db.commit()
    db.refresh(user)
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
