from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from fastapi import HTTPException
from models import User, Category, CommonQuery, Ticket, TicketMessage, Feedback, TicketStatusLog
from sla_models import SLAPolicy, SLALog
from datetime import datetime, timedelta
from schemas import (
    UserRegisterRequest, TicketCreateRequest, TicketMessageRequest, FeedbackRequest,
    SLAPolicyCreate, SLAPolicyUpdate
)

# --- User Operations ---


async def register_user(db: AsyncSession, payload: UserRegisterRequest):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        name=payload.name,
        email=payload.email,
        passwordhash=payload.password,  # Hash before calling this
        preferredlanguage=payload.preferredlanguage,
        organizationname=payload.organizationname,
        position=payload.position,
        prioritylevel=payload.prioritylevel,
        phone=payload.phone,
        department=payload.department,
        country=payload.country,
        createdat=datetime.utcnow(),
        isactive=True,
        isadmin=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_uuid(db: AsyncSession, user_uuid: str):
    result = await db.execute(select(User).where(User.uuid == user_uuid))
    return result.scalar_one_or_none()

# --- Category & Common Queries ---


async def get_categories(db: AsyncSession):
    result = await db.execute(select(Category))
    return result.scalars().all()


async def get_common_queries(db: AsyncSession, category_id: int):
    result = await db.execute(select(CommonQuery).where(CommonQuery.categoryid == category_id))
    return result.scalars().all()

# --- Ticket Operations ---


async def create_ticket(db: AsyncSession, payload: TicketCreateRequest):
    now = datetime.utcnow()
    ticket = Ticket(
        userid=None,
        categoryid=payload.category_id,
        subject=payload.subject,
        status="open",
        priority=payload.priority,
        organizationname=payload.organization,
        createdby=payload.name,
        createdat=now,
        updatedat=now
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_tickets(db: AsyncSession, status=None, priority=None, category=None, limit=50, offset=0):
    query = select(Ticket)
    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if category:
        cat_result = await db.execute(select(Category).where(Category.name == category))
        cat = cat_result.scalar_one_or_none()
        if cat:
            query = query.where(Ticket.categoryid == cat.categoryid)
        else:
            return []
    query = query.order_by(desc(Ticket.createdat)).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


async def get_ticket_details(db: AsyncSession, ticket_id: int):
    result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    return result.scalar_one_or_none()


async def update_ticket_status(db: AsyncSession, ticket_id: int, status: str):
    result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = status
    ticket.updatedat = datetime.utcnow()
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def delete_ticket(db: AsyncSession, ticket_id: int):
    ticket = await get_ticket_details(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.delete(ticket)
    await db.commit()
    return True

# --- Ticket Messages ---


async def get_ticket_messages(db: AsyncSession, ticket_id: int):
    result = await db.execute(select(TicketMessage).where(TicketMessage.ticketid == ticket_id))
    return result.scalars().all()


async def add_ticket_message(db: AsyncSession, ticket_id: int, payload: TicketMessageRequest):
    message = TicketMessage(
        ticketid=ticket_id,
        senderid=payload.user_id,
        content=payload.content,
        isadminreply=payload.is_admin,
        createdat=datetime.utcnow(),
        isbotresponse=False
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message

# --- Feedback ---


async def submit_feedback(db: AsyncSession, payload: FeedbackRequest):
    feedback = Feedback(
        ticketid=payload.ticket_id,
        rating=payload.rating,
        comment=payload.feedback,
        createdat=datetime.utcnow()
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback

# --- SLA Operations ---


async def get_sla_policies(db: AsyncSession):
    result = await db.execute(select(SLAPolicy))
    return result.scalars().all()


async def create_sla_policy(db: AsyncSession, payload: SLAPolicyCreate):
    policy = SLAPolicy(**payload.dict())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


async def update_sla_policy(db: AsyncSession, sla_id: int, payload: SLAPolicyUpdate):
    result = await db.execute(select(SLAPolicy).where(SLAPolicy.sla_id == sla_id))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="SLA policy not found")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(policy, key, value)
    await db.commit()
    await db.refresh(policy)
    return policy

# --- Analytics ---


async def get_ticket_analytics(db: AsyncSession):
    total_result = await db.execute(select(func.count(Ticket.ticketid)))
    total_tickets = total_result.scalar_one()
    statuses = ["open", "in_progress", "resolved", "closed"]
    tickets_by_status = {}
    for status_val in statuses:
        res = await db.execute(select(func.count()).where(Ticket.status == status_val))
        tickets_by_status[status_val] = res.scalar_one()
    return {
        "total_tickets": total_tickets,
        "tickets_by_status": tickets_by_status
    }
