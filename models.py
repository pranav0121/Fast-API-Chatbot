
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# ...existing model classes...

# Ticket Status Logs Table


class TicketStatusLog(Base):
    __tablename__ = "ticket_status_logs"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.ticketid"), nullable=False)
    old_status = Column(Text)
    new_status = Column(Text)
    changed_by_id = Column(Integer)
    changed_by_type = Column(Text)
    escalation_level = Column(Integer)
    comment = Column(Text)
    # Map to database column 'metadata'
    ticket_metadata = Column("metadata", Text)
    created_at = Column(DateTime)
    changed_by = Column(Text)
    changed_at = Column(DateTime)
    sla_status = Column(Text)
    notes = Column(Text)
    metadata_json = Column(Text)


# User Table


class Role(Base):
    __tablename__ = "roles"
    roleid = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    permissions = relationship("RolePermission", back_populates="role")
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    userid = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True,
                  default=lambda: str(uuid.uuid4()), index=True)
    name = Column(Text, nullable=True)
    email = Column(Text, unique=True, nullable=True)
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
    admin_access_roles = Column(Text, nullable=True)  # Comma-separated roles
    country = Column(Text, nullable=True)
    permissions = relationship(
        "Permission", secondary="user_permissions", backref="users")
    roleid = Column(Integer, ForeignKey("roles.roleid"))
    role = relationship("Role", back_populates="users")
# RolePermission table for CRUD permissions


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.roleid"))
    # 'read', 'create', 'update', 'delete'
    permission = Column(String(50), nullable=False)
    # Added for module-based permissions
    module = Column(String(100), nullable=False)
    role = relationship("Role", back_populates="permissions")


# Association table for many-to-many User <-> Permission
user_permissions = Table(
    "user_permissions",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.userid", ondelete="CASCADE")),
    Column("permission_id", Integer, ForeignKey(
        "permissions.permissionid", ondelete="CASCADE")),
    # No need for primary_key=True here, handled by table definition
)

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
    categoryid = Column(Integer, ForeignKey(
        "categories.categoryid"), nullable=True)
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
    country = Column(Text, nullable=True)
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


class Permission(Base):
    __tablename__ = "permissions"
    permissionid = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.userid"))
    action = Column(Text)
    status = Column(Text)
    timestamp = Column(DateTime)
    details = Column(Text)
