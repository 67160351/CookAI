"""V1.3 Personal Nutrition guidance — คำนวณในเครื่องล้วน ๆ ไม่เรียก AI และไม่แตะ Core

หลักการ:
- ข้อมูลทั้งหมดเป็นค่าประมาณ ไม่ใช่การวินิจฉัยทางการแพทย์
- "ปรับสารอาหาร" ทำได้เฉพาะ *ลด* สัดส่วน (factor <= 1) เพื่อไม่ให้เกินปริมาณวัตถุดิบที่ผู้ใช้ตั้งใจใช้
  (กติกา Core: ปริมาณที่ใส่ = ปริมาณที่จะใช้ ห้ามเกิน)
"""
import copy

DISCLAIMER = ("ค่าทั้งหมดเป็นการประมาณเพื่อเป็นแนวทางทั่วไป ไม่ใช่คำแนะนำทางการแพทย์หรือการวินิจฉัย "
              "หากมีโรคประจำตัวหรือต้องการแผนโภชนาการ ควรปรึกษาแพทย์/นักกำหนดอาหาร")

KCAL_PER_KG_PER_DAY = 30      # ค่าประมาณหยาบ ๆ ของพลังงานต่อวัน (ไม่ใช้อายุ/เพศ เพื่อไม่เก็บข้อมูลเกินจำเป็น)
MEALS_PER_DAY = 3
TOLERANCE = 0.25              # เตือนเมื่อพลังงานต่อที่เกินเป้าหมายมากกว่า 25%
MIN_FACTOR = 0.5


def bmi_of(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    m = height_cm / 100.0
    return round(weight_kg / (m * m), 1)


def bmi_category(bmi):
    """เกณฑ์ BMI ทั่วไป (WHO/เอเชียแปซิฟิก แบบย่อ) — เพื่อการให้ข้อมูลเท่านั้น"""
    if bmi is None:
        return None
    if bmi < 18.5:
        return "ต่ำกว่าเกณฑ์ทั่วไป"
    if bmi < 23:
        return "อยู่ในเกณฑ์ทั่วไป"
    if bmi < 25:
        return "เริ่มสูงกว่าเกณฑ์"
    return "สูงกว่าเกณฑ์ทั่วไป"


def meal_target_kcal(weight_kg, bmi):
    day = weight_kg * KCAL_PER_KG_PER_DAY
    if bmi is not None and bmi >= 25:
        day *= 0.85
    elif bmi is not None and bmi < 18.5:
        day *= 1.10
    return round(day / MEALS_PER_DAY)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def evaluate(recipe: dict, weight_kg, height_cm) -> dict:
    """ประเมินเมนู 1 ที่เทียบกับเป้าหมายต่อมื้อ + เสนอ factor (<=1) และสูตรที่ปรับแล้ว"""
    bmi = bmi_of(weight_kg, height_cm)
    cal = _num((recipe.get("nutrition") or {}).get("calories"))
    out = {"bmi": bmi, "bmi_category": bmi_category(bmi), "disclaimer": DISCLAIMER,
           "warning": None, "level": "info", "target_kcal": None, "factor": 1.0, "adjusted": None}
    if not weight_kg or not height_cm or cal is None or cal <= 0:
        out["warning"] = "ใส่น้ำหนักและส่วนสูงในโปรไฟล์เพื่อให้ประเมินได้" if not (weight_kg and height_cm) else None
        return out

    target = meal_target_kcal(weight_kg, bmi)
    out["target_kcal"] = target
    if cal > target * (1 + TOLERANCE):
        factor = max(MIN_FACTOR, round(target / cal, 2))
        out.update(level="warn", factor=factor,
                   warning=f"เมนูนี้ประมาณ {round(cal)} kcal/ที่ สูงกว่าแนวทางต่อมื้อของคุณ (~{target} kcal) "
                           f"ลองลดสัดส่วนเหลือประมาณ {int(factor*100)}% ได้")
        out["adjusted"] = scale_recipe(recipe, factor)
    elif cal < target * (1 - TOLERANCE):
        out.update(level="low",
                   warning=f"เมนูนี้ประมาณ {round(cal)} kcal/ที่ ต่ำกว่าแนวทางต่อมื้อ (~{target} kcal) "
                           "อาจเพิ่มเมนูเคียง/ผลไม้ได้ (ระบบไม่เพิ่มปริมาณวัตถุดิบให้เกินที่คุณใส่)")
    else:
        out.update(level="ok", warning="พลังงานของเมนูนี้อยู่ในแนวทางต่อมื้อโดยประมาณ")
    return out


def scale_recipe(recipe: dict, factor: float) -> dict:
    """ลดสัดส่วนวัตถุดิบ+โภชนาการตาม factor (จำกัด <=1 เสมอ)"""
    factor = min(1.0, max(MIN_FACTOR, factor))
    r = copy.deepcopy(recipe)
    for ing in r.get("ingredients") or []:
        q = _num(ing.get("quantity"))
        if q is not None:
            ing["quantity"] = round(q * factor, 1)
    n = r.get("nutrition") or {}
    for k in ("calories", "protein_g", "carbs_g", "fat_g"):
        v = _num(n.get(k))
        if v is not None:
            n[k] = round(v * factor, 1)
    r["nutrition"] = n
    r["portion_factor"] = factor
    return r
