from models import User, Category, CommonQuery, Ticket, TicketMessage, Feedback
from sla_models import SLAPolicy, SLALog
from sla_controller import (
    get_sla_policies_controller,
    create_sla_policy_controller,
    update_sla_policy_controller,
    get_ticket_sla_status_controller,
    get_sla_violations_controller,
    get_sla_report_controller
)
import os
import logging
from db import get_db
from sqlalchemy.future import select
from schemas import UserRegisterRequest, UserLoginRequest, TokenResponse
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, UploadFile
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import SLAPolicyCreate, SLAPolicyUpdate, SLAPolicyOut, SLAStatusOut, SLAViolationOut, SLAReportOut


# Load priority levels from .env
PRIORITY_LEVELS = {
    "critical": os.getenv("PRIORITY_LEVEL_0", "critical").lower(),
    "high": os.getenv("PRIORITY_LEVEL_1", "high").lower(),
    "medium": os.getenv("PRIORITY_LEVEL_2", "medium").lower(),
    "low": os.getenv("PRIORITY_LEVEL_3", "low").lower(),
}
PRIORITY_LEVELS_REVERSE = {v: k for k, v in PRIORITY_LEVELS.items()}


def get_priority_name(level: int) -> str:
    priority_map = {
        0: PRIORITY_LEVELS["critical"],
        1: PRIORITY_LEVELS["high"],
        2: PRIORITY_LEVELS["medium"],
        3: PRIORITY_LEVELS["low"],
    }
    return priority_map.get(level, PRIORITY_LEVELS["medium"])


def get_priority_level(name: str) -> int:
    level_map = {
        PRIORITY_LEVELS["critical"]: 0,
        PRIORITY_LEVELS["high"]: 1,
        PRIORITY_LEVELS["medium"]: 2,
        PRIORITY_LEVELS["low"]: 3,
    }
    return level_map.get((name or '').lower(), 2)


async def assign_sla_to_ticket(db: AsyncSession, ticket, ticket_priority: str):
    """Assign SLA policy to ticket using the same logic as SLA controller"""
    # Get all SLA policies
    policy_result = await db.execute(select(SLAPolicy))
    all_policies = policy_result.scalars().all()

    # Create case-insensitive mapping
    sla_policies = {}
    for p in all_policies:
        policy_name = str(p.name).strip().lower()
        sla_policies[policy_name] = p

    if not sla_policies:
        return None

    ticket_priority_normalized = ticket_priority.strip().lower()
    matched_sla_name = None
    sla_policy = None

    # First try exact match with ticket priority
    if ticket_priority_normalized in sla_policies:
        sla_policy = sla_policies[ticket_priority_normalized]
        matched_sla_name = sla_policy.name
    else:
        # Try mapping from env variables and check if SLA policy exists
        for env_key, env_value in PRIORITY_LEVELS.items():
            if ticket_priority_normalized == env_value:
                # Look for SLA policy with this name (case insensitive)
                if env_key in sla_policies:
                    sla_policy = sla_policies[env_key]
                    matched_sla_name = sla_policy.name
                    break

        # If still no match, try partial matching on policy names
        if not sla_policy:
            for key, policy in sla_policies.items():
                if key in ticket_priority_normalized or ticket_priority_normalized in key:
                    sla_policy = policy
                    matched_sla_name = policy.name
                    break

        # Final fallback to default
        if not sla_policy:
            sla_policy = sla_policies.get(
                "default sla") or list(sla_policies.values())[0]
            matched_sla_name = sla_policy.name if hasattr(
                sla_policy, "name") else sla_policy.get("name")

    # Set SLA target time
    if sla_policy and ticket.createdat:
        sla_target = ticket.createdat + \
            timedelta(minutes=sla_policy.resolution_time_minutes)
        ticket.current_sla_target = sla_target

        log_user_activity(
            None,
            "SLA_ASSIGNED",
            f"ticket_id: {ticket.ticketid} | priority: {ticket_priority} | sla: {matched_sla_name} | target: {sla_target}"
        )

    return sla_policy


async def sync_existing_tickets_with_sla(db: AsyncSession):
    from datetime import datetime, timedelta
    # Get all SLA policies and map by name (priority)
    sla_policies_result = await db.execute(select(SLAPolicy))
    sla_policies = {
        p.name.lower(): p for p in sla_policies_result.scalars().all()}
    # Find tickets without current_sla_target
    tickets_result = await db.execute(select(Ticket).where(Ticket.current_sla_target == None))
    tickets = tickets_result.scalars().all()
    now = datetime.utcnow()
    updated = 0
    for ticket in tickets:
        # Use env-based priorities
        priority_name = (ticket.priority or get_priority_name(2)).lower()
        sla_policy = sla_policies.get(priority_name)
        if sla_policy:
            ticket.current_sla_target = now + \
                timedelta(minutes=sla_policy.resolution_time_minutes)
            ticket.updatedat = now
            db.add(ticket)
            updated += 1
    if updated:
        await db.commit()
    return {"status": "synced", "updated": updated}


