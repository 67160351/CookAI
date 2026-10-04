# CookAI V1.2

V1.2 เพิ่ม Business/Management Layer รอบ Core AI เดิม: Usage, Subscription, Payment Sandbox, User Dashboard และ Admin Dashboard โดยคง `/analyze-food` contract เดิมไว้

## 1) Run with Docker

```bash
docker compose up --build
```

เปิด:
- http://localhost:8000
- http://localhost:8000/docs

## 2) Environment

คัดลอก `.env.example` เป็น `.env` แล้วใส่ค่าจริง:

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
SECRET_KEY=<สุ่มยาวๆ>
FREE_DAILY_USAGE=2
PRO_DAILY_USAGE=30
PRO_PLAN_PRICE=99
PRO_PLAN_DAYS=30
AI_COST_PER_USAGE_THB=1.0
```

ห้าม commit หรือส่ง `.env` ใน ZIP

ตั้ง Admin: สมัครบัญชีปกติก่อน แล้วรัน `python make_admin.py <username>` (หรือใน Docker: `docker compose exec api python make_admin.py <username>`) — สมัครเองไม่สามารถเป็น admin ได้

`SECRET_KEY` ต้องตั้งใน `.env` (docker compose จะไม่ยอมรันถ้าว่าง)

## 3) V1.2 API

### Usage
- `GET /usage`
- `POST /analyze-food` — Usage ถูกหักเมื่อ AI สำเร็จเท่านั้น

### Subscription
- `GET /subscription/plans`
- `GET /subscription`
- `POST /subscription/subscribe`
- `POST /subscription/cancel`

### Payment Sandbox
- `POST /payment/create`
- `GET /payment/status/{id}`
- `POST /payment/webhook?payment_id={id}&success=true|false`

`/payment/webhook` ในชุดนี้เป็น Sandbox/Test simulator สำหรับงานพัฒนา ไม่ใช่ production provider webhook

### Dashboard
- `GET /dashboard`

### Admin
- `GET /admin/dashboard`
- `GET /admin/users`
- `GET /admin/usage`
- `GET /admin/subscriptions`
- `GET /admin/payments`

## 4) วิธี Test แบบเร็วผ่าน Swagger

1. Register user A
2. Login → copy Bearer token → Authorize
3. `GET /usage` → ต้องเป็น Free, limit 2
4. `POST /analyze-food` สำเร็จ → used 1
5. ยิงอีกครั้ง → used 2
6. ยิงครั้งที่ 3 → 429
7. ทดสอบ AI error/validation → usage ต้องไม่เพิ่ม
8. `GET /subscription/plans` → เลือก Pro
9. `POST /payment/create` → ได้ Pending
10. `POST /payment/webhook?payment_id=...&success=false` → Failed, ยัง Free
11. สร้าง payment ใหม่ แล้ว webhook success=true → Subscription เป็น Pro
12. `GET /dashboard` → ตรวจ Plan/Usage/Start/Expire
13. สร้าง/กำหนด admin user แล้ว Login เป็น admin
14. `GET /admin/dashboard` → ต้องได้ข้อมูล
15. Login user ปกติแล้วเรียก `/admin/dashboard` → ต้อง 403

## 5) Automated Tests

ติดตั้ง dependencies:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q tests
```

หมายเหตุ: test environment ตั้ง `FREE_DAILY_USAGE=100` เฉพาะเพื่อให้ regression tests ของ V1.1 ยิง `/analyze-food` หลายครั้งได้; production/default ยังคง 2/day

## 6) Docker persistence

```bash
docker compose down
```

ไม่ลบ volume → PostgreSQL data ยังอยู่

```bash
docker compose down -v
```

ลบ volume → ข้อมูล DB หาย เหมาะสำหรับ reset test เท่านั้น

## 7) Scope ที่ยังไม่ใช่ Production

- Payment provider ยังเป็น Sandbox/Test simulator
- ยังไม่มี card processing จริง
- ยังไม่มี provider signature verification จริง
- Logout blacklist ยังเป็น memory ตาม baseline เดิม
- Cost/Revenue เป็นค่าประมาณจาก records ไม่ใช่ระบบบัญชี
