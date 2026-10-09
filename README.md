# CookAI V1.3

**AI Food Recommendation Web Application**

CookAI เป็นเว็บแอปพลิเคชันที่ใช้ AI ช่วยแนะนำเมนูอาหารจากวัตถุดิบที่ผู้ใช้มี โดยผู้ใช้สามารถกรอกชื่อวัตถุดิบ ปริมาณ และหน่วย จากนั้นระบบจะใช้ Google Gemini API เพื่อแนะนำเมนูอาหาร พร้อมรายละเอียดสูตรอาหารและข้อมูลโภชนาการโดยประมาณ

โปรเจกต์นี้พัฒนาด้วย Frontend, FastAPI Backend และ PostgreSQL พร้อมระบบสมาชิก การจำกัดจำนวนครั้งที่ใช้ AI ระบบ Subscription และฟีเจอร์ช่วยให้การทำอาหารสะดวกขึ้น

> **Current Version:** V1.3
> **Latest Recorded Test Result:** 45 automated tests passed
> **Payment Status:** Sandbox only — ยังไม่รองรับการชำระเงินจริงผ่าน Production Payment Gateway

---

## 1. Project Overview

### Project Objectives

* ช่วยให้ผู้ใช้คิดเมนูอาหารจากวัตถุดิบที่มีอยู่
* ใช้ AI ช่วยแนะนำสูตรอาหาร
* ระบุปริมาณวัตถุดิบเพื่อให้คำแนะนำเหมาะสมขึ้น
* แสดงรายละเอียดการทำอาหารและโภชนาการโดยประมาณ
* มีระบบ Usage เพื่อควบคุมจำนวนครั้งที่ใช้ AI
* รองรับ Subscription สำหรับเพิ่มสิทธิ์การใช้งาน
* มี Recipe History และ Recipe Book สำหรับจัดการเมนูส่วนตัว

### Main User Flow

1. สมัครสมาชิกและเข้าสู่ระบบ
2. กรอกวัตถุดิบ ปริมาณ และหน่วย
3. ส่งข้อมูลให้ Gemini AI วิเคราะห์
4. รับรายการเมนูอาหารที่แนะนำ
5. เลือกเมนูเพื่อดูรายละเอียดและโภชนาการโดยประมาณ
6. ใช้ Cook Mode เพื่อทำอาหารตามขั้นตอน
7. ระบบบันทึก Usage เมื่อการวิเคราะห์ AI สำเร็จ
8. เมื่อใช้ครบโควตา สามารถตรวจสอบ Subscription และทดลองสมัคร Plan ได้

### Business Model

CookAI เป็น **Subscription-based Digital Service** ไม่ใช่ E-commerce สำหรับขายสินค้าทั่วไป โดย Subscription ใช้กำหนดสิทธิ์การใช้งาน AI ตามโควตาของแต่ละ Plan

---

## 2. Features

### Core Features

* Register, Login และ Logout
* Authentication และ Role-based Authorization
* กรอกวัตถุดิบ ชื่อ ปริมาณ และหน่วย
* เชื่อมต่อ Google Gemini API
* แนะนำเมนูอาหารจากวัตถุดิบ
* แสดงรายละเอียดสูตรอาหารและโภชนาการโดยประมาณ
* จำกัดจำนวน AI Usage
* Free และ Pro Subscription Plans
* Payment Sandbox
* User Dashboard และ Admin Dashboard

### V1.3 Features

**Recipe History**

* บันทึกประวัติเมนูที่ทำเสร็จ
* แสดงจำนวนเมนูที่ทำสำเร็จ
* เปิดดูประวัติการทำอาหาร

**Recommended Menu**

* เริ่มทำอาหารจากเมนูแนะนำ
* ตรวจสอบวัตถุดิบก่อนเข้าสู่ขั้นตอนทำอาหาร

**Example Ingredients**

* กดปุ่มตัวอย่างเพื่อทดลองใช้งาน
* เปลี่ยนชุดตัวอย่างเพื่อทดลองกรอกวัตถุดิบหลายรูปแบบ

**Rating & Recipe Book**

* ให้คะแนนเมนู
* บันทึกเมนูลง Recipe Book ส่วนตัว
* เปิดดูเมนูที่บันทึกไว้

