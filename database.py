import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ถ้ามี DATABASE_URL ใน environment (เช่นตอนรันผ่าน docker-compose ที่ต่อกับ Postgres)
# จะใช้ค่านั้น ถ้าไม่มีจะ fallback ไปใช้ SQLite ไฟล์เดียว (เหมาะกับตอน dev/ทดสอบเร็ว ๆ)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cookai.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency สำหรับ FastAPI: เปิด session ต่อ request แล้วปิดให้อัตโนมัติ"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
