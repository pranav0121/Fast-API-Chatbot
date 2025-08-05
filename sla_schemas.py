from pydantic import BaseModel
from typing import Optional


class SLAPolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    response_time_minutes: int
    resolution_time_minutes: int


class SLAPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    response_time_minutes: Optional[int] = None
    resolution_time_minutes: Optional[int] = None


class SLAPolicyOut(BaseModel):
    sla_id: int
    name: str
    description: Optional[str] = None
    response_time_minutes: int
    resolution_time_minutes: int

    class Config:
        orm_mode = True


class SLAStatusOut(BaseModel):
    ticket_id: int
    sla_policy: SLAPolicyOut
    status: str
    time_left_minutes: int


class SLAViolationOut(BaseModel):
    ticket_id: int
    reason: str


class SLAReportDetail(BaseModel):
    ticketid: int
    subject: str
    status: str
    priority: str
    createdat: str
    resolvedat: str
    time_to_resolve_minutes: int
    sla_minutes: int
    within_sla: bool


class SLAReportOut(BaseModel):
    total_tickets: int
    tickets_within_sla: int
    tickets_breached: int
    compliance_percentage: float
    details: list[SLAReportDetail]


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

    class Config:
        extra = "allow"


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
