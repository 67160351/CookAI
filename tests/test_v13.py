import uuid
import pytest

import ai_service

RECIPE = {
    "name": "ไข่เจียวหมูสับ", "description": "x", "time_minutes": 10, "difficulty": "ง่าย", "servings": 1,
    "ingredients": [{"name": "ไข่ไก่", "quantity": 2, "unit": "ฟอง", "from_user": True},
                    {"name": "หมูสับ", "quantity": 100, "unit": "กรัม", "from_user": True}],
    "steps": ["ตีไข่", "ทอด"],
    "nutrition": {"calories": 900, "protein_g": 40, "carbs_g": 10, "fat_g": 70},
}


def _new_user(client):
    name = "v13" + uuid.uuid4().hex[:8]
    client.post("/register", json={"username": name, "password": "secret123"})
    t = client.post("/login", json={"username": name, "password": "secret123"}).json()["access_token"]
    return {"Authorization": "Bearer " + t}


def _complete(client, h, event_id=None, recipe=RECIPE):
    return client.post("/history/complete", json={"event_id": event_id or uuid.uuid4().hex, "recipe": recipe}, headers=h)


def test_v13_requires_login(client):
    for method, path in [("get", "/history"), ("get", "/stats"), ("get", "/recipe-book"),
                         ("get", "/skill-levels"), ("get", "/profile/nutrition")]:
        assert getattr(client, method)(path).status_code == 401


def test_completion_counts_and_is_idempotent(client):
    h = _new_user(client)
    assert client.get("/stats", headers=h).json()["completed_count"] == 0
    eid = uuid.uuid4().hex
    a = _complete(client, h, eid).json()
    b = _complete(client, h, eid).json()          # ส่งซ้ำ (กดสองครั้ง/รีเทรี) ต้องไม่นับซ้ำ
    assert a["created"] is True and b["created"] is False and a["history_id"] == b["history_id"]
    assert b["completed_count"] == 1
    _complete(client, h)
    hist = client.get("/history", headers=h).json()
    assert hist["total"] == 2 and hist["items"][0]["recipe_name"] == RECIPE["name"]
    assert "completed_at" in hist["items"][0]


def test_history_and_book_are_isolated_per_user(client):
    a, b = _new_user(client), _new_user(client)
    _complete(client, a)
    saved = client.post("/recipe-book", json={"recipe": RECIPE}, headers=a).json()
    assert client.get("/history", headers=b).json()["total"] == 0
    assert client.get("/recipe-book", headers=b).json()["total"] == 0
    assert client.delete(f"/recipe-book/{saved['id']}", headers=b).status_code == 404
    hid = client.get("/history", headers=a).json()["items"][0]["id"]
    assert client.put(f"/history/{hid}/rating", json={"rating": 5}, headers=b).status_code == 404


def test_rating_validation_and_syncs_with_book(client):
    h = _new_user(client)
    hid = _complete(client, h).json()["history_id"]
    for bad in (0, 6, "x"):
        assert client.put(f"/history/{hid}/rating", json={"rating": bad}, headers=h).status_code == 422
    client.post("/recipe-book", json={"recipe": RECIPE}, headers=h)
    r = client.put(f"/history/{hid}/rating", json={"rating": 4}, headers=h).json()
    assert r["rating"] == 4 and r["saved_updated"] is True
    assert client.get("/recipe-book", headers=h).json()["items"][0]["rating"] == 4


def test_recipe_book_save_unsave_no_duplicates(client):
    h = _new_user(client)
    s1 = client.post("/recipe-book", json={"recipe": RECIPE}, headers=h).json()
    s2 = client.post("/recipe-book", json={"recipe": RECIPE, "rating": 3}, headers=h).json()
    assert s1["id"] == s2["id"] and s2["rating"] == 3
    assert client.get("/recipe-book", headers=h).json()["total"] == 1
    assert client.delete(f"/recipe-book/{s1['id']}", headers=h).status_code == 200
    assert client.get("/recipe-book", headers=h).json()["total"] == 0


def test_recipe_payload_validation(client):
    h = _new_user(client)
    assert client.post("/recipe-book", json={"recipe": {"name": ""}}, headers=h).status_code == 422
    big = dict(RECIPE, steps=["x" * 1000] * 40)
    assert client.post("/recipe-book", json={"recipe": big}, headers=h).status_code == 413


def test_skill_levels_follow_completed_count_not_ai_usage(client, monkeypatch):
    h = _new_user(client)
    lv = client.get("/skill-levels", headers=h).json()
    assert lv["skill"]["current"]["min_completed"] == 0 and len(lv["levels"]) >= 3
    need = lv["skill"]["next"]["min_completed"]
    for _ in range(need):
        _complete(client, h)
    s = client.get("/stats", headers=h).json()
    assert s["skill"]["current"]["min_completed"] == need
    assert client.get("/usage", headers=h).json()["used"] == 0     # ไม่ผูกกับ AI usage