**Cook Mode Voice**

* อ่านขั้นตอนการทำอาหารด้วยเสียงผ่าน Browser Speech API
* รองรับการควบคุมเสียงตามที่หน้าเว็บและอุปกรณ์รองรับ

**Skill Level**

* แสดงระดับทักษะจากจำนวนเมนูที่ทำสำเร็จ
* เกณฑ์ระดับทักษะสามารถตั้งค่าได้

**Current Ideas**

* แสดงไอเดียเมนูแบบเลื่อนอัตโนมัติ
* มี Animation เล็กน้อยในส่วน UI

**Personal Nutrition Guidance**

* ตั้งค่าน้ำหนักและส่วนสูง
* เปิดหรือปิดคำแนะนำโภชนาการส่วนบุคคล
* แสดงคำเตือนเมื่อพลังงานต่อมื้อสูงกว่าคำแนะนำ
* เสนอการปรับลดปริมาณอาหารตามที่ระบบรองรับ

> ข้อมูลโภชนาการและคำแนะนำจาก AI เป็นค่าประมาณ ไม่ใช่คำแนะนำทางการแพทย์ และควรตรวจสอบความถูกต้องก่อนนำไปใช้จริง

---

## 3. Technology Stack

| Component            | Technology            |
| -------------------- | --------------------- |
| Frontend             | HTML, CSS, JavaScript |
| Backend              | Python 3.12           |
| Web Framework        | FastAPI               |
| ASGI Server          | Uvicorn               |
| Database             | PostgreSQL 16         |
| ORM                  | SQLAlchemy            |
| AI Service           | Google Gemini API     |
| API Documentation    | OpenAPI / Swagger UI  |
| Automated Testing    | pytest                |
| Containerization     | Docker                |
| Container Management | Docker Compose        |
| Cook Mode Voice      | Browser Speech API    |

### Architecture

ปัจจุบัน CookAI ใช้สถาปัตยกรรมแบบ **Modular Monolith** โดยโมดูลต่าง ๆ ทำงานภายใน FastAPI Application เดียว และใช้ PostgreSQL เป็นฐานข้อมูล

แม้ระบบจะแบ่งความรับผิดชอบเป็นส่วนต่าง ๆ เช่น Authentication, AI, Usage, Subscription และ Dashboard แต่ยังไม่ได้ Deploy เป็น Microservices อิสระหลายบริการ

---

## 4. Subscription Plans

ค่าเริ่มต้นของระบบตาม Configuration ที่ใช้ในโปรเจกต์:

| Plan | Price | Duration |       AI Usage |
| ---- | ----: | -------: | -------------: |
| Free |    ฿0 |    1 วัน |  2 ครั้งต่อวัน |
| Pro  |   ฿99 |   30 วัน | 30 ครั้งต่อวัน |

หมายเหตุ:

* ค่า Plan และ Usage Limit สามารถเปลี่ยนได้ตาม Environment Configuration
* Usage จะถูกหักเมื่อ AI Analysis สำเร็จตามกติกาของระบบ
* Payment ในเวอร์ชันนี้เป็น Sandbox เท่านั้น
* `AI_COST_PER_USAGE_THB` เป็นค่าประมาณสำหรับติดตามต้นทุน ไม่ใช่ค่าใช้จ่ายจริงที่ยืนยันจากผู้ให้บริการ

---

## 5. Requirements

สิ่งที่ต้องมีเพื่อรันโปรเจกต์:

* Docker Desktop หรือ Docker Engine
* Docker Compose
* Google Gemini API Key
* Web Browser รุ่นปัจจุบัน
* Git หากต้องการ Clone Repository

โปรเจกต์ V1.3 ผ่านการทดสอบในสภาพแวดล้อมที่ใช้ Python 3.12 และ Docker

---

## 6. Installation and Setup

### Step 1: Download the Project

Clone Repository หรือแตกไฟล์โปรเจกต์ V1.3 ลงในเครื่อง

เปิด PowerShell ที่ Root Directory ซึ่งมีไฟล์ `docker-compose.yml`

### Step 2: Configure Environment Variables

สร้างไฟล์ `.env` จาก `.env.example` แล้วใส่ค่าที่จำเป็น

