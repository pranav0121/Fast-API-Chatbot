# Utility: Sync all existing tickets with SLA
from sqlalchemy.future import select
from db import get_db
import logging
import os
from models import SLAPolicy
from models import User, Category, CommonQuery, Ticket, TicketMessage, Feedback
from schemas import SLAPolicyCreate, SLAPolicyUpdate, SLAPolicyOut, SLAStatusOut, SLAViolationOut, SLAReportOut
from schemas import UserRegisterRequest, UserLoginRequest, TokenResponse
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, UploadFile
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession


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
        priority = (ticket.priority or "medium").lower()
        sla_policy = sla_policies.get(priority)
        if sla_policy:
            ticket.current_sla_target = now + \
                timedelta(minutes=sla_policy.resolution_time_minutes)
            ticket.updatedat = now
            db.add(ticket)
            updated += 1
    if updated:
        await db.commit()
    return {"status": "synced", "updated": updated}


# Set up logging
logging.basicConfig(filename='user_activity.log', level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(message)s')

# =====================
# SLA Controllers (merged from sla_controller.py)
# =====================


async def get_sla_policies_controller(db: AsyncSession):
    result = await db.execute(select(SLAPolicy))
    return result.scalars().all()


async def create_sla_policy_controller(sla: SLAPolicyCreate, db: AsyncSession):
    new_policy = SLAPolicy(**sla.dict())
    db.add(new_policy)
    await db.commit()
    await db.refresh(new_policy)
    return new_policy


async def update_sla_policy_controller(sla_id: int, sla: SLAPolicyUpdate, db: AsyncSession):
    result = await db.execute(select(SLAPolicy).where(SLAPolicy.sla_id == sla_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    for key, value in sla.dict(exclude_unset=True).items():
        setattr(policy, key, value)
    await db.commit()
    await db.refresh(policy)
    return policy


async def get_ticket_sla_status_controller(ticket_id: int, db: AsyncSession):
    # Example logic: find ticket, get SLA policy, calculate status
    result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # For demo, assume all tickets use the first SLA policy
    policy_result = await db.execute(select(SLAPolicy))
    sla_policy = policy_result.scalars().first()
    if not sla_policy:
        raise HTTPException(status_code=404, detail="No SLA policy found")
    # Calculate status (placeholder logic)
    status = "on track"
    time_left = sla_policy.resolution_time_minutes  # Placeholder
    return {
        "ticket_id": ticket.ticketid,
        "sla_policy": sla_policy,
        "status": status,
        "time_left_minutes": time_left
    }


async def get_sla_violations_controller(db: AsyncSession):
    # Example: find tickets that are breached (placeholder logic)
    # In real logic, compare ticket timestamps to SLA
    return []


async def get_sla_report_controller(db: AsyncSession):
    # Example: count tickets and breached tickets (placeholder logic)
    total_tickets = 0
    tickets_within_sla = 0
    tickets_breached = 0
    compliance_percentage = 100.0
    return {
        "total_tickets": total_tickets,
        "tickets_within_sla": tickets_within_sla,
        "tickets_breached": tickets_breached,
        "compliance_percentage": compliance_percentage
    }


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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
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
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# User registration
async def register_user_controller(db, payload: UserRegisterRequest):
    from models import User
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
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
    return {"status": "success", "user_id": user.userid}

# User login


async def login_user_controller(db, form_data: OAuth2PasswordRequestForm):
    from models import User
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.passwordhash):
        logging.error(f"FAILED LOGIN | email: {form_data.username}")
        raise HTTPException(
            status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    logging.info(f"LOGIN | user_id: {user.userid} | email: {user.email}")
    return TokenResponse(access_token=access_token)

# ...existing code...


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
        logging.error(f"USER NOT FOUND | uuid: {user_uuid}")
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
    # Assign SLA policy based on ticket priority
    from models import SLALog, TicketStatusLog
    sla_policies_result = await db.execute(select(SLAPolicy))
    sla_policies = {
        p.name.lower(): p for p in sla_policies_result.scalars().all()}
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    priority = (payload.priority or "medium").lower()
    sla_policy = sla_policies.get(priority)
    sla_target = None
    if sla_policy:
        sla_target = now + \
            timedelta(minutes=sla_policy.resolution_time_minutes)
    ticket = Ticket(
        userid=None,
        categoryid=payload.category_id,
        subject=payload.subject,
        status="open",
        priority=payload.priority,
        organizationname=payload.organization,
        createdby=payload.name,
        createdat=now,
        updatedat=now,
        current_sla_target=sla_target
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    logging.info(
        f"TICKET CREATED | subject: {payload.subject} | createdby: {payload.name} | ticket_id: {ticket.ticketid}")

    # Log SLA assignment event
    if sla_policy:
        sla_log = SLALog(
            ticket_id=ticket.ticketid,
            sla_policy_id=sla_policy.sla_id,
            event_type="assigned",
            timestamp=now,
            details=f"SLA assigned on ticket creation. SLA: {sla_policy.name}"
        )
        db.add(sla_log)

    # Log ticket status event
    status_log = TicketStatusLog(
        ticket_id=ticket.ticketid,
        status="open",
        timestamp=now,
        details="Ticket created"
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
        logging.info(
            f"TICKET MESSAGE CREATED | ticket_id: {ticket.ticketid} | content: {payload.message}")

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
    logging.info(
        f"TICKET MESSAGE ADDED | ticket_id: {ticket_id} | sender_id: {senderid} | content: {payload.content}")
    return {"message_id": message.messageid, "status": "success"}


async def upload_file_controller(file: UploadFile):
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_location = os.path.join(uploads_dir, file.filename)
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    logging.info(f"FILE UPLOADED | filename: {file.filename}")
    return {"file_url": f"/uploads/{file.filename}"}


async def submit_feedback_controller(db, payload):
    feedback = Feedback(
        ticketid=payload.ticket_id,
        rating=payload.rating,
        comment=payload.feedback
    )
    db.add(feedback)
    await db.commit()
    logging.info(
        f"FEEDBACK SUBMITTED | ticket_id: {payload.ticket_id} | rating: {payload.rating}")
    return {"status": "success"}


async def test_database_controller(db):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}
