from fastapi import UploadFile
import os
from sqlalchemy.future import select
from models import Category, CommonQuery, Ticket, TicketMessage, Feedback
from fastapi import HTTPException, status
from models import Category, CommonQuery, Ticket, TicketMessage, Feedback, User
from sqlalchemy import select

# ...existing code...


async def get_users_controller(db):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [{"userid": u.userid, "name": u.name, "email": u.email} for u in users]}


async def get_categories_controller(db):
    result = await db.execute(select(Category))
    categories = result.scalars().all()
    return {"categories": [{"id": c.categoryid, "name": c.name} for c in categories]}


async def get_common_queries_controller(db, category_id: int):
    result = await db.execute(select(CommonQuery).where(CommonQuery.categoryid == category_id))
    queries = result.scalars().all()
    return {"queries": [{"id": q.queryid, "question": q.question, "solution": q.solution} for q in queries]}


async def create_ticket_controller(db, payload):
    ticket = Ticket(
        userid=None,
        categoryid=payload.category_id,
        subject=payload.subject,
        status="open",
        priority=payload.priority,
        organizationname=payload.organization,
        createdby=payload.name,
        createdat=None,
        updatedat=None
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    # Create initial message for the ticket
    if payload.message:
        message = TicketMessage(
            ticketid=ticket.ticketid,
            senderid=None,
            content=payload.message,
            isadminreply=False,
            isbotresponse=False
        )
        db.add(message)
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
    return {"message_id": message.messageid, "status": "success"}


async def upload_file_controller(file: UploadFile):
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_location = os.path.join(uploads_dir, file.filename)
    with open(file_location, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"file_url": f"/uploads/{file.filename}"}


async def submit_feedback_controller(db, payload):
    feedback = Feedback(
        ticketid=payload.ticket_id,
        rating=payload.rating,
        comment=payload.feedback
    )
    db.add(feedback)
    await db.commit()
    return {"status": "success"}


async def test_database_controller(db):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}
