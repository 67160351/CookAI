"""ตั้ง role=admin ให้ user ที่มีอยู่แล้ว:  python make_admin.py <username>  (เพิ่ม --revoke เพื่อถอน)"""
import sys
from dotenv import load_dotenv
load_dotenv()
from database import SessionLocal
import models

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python make_admin.py <username> [--revoke]")
    db = SessionLocal()
    u = db.query(models.User).filter_by(username=sys.argv[1]).first()
    if not u:
        sys.exit("ไม่พบ user นี้")
    u.role = "user" if "--revoke" in sys.argv else "admin"
    db.commit()
    print(f"{u.username} -> {u.role}")

if __name__ == "__main__":
    main()
