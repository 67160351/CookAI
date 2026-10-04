import os
import sys
import tempfile

# ใช้ SQLite ชั่วคราวเสมอ ไม่แตะ Postgres/ข้อมูลจริง และบังคับโหมด mock เว้นแต่เทสต์จะตั้ง key เอง
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ.pop("GEMINI_API_KEY", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture(scope="session")
def client():
    from main import app
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """ผู้ใช้ใหม่ทุกเทสต์ = โควตา Free (2/วัน) ใหม่ของตัวเอง

    เทสต์ AI regression เรียก /analyze-food หลายครั้ง ถ้าใช้ user ร่วมกันจะชนลิมิต Free
    แล้วได้ 429 ก่อนถึงตรรกะที่ต้องการทดสอบ จึงแยก user ต่อเทสต์
    (ไม่ปิด usage check และไม่แก้กติกา Free=2/day ใน production code)
    """
    import uuid
    name = "t" + uuid.uuid4().hex[:10]
    client.post("/register", json={"username": name, "password": "secret123"})
    token = client.post("/login", json={"username": name, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