def test_skill_levels_configurable_and_bad_config_falls_back(client, monkeypatch):
    h = _new_user(client)
    monkeypatch.setenv("SKILL_LEVELS", "0:A,1:B")
    _complete(client, h)
    assert client.get("/stats", headers=h).json()["skill"]["current"]["name"] == "B"
    monkeypatch.setenv("SKILL_LEVELS", "garbage")
    assert client.get("/stats", headers=h).status_code == 200


def test_v13_endpoints_never_call_ai_or_charge_usage(client, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("V1.3 must not call AI")
    monkeypatch.setattr(ai_service, "analyze", boom)
    h = _new_user(client)
    _complete(client, h)
    client.post("/recipe-book", json={"recipe": RECIPE}, headers=h)
    client.put("/profile/nutrition", json={"weight_kg": 70, "height_cm": 170, "guidance_enabled": True}, headers=h)
    client.post("/nutrition/guidance", json={"recipe": RECIPE}, headers=h)
    assert client.get("/usage", headers=h).json()["used"] == 0


def test_nutrition_profile_validation(client):
    h = _new_user(client)
    assert client.get("/profile/nutrition", headers=h).json()["guidance_enabled"] is False   # default OFF
    for body in ({"weight_kg": 5}, {"height_cm": 500}, {"weight_kg": 70, "height_cm": 10}):
        assert client.put("/profile/nutrition", json=body, headers=h).status_code == 422
    # เปิดโดยไม่มีข้อมูล = ปฏิเสธ
    assert client.put("/profile/nutrition", json={"guidance_enabled": True}, headers=h).status_code == 422
    ok = client.put("/profile/nutrition", json={"weight_kg": 70, "height_cm": 175, "guidance_enabled": True}, headers=h).json()
    assert ok["bmi"] == 22.9 and ok["guidance_enabled"] is True and "ไม่ใช่คำแนะนำทางการแพทย์" in ok["disclaimer"]


def test_guidance_off_changes_nothing(client):
    h = _new_user(client)
    r = client.post("/nutrition/guidance", json={"recipe": RECIPE}, headers=h).json()
    assert r["enabled"] is False and "adjusted" not in r and "warning" not in r
    client.put("/profile/nutrition", json={"weight_kg": 70, "height_cm": 175, "guidance_enabled": True}, headers=h)
    client.put("/profile/nutrition", json={"weight_kg": 70, "height_cm": 175, "guidance_enabled": False}, headers=h)
    assert client.post("/nutrition/guidance", json={"recipe": RECIPE}, headers=h).json()["enabled"] is False


def test_guidance_on_warns_and_only_reduces_quantities(client):
    h = _new_user(client)
    client.put("/profile/nutrition", json={"weight_kg": 60, "height_cm": 170, "guidance_enabled": True}, headers=h)
    r = client.post("/nutrition/guidance", json={"recipe": RECIPE}, headers=h).json()
    assert r["enabled"] and r["level"] == "warn" and r["warning"] and 0.5 <= r["factor"] < 1
    adj = r["adjusted"]
    for old, new in zip(RECIPE["ingredients"], adj["ingredients"]):
        assert new["quantity"] <= old["quantity"]          # ห้ามเกินปริมาณที่ผู้ใช้ใส่
    assert adj["nutrition"]["calories"] < RECIPE["nutrition"]["calories"]
    assert RECIPE["ingredients"][0]["quantity"] == 2       # ไม่แก้ต้นฉบับ


def test_guidance_low_calorie_never_scales_up(client):
    h = _new_user(client)
    client.put("/profile/nutrition", json={"weight_kg": 90, "height_cm": 170, "guidance_enabled": True}, headers=h)
    light = dict(RECIPE, nutrition={"calories": 150, "protein_g": 5, "carbs_g": 20, "fat_g": 3})
    r = client.post("/nutrition/guidance", json={"recipe": light}, headers=h).json()
    assert r["level"] == "low" and r["factor"] == 1.0 and r["adjusted"] is None


def test_pure_guidance_functions():
    import nutrition_guidance as ng
    assert ng.bmi_of(70, 175) == 22.9 and ng.bmi_of(None, 170) is None
    assert ng.bmi_category(17) != ng.bmi_category(27)
    assert ng.scale_recipe(RECIPE, 5)["portion_factor"] == 1.0     # factor ถูก clamp ไม่เกิน 1
