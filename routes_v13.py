"""V1.3: ประวัติการทำอาหาร, สมุดสูตรส่วนตัว, ระดับฝีมือ, Personal Nutrition
ทุก endpoint ผูกกับ current_user (แยกข้อมูลต่อ user) และ *ไม่เรียก AI / ไม่หัก Usage*
"""
import datetime
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
import models
import nutrition_guidance
from database import get_db

router = APIRouter(tags=["V1.3"])

MAX_RECIPE_JSON = 20000

DEFAULT_LEVELS = "0:พ่อครัวฝึกหัด ⭐,5:พ่อครัวมือใหม่ ⭐⭐,15:พ่อครัวฝีมือดี ⭐⭐⭐,30:เชฟประจำบ้าน ⭐⭐⭐⭐,60:เชฟมือโปร ⭐⭐⭐⭐⭐"


def skill_levels() -> List[dict]:
    """เกณฑ์ปรับได้ผ่าน env SKILL_LEVELS เช่น '0:ฝึกหัด,5:มือใหม่'"""
    raw = os.getenv("SKILL_LEVELS", DEFAULT_LEVELS)
    levels = []
    try:
        for part in raw.split(","):
            n, name = part.split(":", 1)
            levels.append({"min_completed": int(n), "name": name.strip()})
        levels.sort(key=lambda x: x["min_completed"])
        if not levels or levels[0]["min_completed"] != 0:
            raise ValueError
    except ValueError:
        levels = [{"min_completed": int(p.split(":")[0]), "name": p.split(":", 1)[1]} for p in DEFAULT_LEVELS.split(",")]
    return levels


def level_for(count: int) -> dict:
    levels = skill_levels()
    cur = levels[0]
    nxt = None
    for i, lv in enumerate(levels):
        if count >= lv["min_completed"]:
            cur = lv
            nxt = levels[i + 1] if i + 1 < len(levels) else None
    return {"current": cur, "next": nxt, "remaining_to_next": (nxt["min_completed"] - count) if nxt else 0}


# ---------- schemas ----------
class RecipeSnapshot(BaseModel):
    model_config = {"extra": "allow"}
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = None
    time_minutes: Optional[float] = None
    difficulty: Optional[str] = None
    servings: Optional[float] = None
    ingredients: List[Dict[str, Any]] = Field(default_factory=list, max_length=60)
    steps: List[str] = Field(default_factory=list, max_length=60)
    nutrition: Dict[str, Any] = Field(default_factory=dict)


