from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from models import Base

# SLA Policy Model


class SLAPolicy(Base):
    __tablename__ = "sla_policies"
    sla_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    response_time_minutes = Column(Integer, nullable=False)
    resolution_time_minutes = Column(Integer, nullable=False)

# SLA Logs Table


class SLALog(Base):
    __tablename__ = "sla_logs"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.ticketid"), nullable=False)
    sla_policy_id = Column(Integer, ForeignKey(
        "sla_policies.sla_id"), nullable=False)
    # e.g., 'assigned', 'breached', 'resolved'
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    details = Column(Text)
