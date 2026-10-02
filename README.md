# CookAI API — Authentication & User Management

REST API ที่สร้างด้วย FastAPI ครบตาม checklist:

**Authentication**
- `POST /register`
- `POST /login`
- `POST /logout`
- `POST /change-password`

**User Management**
- `GET /me`
- `GET /users/{id}`
- `GET /users` (มี pagination ด้วย `?page=&limit=`)
- `PUT /users/{id}`
- `DELETE /users/{id}`
- `GET /check-username/{name}`

---

## โครงสร้างไฟล์

```
cookai-api/
├── main.py            # endpoint ทั้งหมด
├── models.py           # ตาราง User (SQLAlchemy)
├── schemas.py          # รูปแบบ request/response (Pydantic)
├── auth.py             # hash password + JWT token
├── database.py          # เชื่อมต่อฐานข้อมูล
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

## เกี่ยวกับ Colab

Colab เขียนโค้ด Python ได้ แต่**รัน Docker ไม่ได้** (ไม่มีสิทธิ์ root เข้าถึง Docker daemon)
ดังนั้นให้ใช้ Colab หรือโปรแกรมแก้โค้ดอะไรก็ได้ (VS Code แนะนำ) แค่ **เขียน/แก้ไฟล์ .py**
แล้วค่อยเอาไฟล์มารันด้วย Docker บนเครื่องตัวเอง (หรือ VM ที่มี Docker) ตามขั้นตอนด้านล่าง

---

## ขั้นตอนที่ 1 — ติดตั้ง Docker Desktop (ถ้ายังไม่มี)

ทำตามคู่มือ Docker & FastAPI ของอาจารย์ (หัวข้อ 3):
- Windows: โหลดจาก docker.com/products/docker-desktop ต้องเปิด WSL2 ก่อน
- Mac: เลือกเวอร์ชันให้ตรงชิป (Apple Silicon / Intel)
- Linux: `sudo apt install -y docker.io docker-compose-v2`

ตรวจสอบว่าติดตั้งสำเร็จ:
```bash
docker --version
docker compose version
```

## ขั้นตอนที่ 2 — วางไฟล์โปรเจกต์

แตกไฟล์ zip ที่ให้มา จะได้โฟลเดอร์ `cookai-api/` เปิด terminal แล้ว `cd` เข้าไปในโฟลเดอร์นั้น

## ขั้นตอนที่ 3 — รันด้วย Docker Compose (API + Postgres พร้อมกัน)

```bash
docker compose up --build
```

คำสั่งนี้จะ:
1. Build image ของ API จาก `Dockerfile`
2. ดึง (pull) image ของ Postgres
3. รันทั้งสอง container พร้อมกัน แล้วเชื่อม network ให้อัตโนมัติ
   (API เรียกฐานข้อมูลด้วยชื่อ service `db` ตามที่ตั้งไว้ใน `DATABASE_URL`)

รอจนเห็นบรรทัดประมาณ `Uvicorn running on http://0.0.0.0:8000` แปลว่าใช้งานได้แล้ว

รันแบบ background (ไม่ค้าง terminal): เพิ่ม `-d`
```bash
docker compose up --build -d
```

## ขั้นตอนที่ 4 — ทดสอบ API

เปิดเบราว์เซอร์ไปที่:
```
http://localhost:8000/docs
```

จะเห็นหน้า Swagger UI ที่ FastAPI สร้างให้อัตโนมัติ ลองกด **Try it out** ที่ `POST /register`
กรอก username/password แล้วกด Execute จะได้ user ใหม่ทันที จากนั้นลอง `POST /login` เพื่อรับ
token แล้วเอา token ไปใส่ในปุ่ม **Authorize** (มุมขวาบนของหน้า Swagger) เพื่อเรียก endpoint
ที่ต้อง login (`/me`, `/users`, ...) ได้

## คำสั่ง Docker ที่ใช้บ่อย

```bash
docker compose ps              # ดูสถานะ container
docker compose logs -f api     # ดู log ของ service api แบบ real-time
docker compose exec api bash   # เข้าไปสำรวจข้างใน container ของ api
docker compose down            # หยุดและลบ container/network (ข้อมูลใน volume ยังอยู่)
docker compose down -v         # หยุดและลบ volume ด้วย (ข้อมูลฐานข้อมูลหายหมด)
```

## แก้โค้ดแล้วอยากเห็นผลทันที

`docker-compose.yml` ผูก volume `.:/app` ไว้แล้ว โค้ดที่แก้บนเครื่อง host จะ sync เข้า
container ทันที แต่ uvicorn ยังไม่ auto-reload (ตั้งใจปิดไว้เพราะใน production ไม่ควรใช้)
ถ้าอยากได้ auto-reload ตอน dev ให้แก้บรรทัดสุดท้ายของ `Dockerfile` ชั่วคราวเป็น:
```
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```
แล้ว `docker compose up --build` ใหม่

## ทดสอบโดยไม่ใช้ Docker เลย (รันตรงบนเครื่อง เร็วกว่าตอน dev)

ถ้าอยากรันเร็ว ๆ โดยไม่ผ่าน Docker ก่อน (จะได้ auto-reload และ debug ง่ายกว่า) ระบบจะ
fallback ไปใช้ SQLite ไฟล์เดียวให้อัตโนมัติถ้าไม่ได้ตั้ง `DATABASE_URL`:
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## เชื่อมกับ Frontend — ไฟล์ CookAI_with_login.html