# Set up separate loggers for user, admin, and superadmin
user_logger = logging.getLogger("user_logger")
user_handler = logging.FileHandler("user_activity.log")
user_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s'))
user_logger.addHandler(user_handler)
user_logger.setLevel(logging.INFO)

admin_logger = logging.getLogger("admin_logger")
admin_handler = logging.FileHandler("admin_activity.log")
admin_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s'))
admin_logger.addHandler(admin_handler)
admin_logger.setLevel(logging.INFO)

superadmin_logger = logging.getLogger("superadmin_logger")
superadmin_handler = logging.FileHandler("superadmin_activity.log")
superadmin_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)s | %(message)s'))
superadmin_logger.addHandler(superadmin_handler)
superadmin_logger.setLevel(logging.INFO)


def get_user_type_logger(user):
    """Get appropriate logger based on user role"""
    if not user:
        return superadmin_logger  # Default to superadmin for system actions

    # Handle string UUIDs - default to user logger
    if isinstance(user, str):
        return user_logger

    # Use only direct boolean fields to avoid lazy loading database queries
    # Accessing user.role would trigger an async DB query which causes greenlet issues
    if getattr(user, 'is_superadmin', False):
        return superadmin_logger
    elif getattr(user, 'isadmin', False):
        return admin_logger
    else:
        return user_logger


def log_user_activity(user, action, details="", level="INFO"):
    """Enhanced logging function for user activities"""
    logger = get_user_type_logger(user)

    if user:
        # Handle both User objects and string UUIDs
        if isinstance(user, str):
            # If user is a string UUID, we'll log it as such
            user_info = f"USER_UUID:{user}"
            role = "USER"  # Default role for UUID-only logging
        else:
            # If user is a User object
            user_info = f"USER_ID:{user.userid} | EMAIL:{user.email}"
            role = "SUPERADMIN" if getattr(user, 'is_superadmin', False) else \
                   "ADMIN" if getattr(user, 'isadmin', False) else "USER"

            # Note: Avoiding user.role access to prevent lazy loading DB queries

        message = f"{user_info} | ROLE:{role} | ACTION:{action}"
        if details:
            message += f" | {details}"
    else:
        message = f"SYSTEM | ACTION:{action}"
        if details:
            message += f" | {details}"

    if level.upper() == "ERROR":
        logger.error(message)
    elif level.upper() == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)


# JWT settings
# Change this to a strong secret in production
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + \
        (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": "YouCloud Pay"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)):
    from models import User
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    if db is None:
        raise credentials_exception
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User).options(selectinload(
            User.role)).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# User registration
async def register_user_controller(db, payload: UserRegisterRequest):
    from models import User
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        log_user_activity(None, "REGISTRATION_FAILED",
                          f"email_already_exists: {payload.email}", "WARNING")
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(payload.password)
    # Always assign roleid=3 (user) for new users
    user = User(
        name=payload.name,
        email=payload.email,
        passwordhash=hashed_password,
        preferredlanguage=payload.preferredlanguage,
        organizationname=payload.organizationname,
        position=payload.position,
        prioritylevel=payload.prioritylevel,
        phone=payload.phone,
        department=payload.department,
        country=payload.country,
        createdat=datetime.utcnow(),
        isactive=True,
        isadmin=False,
        roleid=3
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log_user_activity(user, "USER_REGISTERED",
                      f"new_user_created | org: {payload.organizationname}")
    return {"status": "success", "user_id": user.userid}

# User login


async def login_user_controller(db, form_data: OAuth2PasswordRequestForm):
    from models import User
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.passwordhash):
        log_user_activity(None, "LOGIN_FAILED",
                          f"email: {form_data.username}", "ERROR")
        raise HTTPException(
            status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={
        "sub": user.email,
        "user_id": user.userid,
        "role_id": user.roleid
    })
    log_user_activity(user, "LOGIN_SUCCESS", f"token_generated")
    return TokenResponse(access_token=access_token)


async def get_users_controller(db):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [
        {"userid": u.userid, "uuid": u.uuid, "name": u.name, "email": u.email}
        for u in users
    ]}


