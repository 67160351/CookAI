import json
import httpx
import pytest

import ai_service
import schemas

BASIC = {
    "ingredients": [
        {"name": "หมูสับ", "quantity": 100, "unit": "กรัม"},
        {"name": "ไข่ไก่", "quantity": 2, "unit": "ฟอง"},
    ],
    "preferences": {"meal_type": "อาหารจานเดียว", "spicy": True, "healthy": False},
}

GEMINI_OK = {
    "recommendations": [
        {
            "name": f"เมนู {i}", "description": "d", "time_minutes": 15, "difficulty": "ง่าย", "servings": 1,
            "ingredients": [{"name": "หมูสับ", "quantity": 100, "unit": "กรัม", "from_user": True}],
            "nutrition": {"calories": 400, "protein_g": 25, "carbs_g": 10, "fat_g": 20},
            "steps": ["a", "b"], "tip": "t",
        } for i in range(1, 4)
    ]
}


def post(client, headers, body):
    return client.post("/analyze-food", json=body, headers=headers)


# ---------- auth & validation ----------
def test_requires_login(client):
    assert client.post("/analyze-food", json=BASIC).status_code == 401


@pytest.mark.parametrize("body", [
    {"ingredients": []},
    {"ingredients": [{"name": "หมูสับ", "quantity": 0, "unit": "กรัม"}]},
    {"ingredients": [{"name": "หมูสับ", "quantity": -5, "unit": "กรัม"}]},
    {"ingredients": [{"name": "  ", "quantity": 5, "unit": "กรัม"}]},
    {"ingredients": [{"name": "หมูสับ", "quantity": 5, "unit": "ตัน"}]},
    {"ingredients": [{"name": "x", "quantity": 1, "unit": "กรัม"}] * 31},
])
def test_validation_rejects_bad_input(client, auth_headers, body):
    assert post(client, auth_headers, body).status_code == 422


def test_unit_alias(client, auth_headers):
    r = post(client, auth_headers, {"ingredients": [{"name": "หมูสับ", "quantity": 100, "unit": "g"}]})
    assert r.status_code == 200


# ---------- mock mode (ไม่มี key) ----------
def test_mock_returns_three_recipes_with_structure(client, auth_headers):
    r = post(client, auth_headers, BASIC)
    assert r.status_code == 200
    d = r.json()
    assert d["source"] == "mock"
    assert len(d["recommendations"]) == 3
    assert "ไม่ใช่ข้อมูลทางการแพทย์" in d["disclaimer"]
    rec = d["recommendations"][0]
    assert rec["steps"] and rec["nutrition"]["calories"] > 0
    user_ings = {i["name"]: (i["quantity"], i["unit"]) for i in rec["ingredients"] if i["from_user"]}
    assert user_ings == {"หมูสับ": (100, "กรัม"), "ไข่ไก่": (2, "ฟอง")}


def test_mock_nutrition_follows_quantity(client, auth_headers):
    small = post(client, auth_headers, {"ingredients": [{"name": "หมูสับ", "quantity": 100, "unit": "กรัม"}]}).json()
    big = post(client, auth_headers, {"ingredients": [{"name": "หมูสับ", "quantity": 1, "unit": "กิโลกรัม"}]}).json()
    assert big["recommendations"][0]["nutrition"]["calories"] > small["recommendations"][0]["nutrition"]["calories"] * 5


# ---------- prompt (Quantity Logic) ----------
def test_prompt_uses_selected_quantity_not_total():
    req = schemas.AnalyzeFoodRequest.model_validate(BASIC)
    p = ai_service.build_prompt(req)
    assert "หมูสับ 100 กรัม" in p and "ไข่ไก่ 2 ฟอง" in p
    assert "ปริมาณที่ตั้งใจจะใช้" in p and "ห้ามใช้เกิน" in p
    assert '"spicy": true' in p


def test_prompt_converts_kg():
    req = schemas.AnalyzeFoodRequest.model_validate({"ingredients": [{"name": "หมูสับ", "quantity": 1, "unit": "กิโลกรัม"}]})
    assert "1000 กรัม" in ai_service.build_prompt(req)


# ---------- Gemini path (จำลอง HTTP) ----------
def _patch_http(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def _gemini_body(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_gemini_success_and_key_in_header_only(client, auth_headers, monkeypatch):
    seen = {}

    def handler(request):
        seen["url"], seen["key"] = str(request.url), request.headers.get("x-goog-api-key")
        seen["prompt"] = json.loads(request.content)["contents"][0]["parts"][0]["text"]
        return httpx.Response(200, json=_gemini_body("```json\n" + json.dumps(GEMINI_OK, ensure_ascii=False) + "\n```"))

    _patch_http(monkeypatch, handler)
    r = post(client, auth_headers, BASIC)
    assert r.status_code == 200 and r.json()["source"] == "gemini"
    assert seen["key"] == "test-key" and "test-key" not in seen["url"]
    assert "หมูสับ 100 กรัม" in seen["prompt"]


@pytest.mark.parametrize("resp,code", [
    (httpx.Response(429, text="quota"), 503),
    (httpx.Response(403, text="bad key"), 502),
    (httpx.Response(500, text="boom"), 502),
    (httpx.Response(200, json=_gemini_body("ไม่ใช่ json")), 502),
    (httpx.Response(200, json=_gemini_body(json.dumps({"recommendations": [{"name": "x"}]}))), 502),
    (httpx.Response(200, json=_gemini_body(json.dumps({"recommendations": []}))), 502),
    (httpx.Response(200, json={"candidates": []}), 502),
])
def test_gemini_failures_map_to_clean_errors(client, auth_headers, monkeypatch, resp, code):
    _patch_http(monkeypatch, lambda request: resp)
    r = post(client, auth_headers, BASIC)
    assert r.status_code == code
    assert "test-key" not in r.text and "bad key" not in r.text


def test_gemini_timeout(client, auth_headers, monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("slow")
    _patch_http(monkeypatch, handler)
    assert post(client, auth_headers, BASIC).status_code == 504
