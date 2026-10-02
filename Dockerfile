FROM python:3.12-slim

WORKDIR /app

# copy requirements ก่อนเพื่อให้ Docker cache layer นี้ไว้ (ถ้าโค้ดเปลี่ยนแต่ requirements ไม่เปลี่ยน
# จะไม่ต้อง pip install ใหม่ทุกครั้ง ทำให้ build เร็วขึ้นมาก)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy โค้ดที่เหลือทั้งหมดเข้า image
COPY . .

EXPOSE 8000

# ใช้ shell form เพื่อให้อ่านค่า $PORT ที่ Render inject มาได้ (ถ้าไม่มีจะ fallback เป็น 8000 ตอนรันในเครื่อง)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