async def get_user_by_uuid_controller(db, user_uuid: str):
    result = await db.execute(select(User).where(User.uuid == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        log_user_activity(
            None,
            "USER_NOT_FOUND_ERROR",
            f"uuid: {user_uuid}"
        )
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "userid": user.userid,
        "uuid": user.uuid,
        "name": user.name,
        "email": user.email,
        "createdat": user.createdat,
        "isactive": user.isactive,
        "isadmin": user.isadmin
    }


async def get_categories_controller(db):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    return {"categories": [{"id": c.categoryid, "name": c.name} for c in categories]}


async def get_common_queries_controller(db, category_id: int):
    result = await db.execute(select(CommonQuery).where(CommonQuery.categoryid == category_id))
    queries = result.scalars().all()
    return {"queries": [{"id": q.queryid, "question": q.question, "solution": q.solution} for q in queries]}


async def create_ticket_controller(db, payload):
    from models import TicketStatusLog
    from datetime import datetime, timedelta

    now = datetime.utcnow()

    # Validate and normalize priority
    requested_priority = (
        payload.priority or get_priority_name(2)).strip().lower()
    allowed_priorities = set(PRIORITY_LEVELS.values())

    if requested_priority not in allowed_priorities:
        requested_priority = get_priority_name(2)  # Default to medium

    # Create ticket first
    ticket = Ticket(
        userid=None,
        categoryid=payload.category_id,
        subject=payload.subject,
        status="open",
        priority=requested_priority,
        organizationname=payload.organization,
        createdby=payload.name,
        createdat=now,
        updatedat=now
    )
    db.add(ticket)
    await db.flush()  # Get ticket ID without committing

    # Assign SLA using consistent logic
    await assign_sla_to_ticket(db, ticket, requested_priority)

    await db.commit()
    await db.refresh(ticket)

    log_user_activity(
        None,
        "TICKET_CREATED",
        f"ticket_id: {ticket.ticketid} | subject: {payload.subject} | createdby: {payload.name} | priority: {requested_priority} | sla_target: {ticket.current_sla_target}"
    )

    # Log ticket status event
    status_log = TicketStatusLog(
        ticket_id=ticket.ticketid,
        old_status=None,
        new_status="open",
        changed_by_type="system",  # Required field
        created_at=now,
        changed_at=now,
        comment="Ticket created"
    )
    db.add(status_log)

    # Create initial message for the ticket
    if payload.message:
        message = TicketMessage(
            ticketid=ticket.ticketid,
            senderid=None,
            content=payload.message,
            isadminreply=False,
            isbotresponse=False,
            createdat=now
        )
        db.add(message)
        log_user_activity(
            None,
            "TICKET_MESSAGE_CREATED",
            f"ticket_id: {ticket.ticketid} | content_length: {len(payload.message)}"
        )

    await db.commit()
    return {"ticket_id": ticket.ticketid, "status": "success"}


async def get_ticket_details_controller(db, ticket_id: int):
    result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ticket": {
        "ticketid": ticket.ticketid,
        "subject": ticket.subject,
        "status": ticket.status,
        "priority": ticket.priority,
        "organizationname": ticket.organizationname
    }}


async def get_ticket_messages_controller(db, ticket_id: int):
    result = await db.execute(select(TicketMessage).where(TicketMessage.ticketid == ticket_id))
    messages = result.scalars().all()
    return {"messages": [{"id": m.messageid, "content": m.content, "is_admin": m.isadminreply} for m in messages]}


async def add_ticket_message_controller(db, ticket_id: int, payload):
    senderid = payload.user_id
    if senderid is not None:
        user_result = await db.execute(select(User).where(User.userid == senderid))
        user = user_result.scalar_one_or_none()
        if not user:
            senderid = None
    message = TicketMessage(
        ticketid=ticket_id,
        senderid=senderid,
        content=payload.content,
        isadminreply=bool(payload.is_admin),
        isbotresponse=False
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    log_user_activity(
        None,
        "TICKET_MESSAGE_ADDED",
        f"ticket_id: {ticket_id} | sender_id: {senderid} | content_length: {len(payload.content)}"
    )
    return {"message_id": message.messageid, "status": "success"}


async def upload_file_controller(file: UploadFile):
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_location = os.path.join(uploads_dir, file.filename)
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    log_user_activity(
        None,
        "FILE_UPLOADED",
        f"filename: {file.filename} | size: {len(content)} bytes"
    )
    return {"file_url": f"/uploads/{file.filename}"}


async def submit_feedback_controller(db, payload):
    feedback = Feedback(
        ticketid=payload.ticket_id,
        rating=payload.rating,
        comment=payload.feedback
    )
    db.add(feedback)
    await db.commit()
    log_user_activity(
        None,
        "FEEDBACK_SUBMITTED",
        f"ticket_id: {payload.ticket_id} | rating: {payload.rating}"
    )
    return {"status": "success"}


async def test_database_controller(db):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}
