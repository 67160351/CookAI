import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[EmailStr] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    username: str


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None  # โชว์ตรงนี้เพื่อ demo เท่านั้น ระบบจริงต้องส่งทางอีเมลแทน


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=6, max_length=128)


# ---------- User ----------
class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    is_active: bool
    role: str = "user"
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class PaginatedUsers(BaseModel):
    total: int
    page: int
    limit: int
    items: List[UserOut]


class MessageResponse(BaseModel):
    message: str


class UsernameAvailability(BaseModel):
    username: str
    available: bool


# ---------- AI Food Analysis (v1.1) ----------
from typing import Literal, Union
from pydantic import field_validator

# หน่วยที่รองรับ (ตรงกับ dropdown ในหน้าเว็บ)
Unit = Literal["กรัม", "กิโลกรัม", "ฟอง", "ลูก", "ช้อนโต๊ะ", "ช้อนชา", "ต้น", "กลีบ", "มิลลิลิตร", "ถ้วย"]

_UNIT_ALIASES = {
    "g": "กรัม", "gram": "กรัม", "grams": "กรัม", "kg": "กิโลกรัม",
    "ml": "มิลลิลิตร", "tbsp": "ช้อนโต๊ะ", "tsp": "ช้อนชา", "cup": "ถ้วย",
}


class IngredientIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    quantity: float = Field(gt=0, le=100000)
    unit: Unit

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("unit", mode="before")
    @classmethod
    def _normalize_unit(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return _UNIT_ALIASES.get(v.lower(), v)
        return v


class PreferencesIn(BaseModel):
    meal_type: Optional[str] = Field(default=None, max_length=50)
    spicy: bool = False
    healthy: bool = False


class AnalyzeFoodRequest(BaseModel):
    ingredients: List[IngredientIn] = Field(min_length=1, max_length=30)
    preferences: PreferencesIn = PreferencesIn()


class RecipeIngredient(BaseModel):
    name: str
    quantity: Union[float, str]
    unit: str = ""
    from_user: bool = False  # True = วัตถุดิบที่ผู้ใช้ระบุ, False = เครื่องปรุงพื้นฐานที่ AI เติมให้


class Nutrition(BaseModel):
    """ค่าประมาณต่อ 1 ที่ — ไม่ใช่ค่าทางการแพทย์"""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class Recipe(BaseModel):
    name: str
    description: str = ""
    time_minutes: int = 0
    difficulty: str = ""
    servings: int = 1
    ingredients: List[RecipeIngredient]
    nutrition: Nutrition
    steps: List[str] = Field(min_length=1)
    tip: Optional[str] = None


class AnalyzeFoodResponse(BaseModel):
    recommendations: List[Recipe]
    disclaimer: str
    source: Literal["gemini", "mock"]

# ---------- V1.2 Usage / Subscription / Payment / Dashboard ----------
class PlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int
    usage_limit: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class UsageOut(BaseModel):
    plan_name: str
    subscription_status: str
    usage_date: datetime.date
    used: int
    limit: int
    remaining: int

class SubscriptionOut(BaseModel):
    plan: PlanOut
    status: str
    start_date: datetime.datetime
    expire_date: datetime.datetime

class SubscribeRequest(BaseModel):
    plan_id: int

class PaymentCreateRequest(BaseModel):
    plan_id: int

class PaymentOut(BaseModel):
    id: int
    transaction_id: str
    plan_id: int
    amount: float
    status: str
    provider: str
    provider_reference: Optional[str] = None
    created_at: datetime.datetime
    paid_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)

class DashboardOut(BaseModel):
    username: str
    plan: PlanOut
    subscription: SubscriptionOut
    usage: UsageOut
    recent_payments: List[PaymentOut]

class AdminUserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    role: str
    is_active: bool
    plan_name: str
    subscription_status: str
    usage_used: int
    usage_limit: int

class AdminDashboardOut(BaseModel):
    total_users: int
    free_users: int
    paid_users: int
    active_subscriptions: int
    expired_subscriptions: int
    ai_usage_today: int
    ai_usage_this_month: int
    estimated_ai_cost: float
    subscription_revenue: float
    cost_note: str
    revenue_note: str
