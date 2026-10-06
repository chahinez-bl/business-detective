from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

CURRENCIES = ["DZD", "EUR", "USD", "GBP", "MAD", "TND", "CAD", "CHF", "AED", "SAR"]
Role = Literal["owner", "admin", "member", "viewer"]
ActionStatus = Literal["todo", "in_progress", "resolved", "dismissed"]


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v): return v.strip()


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str


class TokenOut(BaseModel):
    token: str
    expires_at: datetime
    user: UserOut


class BusinessIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    industry: str = Field(default="", max_length=80)
    currency: str = Field(default="DZD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def cur(cls, v):
        v = v.upper()
        if v not in CURRENCIES:
            raise ValueError("Choose one of: " + ", ".join(CURRENCIES))
        return v

    @field_validator("name", "industry")
    @classmethod
    def strip(cls, v): return v.strip()


class BusinessPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    industry: Optional[str] = Field(default=None, max_length=80)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def cur(cls, v):
        if v is None: return v
        v = v.upper()
        if v not in CURRENCIES:
            raise ValueError("Choose one of: " + ", ".join(CURRENCIES))
        return v


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    industry: str
    currency: str
    role: Optional[str] = None


class MemberIn(BaseModel):
    email: EmailStr
    role: Role = "member"


class MappingIn(BaseModel):
    mapping: dict[str, Optional[str]]


class ActionIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    note: str = Field(default="", max_length=4000)
    insight_id: Optional[int] = None
    recommendation_id: Optional[int] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None


class ActionPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    note: Optional[str] = Field(default=None, max_length=4000)
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[ActionStatus] = None
    clear_assignee: bool = False
    clear_due_date: bool = False


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=400)


class SimulateIn(BaseModel):
    product: Optional[str] = None
    price_pct: float = 0
    cost_pct: float = 0
    volume_pct: float = 0
    elasticity: Optional[float] = Field(default=None, ge=-10, le=10)
