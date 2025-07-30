
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# User Table
class User(Base):
    __tablename__ = "users"
    userid = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    createdat = Column(DateTime, nullable=True)
    passwordhash = Column(Text, nullable=True)
    preferredlanguage = Column(Text, nullable=False)
    organizationname = Column(Text, nullable=True)
    position = Column(Text, nullable=True)
    prioritylevel = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    department = Column(Text, nullable=True)
    lastlogin = Column(DateTime, nullable=True)
    isactive = Column(Boolean, nullable=True)
    isadmin = Column(Boolean, nullable=True)
    country = Column(Text, nullable=True)
    last_device_type = Column(Text, nullable=True)
    device_type = Column(String, nullable=True)
    operating_system = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    browser_version = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    device_brand = Column(String, nullable=True)
    device_model = Column(String, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    username = Column(Text, nullable=True)
    organization_id = Column(Integer, nullable=True)

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Categories Table
class Category(Base):
    __tablename__ = "categories"
    categoryid = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    team = Column(Text, nullable=False)
    createdat = Column(DateTime, nullable=True)

# CommonQueries Table (commonqueries)
class CommonQuery(Base):
    __tablename__ = "commonqueries"
    queryid = Column(Integer, primary_key=True, index=True)
    categoryid = Column(Integer, ForeignKey("categories.categoryid"))
    question = Column(Text, nullable=False)
    solution = Column(Text, nullable=False)
    createdat = Column(DateTime, nullable=True)
    updatedat = Column(DateTime, nullable=True)
    category = relationship("Category")

# Tickets Table
class Ticket(Base):
    __tablename__ = "tickets"
    ticketid = Column(Integer, primary_key=True, index=True)
    userid = Column(Integer, nullable=True)
    categoryid = Column(Integer, ForeignKey("categories.categoryid"), nullable=True)
    subject = Column(Text, nullable=False)
    status = Column(Text, nullable=True)
    createdat = Column(DateTime, nullable=True)
    updatedat = Column(DateTime, nullable=True)
    priority = Column(Text, nullable=True)
    organizationname = Column(Text, nullable=True)
    createdby = Column(Text, nullable=True)
    assignedto = Column(Text, nullable=True)
    escalation_level = Column(Integer, nullable=True)
    current_sla_target = Column(DateTime, nullable=True)
    resolution_method = Column(Text, nullable=True)
    bot_attempted = Column(Boolean, nullable=True)
    partner_id = Column(Integer, nullable=True)
    odoo_customer_id = Column(Integer, nullable=True)
    odoo_ticket_id = Column(Integer, nullable=True)
    sla_time = Column(Integer, nullable=True)
    raise_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    country = Column(Text, nullable=True)
    source_device = Column(Text, nullable=True)
    enddate = Column(DateTime, nullable=True)
    escalationlevel = Column(Text, nullable=True)
    escalationreason = Column(Text, nullable=True)
    escalationtimestamp = Column(DateTime, nullable=True)
    escalatedto = Column(Text, nullable=True)
    slabreachstatus = Column(Text, nullable=True)
    autoescalated = Column(Boolean, nullable=True)
    escalationhistory = Column(Text, nullable=True)
    currentassignedrole = Column(Text, nullable=True)
    slatarget = Column(DateTime, nullable=True)
    originalslatarget = Column(DateTime, nullable=True)
    device_type = Column(Text, nullable=True)
    operating_system = Column(String, nullable=True)
    browser = Column(String, nullable=True)
    browser_version = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    device_brand = Column(String, nullable=True)
    device_model = Column(String, nullable=True)
    device_fingerprint = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    category = relationship("Category")

# Ticket Messages Table (messages)
class TicketMessage(Base):
    __tablename__ = "messages"
    messageid = Column(Integer, primary_key=True, index=True)
    ticketid = Column(Integer, ForeignKey("tickets.ticketid"), nullable=True)
    senderid = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    isadminreply = Column(Boolean, nullable=True)
    createdat = Column(DateTime, nullable=True)
    isbotresponse = Column(Boolean, nullable=False)
    ticket = relationship("Ticket")

# Feedback Table
class Feedback(Base):
    __tablename__ = "feedback"
    feedbackid = Column(Integer, primary_key=True, index=True)
    ticketid = Column(Integer, ForeignKey("tickets.ticketid"), nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    createdat = Column(DateTime, nullable=True)
    ticket = relationship("Ticket")
