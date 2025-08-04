from sqlalchemy import Column, Integer, String, Interval, Text
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class SLAPolicy(Base):
    __tablename__ = "sla_policies"
    sla_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    response_time_minutes = Column(Integer, nullable=False)
    resolution_time_minutes = Column(Integer, nullable=False)
