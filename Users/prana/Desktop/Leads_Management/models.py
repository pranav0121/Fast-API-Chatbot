from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    score = Column(Float, nullable=False)


class Answer(Base):
    __tablename__ = 'answers'

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False)
    question_id = Column(Integer, nullable=False)
    answer_text = Column(Text, nullable=False)
    time_taken = Column(Integer, nullable=True)  # seconds
    score_earned = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())


class Lead(Base):
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False, unique=True)
    utm_source = Column(String, nullable=True)
    lead_score = Column(Float, default=0.0)
    lead_type = Column(String, nullable=True)  # SQL, MQL, Unqualified
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    location = Column(String, nullable=True)
    staff_size = Column(String, nullable=True)
    monthly_sales = Column(String, nullable=True)
    features_interested = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class UserBehavior(Base):
    __tablename__ = 'user_behaviors'

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    score_change = Column(Float, default=0.0)
    behavior_metadata = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=func.now())