ไฟล์นี้คือ `CookAI_Frontend.html` เดิม **ที่เพิ่มหน้า Login/Register เข้าไปข้างหน้าแล้ว**
เชื่อมกับ API ชุดนี้ตรง ๆ ผ่าน `fetch()` เปิดไฟล์นี้ในเบราว์เซอร์ได้เลยหลังจากรัน `uvicorn`
(ดูขั้นตอนรัน server ด้านบน) ไม่ต้องตั้งค่าอะไรเพิ่ม

การไหลของหน้าจอ:
1. เปิดมาเจอหน้า **Login** ก่อน
2. ยังไม่มีบัญชี → กด "สมัครสมาชิก" → กรอกข้อมูล → ระบบพากลับมาหน้า Login ให้อัตโนมัติ
3. Login สำเร็จ → **เข้าแอปจริงทันที** ไปหน้า Dashboard (หน้าเดิมของ CookAI ที่มีปุ่มถ่ายรูปคิดเมนู)
   ชื่อผู้ใช้ที่ล็อกอินจะไปโชว์แทนที่ "น้องบาส" อัตโนมัติ
4. กดที่วงกลมอวตาร์มุมขวาบนของ Dashboard เพื่อ **ออกจากระบบ** กลับไปหน้า Login

ไฟล์ `CookAI.html` เดิมที่ส่งมายังใช้ได้ปกติ (เป็น demo แบบไม่ต้อง login) ส่วน
`CookAI_with_login.html` คือเวอร์ชันที่ต่อกับ API จริงแล้ว

## เช็คลิสต์ว่าทุกอย่างใช้งานได้จริง

- [ ] หน้า Login มีลิงก์ "ลืมรหัสผ่าน?" กดแล้วไปหน้ากรอก username
- [ ] กด "ขอรีเซ็ตรหัสผ่าน" แล้วได้กล่อง reset token โผล่มา (โหมด demo — ระบบจริงต้องส่งอีเมลแทน)
- [ ] กด "ไปตั้งรหัสผ่านใหม่" → token ถูกกรอกให้อัตโนมัติ → ใส่รหัสผ่านใหม่ → กดยืนยันสำเร็จ
- [ ] Login ด้วยรหัสผ่านใหม่ได้ (รหัสเก่าใช้ไม่ได้แล้ว)
- [ ] ที่หน้า Dashboard กดแท็บ "กะเพรา" (หรือแท็บอื่น) แล้วมีการ์ดสูตรอาหารโผล่มาใต้แท็บ
      พร้อมวัตถุดิบ/เวลา/ขั้นตอนทำ
- [ ] กด "ทั้งหมด" แล้วการ์ดสูตรอาหารหายไป (ยังไม่เจาะจงเมนู)
- [ ] กดลูกศรขวาที่การ์ด "ไอเดียประจำวัน" แล้วข้อความเปลี่ยนไปเรื่อย ๆ วนลูป

- [ ] เปิด `http://127.0.0.1:8000/docs` เห็น endpoint ครบ 10 ตัว (register, login, logout,
      change-password, me, users, users/{id} x3, check-username)
- [ ] เปิด `CookAI_with_login.html` เจอหน้า Login ก่อน
- [ ] กดสมัครสมาชิก กรอกข้อมูล → ได้ข้อความ "สมัครสำเร็จ" → เด้งกลับหน้า Login เอง
- [ ] Login ด้วยบัญชีที่สมัคร → เข้าหน้า Dashboard ของ CookAI ได้ทันที เห็นชื่อ user โผล่แทน "น้องบาส"
- [ ] กดวงกลมอวตาร์มุมขวาบน → กลับไปหน้า Login ได้ (แปลว่า logout สำเร็จ)
- [ ] ปิด-เปิด `uvicorn` ใหม่ แล้ว login ด้วยบัญชีเดิมได้อีก → แปลว่าข้อมูลถูกบันทึกจริง ไม่หายไปไหน

ถ้าทำครบทุกข้อ = ระบบพร้อม present แล้ว

## ข้อมูลถูกเก็บที่ไหน (ไม่ต้อง setup อะไรเพิ่ม)

ตอนรันแบบ `uvicorn main:app --reload` (ไม่ผ่าน Docker) ระบบจะสร้างไฟล์ `cookai.db`
(SQLite) ขึ้นในโฟลเดอร์เดียวกันให้อัตโนมัติตั้งแต่ครั้งแรกที่รัน — ข้อมูล user ทุกคนที่สมัคร
ถูกเก็บอยู่ในไฟล์นี้ถาวร ปิด-เปิดเครื่องใหม่ก็ไม่หาย **อย่าลบไฟล์นี้** ถ้าไม่อยากให้ข้อมูล user หาย

## วิธีเก็บ/ส่งงาน

รวบไฟล์ทั้งโฟลเดอร์ `cookai-api/` เป็น zip ส่งได้เลย (ไม่ต้องรวมโฟลเดอร์ `venv/` หรือไฟล์
`cookai.db` เพราะสร้างขึ้นใหม่ได้เสมอตอนรัน) ถ้าใช้ git ให้สร้างไฟล์ `.gitignore` ที่มีบรรทัด
`venv/` และ `cookai.db` กันไม่ให้ push ขึ้นไปโดยไม่ตั้งใจ

## หมายเหตุด้านความปลอดภัย (สำหรับส่งงาน พอเข้าใจแนวคิด)

- `SECRET_KEY` และรหัสผ่าน Postgres ใน `docker-compose.yml` เป็นค่า placeholder — ห้ามใช้จริงใน
  production ควรอ่านจากไฟล์ `.env` ที่ไม่ push ขึ้น git
- ระบบ logout ใช้ token blacklist แบบเก็บใน memory เพื่อความง่าย เหมาะกับงานเรียน/dev เท่านั้น
  ของจริงควรใช้ Redis เพื่อให้ใช้ได้ตอนมีหลาย instance และไม่หายตอน restart
