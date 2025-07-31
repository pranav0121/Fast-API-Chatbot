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
