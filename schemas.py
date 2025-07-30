from pydantic import BaseModel
from typing import Optional

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