class CompleteRequest(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    recipe: RecipeSnapshot


class RatingRequest(BaseModel):
    rating: int = Field(ge=1, le=5)


class SaveRequest(BaseModel):
    recipe: RecipeSnapshot
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class NutritionProfileRequest(BaseModel):
    weight_kg: Optional[float] = Field(default=None, ge=20, le=300)
    height_cm: Optional[float] = Field(default=None, ge=80, le=250)
    guidance_enabled: bool = False


class GuidanceRequest(BaseModel):
    recipe: RecipeSnapshot


def _dump(recipe: RecipeSnapshot) -> str:
    s = json.dumps(recipe.model_dump(), ensure_ascii=False)
    if len(s) > MAX_RECIPE_JSON:
        raise HTTPException(status_code=413, detail="ข้อมูลสูตรใหญ่เกินไป")
    return s


def recipe_key(recipe: RecipeSnapshot) -> str:
    base = recipe.name.strip().lower() + "|" + ",".join(
        f"{str(i.get('name', '')).strip().lower()}:{i.get('quantity', '')}" for i in recipe.ingredients)
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _hist_out(h: models.CookHistory) -> dict:
    return {"id": h.id, "recipe_name": h.recipe_name, "rating": h.rating,
            "completed_at": h.completed_at.isoformat() + "Z", "recipe": json.loads(h.recipe_json)}


def _saved_out(s: models.SavedRecipe) -> dict:
    return {"id": s.id, "recipe_key": s.recipe_key, "recipe_name": s.recipe_name, "rating": s.rating,
            "saved_at": s.created_at.isoformat() + "Z", "recipe": json.loads(s.recipe_json)}


def _count(db: Session, uid: int) -> int:
    return db.query(models.CookHistory).filter_by(user_id=uid).count()


# ---------- history / stats ----------
@router.post("/history/complete")
def complete_recipe(payload: CompleteRequest, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """บันทึกว่าทำเมนูเสร็จ — idempotent ด้วย event_id (ส่งซ้ำไม่นับซ้ำ)"""
    row = db.query(models.CookHistory).filter_by(user_id=user.id, event_id=payload.event_id).first()
    created = False
    if not row:
        row = models.CookHistory(user_id=user.id, event_id=payload.event_id,
                                 recipe_name=payload.recipe.name.strip()[:160], recipe_json=_dump(payload.recipe))
        db.add(row)
        try:
            db.commit()
            created = True
        except IntegrityError:
            db.rollback()
            row = db.query(models.CookHistory).filter_by(user_id=user.id, event_id=payload.event_id).first()
        db.refresh(row)
    count = _count(db, user.id)
    return {"history_id": row.id, "created": created, "completed_count": count, "skill": level_for(count)}


@router.get("/history")
def list_history(limit: int = 50, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 200)
    rows = (db.query(models.CookHistory).filter_by(user_id=user.id)
            .order_by(models.CookHistory.completed_at.desc(), models.CookHistory.id.desc()).limit(limit).all())
    return {"total": _count(db, user.id), "items": [_hist_out(h) for h in rows]}


@router.get("/stats")
def my_stats(user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    count = _count(db, user.id)
    return {"completed_count": count, "skill": level_for(count)}


@router.get("/skill-levels")
def get_skill_levels(user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    count = _count(db, user.id)
    return {"levels": skill_levels(), "completed_count": count, "skill": level_for(count),
            "note": "ระดับนับจากจำนวนเมนูที่ทำเสร็จ ไม่เกี่ยวกับการใช้ AI"}


@router.put("/history/{history_id}/rating")
def rate_history(history_id: int, payload: RatingRequest, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    h = db.query(models.CookHistory).filter_by(id=history_id, user_id=user.id).first()
    if not h:
        raise HTTPException(status_code=404, detail="ไม่พบรายการนี้")
    h.rating = payload.rating
    # ถ้าสูตรนี้อยู่ในสมุดสูตรของ user แล้ว ให้คะแนนตรงกัน
    key = recipe_key(RecipeSnapshot(**json.loads(h.recipe_json)))
    saved = db.query(models.SavedRecipe).filter_by(user_id=user.id, recipe_key=key).first()
    if saved:
        saved.rating = payload.rating
    db.commit()
    return {"history_id": h.id, "rating": h.rating, "saved_updated": bool(saved)}


# ---------- recipe book ----------
@router.post("/recipe-book")
def save_recipe(payload: SaveRequest, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    key = recipe_key(payload.recipe)
    row = db.query(models.SavedRecipe).filter_by(user_id=user.id, recipe_key=key).first()
    if row:
        if payload.rating is not None:
            row.rating = payload.rating
    else:
        row = models.SavedRecipe(user_id=user.id, recipe_key=key, recipe_name=payload.recipe.name.strip()[:160],
                                 recipe_json=_dump(payload.recipe), rating=payload.rating)
        db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.query(models.SavedRecipe).filter_by(user_id=user.id, recipe_key=key).first()
    db.refresh(row)
    return _saved_out(row)


@router.get("/recipe-book")
def list_recipe_book(user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    rows = db.query(models.SavedRecipe).filter_by(user_id=user.id).order_by(models.SavedRecipe.created_at.desc(), models.SavedRecipe.id.desc()).all()
    return {"total": len(rows), "items": [_saved_out(r) for r in rows]}


@router.delete("/recipe-book/{saved_id}")
def unsave_recipe(saved_id: int, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    row = db.query(models.SavedRecipe).filter_by(id=saved_id, user_id=user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="ไม่พบสูตรนี้ในสมุดของคุณ")
    db.delete(row)
    db.commit()
    return {"message": "ลบออกจากสมุดสูตรแล้ว"}


# ---------- personal nutrition ----------
def _profile(db: Session, uid: int) -> Optional[models.UserNutritionProfile]:
    return db.query(models.UserNutritionProfile).filter_by(user_id=uid).first()


def _profile_out(p: Optional[models.UserNutritionProfile]) -> dict:
    w = p.weight_kg if p else None
    h = p.height_cm if p else None
    bmi = nutrition_guidance.bmi_of(w, h)
    return {"weight_kg": w, "height_cm": h, "guidance_enabled": bool(p.guidance_enabled) if p else False,
            "bmi": bmi, "bmi_category": nutrition_guidance.bmi_category(bmi),
            "disclaimer": nutrition_guidance.DISCLAIMER}


@router.get("/profile/nutrition")
def get_nutrition_profile(user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    return _profile_out(_profile(db, user.id))


@router.put("/profile/nutrition")
def put_nutrition_profile(payload: NutritionProfileRequest, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if payload.guidance_enabled and not (payload.weight_kg and payload.height_cm):
        raise HTTPException(status_code=422, detail="ต้องใส่น้ำหนักและส่วนสูงก่อนเปิด Personal Nutrition")
    p = _profile(db, user.id)
    if not p:
        p = models.UserNutritionProfile(user_id=user.id)
        db.add(p)
    p.weight_kg, p.height_cm = payload.weight_kg, payload.height_cm
    p.guidance_enabled = payload.guidance_enabled
    p.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(p)
    return _profile_out(p)


@router.post("/nutrition/guidance")
def nutrition_guidance_for_recipe(payload: GuidanceRequest, user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """toggle ปิด = ไม่ทำอะไร (ไม่เตือน ไม่ปรับสูตร) — ไม่เรียก AI"""
    p = _profile(db, user.id)
    if not p or not p.guidance_enabled:
        return {"enabled": False, "disclaimer": nutrition_guidance.DISCLAIMER}
    res = nutrition_guidance.evaluate(payload.recipe.model_dump(), p.weight_kg, p.height_cm)
    res["enabled"] = True
    return res