ตัวอย่าง:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
SECRET_KEY=your_long_random_secret
FREE_DAILY_USAGE=2
PRO_DAILY_USAGE=30
PRO_PLAN_PRICE=99
PRO_PLAN_DAYS=30
AI_COST_PER_USAGE_THB=1.0
```

เปลี่ยน `GEMINI_API_KEY` และ `SECRET_KEY` เป็นค่าของตัวเองก่อนใช้งานจริง

**Security Rules**

* ห้าม Commit ไฟล์ `.env` ลง Git
* ห้ามเปิดเผย Gemini API Key หรือ SECRET_KEY
* ใช้ `.env.example` สำหรับเผยแพร่ตัวอย่าง Configuration
* ตรวจสอบ `.gitignore` ก่อน Push ขึ้น GitHub

### Step 3: Start Docker Desktop

เปิด Docker Desktop และรอให้ระบบพร้อมทำงาน

ตรวจสอบด้วย PowerShell:

```powershell
docker version
```

ควรเห็นทั้งส่วน Client และ Server

### Step 4: Start CookAI

จาก Root Directory ของ V1.3:

```powershell
docker compose up -d
```

หากแก้ไข Source Code, Dependencies หรือ Dockerfile และต้องการ Build ใหม่:

```powershell
docker compose up -d --build
```

### Step 5: Verify the Containers

```powershell
docker compose ps
docker compose logs api
```

ตรวจสอบว่า API และ Database ทำงานปกติ

### Step 6: Open the API

จาก Configuration ที่ใช้ทดสอบ V1.3:

* API: http://localhost:8001
* Health Check: http://localhost:8001/health
* Swagger UI: http://localhost:8001/docs
* PostgreSQL Host Port: `5433`

Port อาจแตกต่างกันได้หากแก้ไข `docker-compose.yml`

### Step 7: Stop CookAI

```powershell
docker compose down
```

คำสั่งนี้หยุดและนำ Container ของ Compose ออก โดยปกติจะไม่ลบ Named Volume ของ Database

**ห้ามใช้ `docker compose down -v` หากไม่ต้องการลบ Database Volume และข้อมูลที่อยู่ในนั้น**

---

## 7. User Manual

### 7.1 Register and Login

1. เปิดหน้าเว็บ CookAI ตามวิธีรัน Frontend ของโปรเจกต์
2. สมัครสมาชิก
3. Login ด้วยบัญชีที่สมัครไว้
4. เข้าสู่หน้า Dashboard

### 7.2 Analyze Ingredients

1. เพิ่มวัตถุดิบที่มี
2. กรอกปริมาณและหน่วย
3. ตรวจสอบรายการวัตถุดิบ
4. กดปุ่มวิเคราะห์
5. รอ AI สร้างคำแนะนำเมนู
6. เลือกเมนูที่สนใจ
7. ตรวจสอบรายละเอียดสูตรและโภชนาการโดยประมาณ

ควรกรอกปริมาณวัตถุดิบตามความเป็นจริง เพราะมีผลต่อการประเมินปริมาณอาหารและโภชนาการ

### 7.3 Cook Mode

1. เปิดรายละเอียดเมนู
2. เข้า Cook Mode
3. ทำตามขั้นตอนที่แสดงบนหน้าจอ
4. หาก Browser รองรับ สามารถใช้ปุ่มเสียงเพื่ออ่านขั้นตอน
5. ใช้ปุ่มควบคุมเสียงตามที่ระบบแสดง

หากอุปกรณ์ไม่รองรับเสียง ให้ทำตามคำแนะนำแบบข้อความแทน

### 7.4 Recipe History

1. ทำอาหารตามขั้นตอน
2. เมื่อทำเสร็จ ให้บันทึกสถานะเมนูว่าสำเร็จ
3. ตรวจสอบจำนวนเมนูที่ทำเสร็จ
4. เปิด History เพื่อดูประวัติที่ผ่านมา

ควรบันทึกว่าเสร็จหลังทำอาหารจริง เพื่อให้สถิติและ Skill Level มีความหมาย

### 7.5 Rating and Recipe Book

* ให้คะแนนเมนูตามประสบการณ์ใช้งาน
* บันทึกสูตรที่ชอบลง Recipe Book
* เปิด Recipe Book เพื่อดูเมนูที่บันทึกไว้
* ตรวจสอบว่าใช้งานด้วยบัญชีที่ถูกต้อง

### 7.6 Personal Nutrition Guidance

1. เปิด Profile หรือ Settings
2. กรอกน้ำหนักและส่วนสูง
3. เปิดหรือปิด Personal Nutrition Guidance
4. เมื่อเปิดใช้งาน ระบบอาจแสดงคำเตือนและเสนอให้ปรับลด Portion ตามเงื่อนไขที่รองรับ

การคำนวณเป็นเพียงค่าประมาณ ไม่ใช่การวินิจฉัยหรือคำแนะนำทางการแพทย์

### 7.7 Subscription

1. เปิดหน้า Subscription
2. ตรวจสอบ Plan ปัจจุบันและ Usage Limit
3. ตรวจสอบวันหมดอายุและสถานะ
4. ทดลองสมัคร Plan ตาม Flow ของระบบ

Payment ใน V1.3 เป็น Sandbox ไม่มีการตัดเงินจริงผ่าน Production Payment Gateway

---

## 8. Admin Manual

Admin Dashboard ใช้สำหรับดูภาพรวมของระบบและข้อมูลที่เกี่ยวข้องกับผู้ใช้

ข้อมูลที่สามารถตรวจสอบได้ตาม Endpoint ของระบบ ได้แก่:

* Total Users
* Free / Pro Users
* Subscription Status
* AI Usage
* Payment Records
* Estimated Cost / Revenue

### Admin Security

การเข้าถึงต้องตรวจสอบ Role จาก Backend ไม่ใช่พิจารณาจาก URL เพียงอย่างเดียว

บัญชีทั่วไปต้องไม่สามารถเรียก Admin API ได้ และ Backend ต้องส่ง HTTP Error ที่เหมาะสมเมื่อไม่มีสิทธิ์

สำหรับการจัดการ Role ให้ใช้วิธีที่กำหนดไว้ในชุด Source Code ของ V1.3 และตรวจสอบผลผ่าน `/me` หรือ Admin API ตามที่ระบบรองรับ

---

## 9. API Documentation

สามารถตรวจสอบ Endpoint, Request, Response และ Authentication ได้จาก:

**Swagger UI:** http://localhost:8001/docs

### Main API Endpoints

| Method | Endpoint                       | Purpose                             |
| ------ | ------------------------------ | ----------------------------------- |
| GET    | `/health`                      | ตรวจสอบสถานะ API                    |
| POST   | `/register`                    | สมัครสมาชิก                         |
| POST   | `/login`                       | Login                               |
| POST   | `/logout`                      | Logout                              |
| GET    | `/me`                          | ข้อมูลบัญชีปัจจุบัน                 |
| POST   | `/analyze-food`                | วิเคราะห์วัตถุดิบและแนะนำเมนู       |
| GET    | `/usage`                       | ตรวจสอบ Usage                       |
| GET    | `/subscription/plans`          | รายการ Plan                         |
| GET    | `/subscription`                | Subscription ปัจจุบัน               |
| POST   | `/subscription/subscribe`      | สมัคร Subscription                  |
| POST   | `/subscription/cancel`         | ยกเลิก Subscription ตามเงื่อนไขระบบ |
| POST   | `/payment/create`              | สร้างรายการ Payment Sandbox         |
| GET    | `/payment/status/{payment_id}` | ตรวจสอบสถานะ Payment                |
| POST   | `/payment/webhook`             | Webhook สำหรับ Flow ทดสอบ           |
| GET    | `/dashboard`                   | User Dashboard                      |
| GET    | `/admin/dashboard`             | Admin Dashboard                     |
| GET    | `/admin/users`                 | รายชื่อผู้ใช้สำหรับ Admin           |
| GET    | `/admin/usage`                 | ภาพรวม Usage                        |
| GET    | `/admin/subscriptions`         | ภาพรวม Subscription                 |
| GET    | `/admin/payments`              | ภาพรวม Payment                      |
| GET    | `/history`                     | ประวัติเมนู                         |
| POST   | `/history/complete`            | บันทึกเมนูที่ทำเสร็จ                |
| GET    | `/skill-levels`                | เกณฑ์ Skill Level                   |
| PUT    | `/history/{history_id}/rating` | ให้คะแนนเมนู                        |
| GET    | `/recipe-book`                 | ดู Recipe Book                      |
| POST   | `/recipe-book`                 | บันทึกเมนู                          |
| DELETE | `/recipe-book/{saved_id}`      | ลบเมนูที่บันทึก                     |
| GET    | `/profile/nutrition`           | ดูการตั้งค่าโภชนาการ                |
| PUT    | `/profile/nutrition`           | แก้ไขการตั้งค่าโภชนาการ             |
| POST   | `/nutrition/guidance`          | ขอคำแนะนำโภชนาการ                   |

รายการข้างต้นอ้างอิงจาก Endpoint ที่บันทึกไว้สำหรับ V1.3 ให้ตรวจสอบ `/docs` ของ Build ที่กำลังใช้งานเพื่อยืนยันรายละเอียดล่าสุด

---

## 10. Testing

ผล Automated Test ล่าสุดที่บันทึกไว้:

```text
45 passed
```

หากติดตั้ง Development Dependencies แล้ว สามารถรันทดสอบด้วย:

```powershell
python -m pytest -q
```

### Recommended Smoke Tests

1. ตรวจสอบ `docker compose ps`
2. เปิด `/health`
3. เปิด `/docs`
4. ทดสอบ Register / Login
5. ตรวจสอบ `/me`
6. ทดสอบ Usage จนเต็มโควตา และตรวจสอบ Response `429`
7. ทดสอบ Subscription และ Payment Sandbox
8. ทดสอบสิทธิ์ Admin ด้วยบัญชี Admin และบัญชี User ปกติ
9. ทดสอบ History, Rating, Recipe Book, Cook Mode Voice และ Personal Nutrition
10. รัน Automated Tests อีกครั้งหลังแก้ไข Source Code

---

## 11. Known Limitations

* Payment ยังเป็น Sandbox ไม่ใช่ระบบรับชำระเงินจริง
* Token blacklist สำหรับ Logout ใน Implementation ที่บันทึกไว้เป็น In-memory และหายไปเมื่อ API Restart
* Estimated AI Cost เป็นค่าประมาณ ไม่ใช่ข้อมูลจากใบแจ้งหนี้จริง
* Nutrition และ Personal Nutrition Guidance เป็นค่าประมาณ ไม่ใช่คำแนะนำทางการแพทย์
* เสียงพูดและคุณภาพภาษาไทยขึ้นอยู่กับ Browser และอุปกรณ์
* การแก้ไข Database Schema ในอนาคตควรใช้ Migration ที่เป็นระบบ และสำรองข้อมูลก่อนแก้ไขฐานข้อมูล
* ก่อน Deploy สู่ Production ควรทบทวน Payment Security, Token Revocation, Secret Management, Database Backup, Monitoring และ Rate Limiting

---

## 12. Git Repository Checklist

ก่อน Commit และ Push:

```powershell
git status
git check-ignore .env
```

ตรวจสอบว่า:

* `.env` ไม่ถูก Track โดย Git
* ไม่มี API Key หรือ Secret ในไฟล์ที่กำลังจะ Commit
* `.env.example` ใช้ Placeholder เท่านั้น
* `.venv`, `__pycache__` และไฟล์ชั่วคราวไม่ถูก Commit โดยไม่จำเป็น
* การเปลี่ยนแปลง V1.3 ไม่ได้เขียนทับ Baseline ของ V1.2

---

## 13. V1.3 Verification Summary

ตามผลตรวจสอบล่าสุดที่บันทึกไว้:

* Automated Tests: **45 passed**
* Manual Browser Tests ของฟีเจอร์ P0–P3: รายงานว่าผ่าน
* Docker API และ PostgreSQL: ตรวจสอบการเริ่มระบบแล้ว
* `/health`: ผ่าน
* `/docs`: ผ่าน

ควรรันทดสอบซ้ำกับ Source Code ชุดสุดท้ายก่อนส่งงานหรือ Release ทุกครั้ง
