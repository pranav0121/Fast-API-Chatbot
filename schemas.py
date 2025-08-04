from pydantic import BaseModel, EmailStr

from typing import Optional

# For user registration


class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    preferredlanguage: str
    organizationname: Optional[str] = None
    position: Optional[str] = None
    prioritylevel: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None

# For user login


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

# For JWT response


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TicketCreateRequest(BaseModel):
    name: str
    category_id: int
    subject: Optional[str]
    message: str
    priority: Optional[str] = "medium"
    organization: Optional[str]


class TicketMessageRequest(BaseModel):
    user_id: Optional[int]
    content: str
    is_admin: Optional[bool] = False


class FeedbackRequest(BaseModel):
    ticket_id: int
    rating: int
    feedback: Optional[str] = None

# SLA Schemas (merged from sla_schemas.py)


class SLAPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    response_time_minutes: int
    resolution_time_minutes: int


class SLAPolicyCreate(SLAPolicyBase):
    pass


class SLAPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    response_time_minutes: Optional[int] = None
    resolution_time_minutes: Optional[int] = None


class SLAPolicyOut(SLAPolicyBase):
    sla_id: int

    class Config:
        orm_mode = True


class SLAStatusOut(BaseModel):
    ticket_id: int
    sla_policy: Optional[SLAPolicyOut]
    status: str  # e.g., on track, breached
    time_left_minutes: Optional[int]


class SLAViolationOut(BaseModel):
    ticket_id: int
    user_id: int
    breached_at: str
    sla_policy: Optional[SLAPolicyOut]


class SLAReportOut(BaseModel):
    total_tickets: int
    tickets_within_sla: int
    tickets_breached: int
    compliance_percentage: float
