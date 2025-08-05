# Role-based CRUD permission check dependency
from controller import get_current_user, log_user_activity
from datetime import datetime, timedelta
from typing import List, Optional
from models import Ticket, TicketMessage, Category, User, Permission, AuditLog
from db import get_db
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, Request
from models import RolePermission
from router import require_role_permission


admin_router = APIRouter()

# Helper dependency to check admin


async def admin_required(current_user: User = Depends(get_current_user)):
    if not current_user.isadmin:
        raise HTTPException(
            status_code=403, detail="Admin privileges required")
    return current_user


def log_audit(db: AsyncSession, user_id: int, action: str, status: str, details: str = ""):
    log = AuditLog(user_id=user_id, action=action,
                   status=status, details=details)
    db.add(log)
    # This is now a sync helper, call await db.commit() after using in endpoints if needed

# --- Admin Dashboard ---


@admin_router.get("/dashboard-stats", summary="Get dashboard statistics", tags=["Admin Dashboard"], operation_id="get_dashboard_stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_required)):
    total_tickets = await db.execute(select(func.count(Ticket.ticketid)))
    pending_tickets = await db.execute(select(func.count()).where(Ticket.status.in_(["open", "in_progress"])))
    resolved_tickets = await db.execute(select(func.count()).where(Ticket.status == "resolved"))
    active_chats = await db.execute(select(func.count()).where(Ticket.status.in_(["open", "in_progress"])))

    stats = {
        "totalTickets": total_tickets.scalar(),
        "pendingTickets": pending_tickets.scalar(),
        "resolvedTickets": resolved_tickets.scalar(),
        "activeChats": active_chats.scalar(),
        "success": True
    }

    log_user_activity(
        current_user.uuid,
        "DASHBOARD_STATS_ACCESSED",
        f"total: {stats['totalTickets']} | pending: {stats['pendingTickets']} | resolved: {stats['resolvedTickets']}"
    )

    return stats


@admin_router.get("/recent-activity", summary="Get recent ticket activity", tags=["Admin Dashboard"], operation_id="get_recent_activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_required)):
    result = await db.execute(
        select(Ticket, User, Category)
        .join(User, Ticket.userid == User.userid, isouter=True)
        .join(Category, Ticket.categoryid == Category.categoryid, isouter=True)
        .order_by(desc(Ticket.createdat)).limit(10)
    )
    activities = []
    for ticket, user, category in result.all():
        user_name = user.name if user and user.name else ticket.createdby
        created_at = ticket.createdat.strftime(
            '%Y-%m-%d %H:%M:%S') if ticket.createdat else None
        activities.append({
            "ticketid": ticket.ticketid,
            "subject": ticket.subject,
            "category": category.name if category else None,
            "user_name": user_name,
            "created_at": created_at
        })
    return {"activities": activities}

# --- Admin Ticket ---


@admin_router.get("/tickets", summary="Get all tickets", tags=["Admin Ticket"], operation_id="get_admin_tickets")
async def get_admin_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_required)
):
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
            return {"tickets": [], "pagination": {"total": 0, "limit": limit, "offset": offset, "has_more": False}}
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_result.scalar_one()
    tickets = await db.execute(query.order_by(desc(Ticket.createdat)).offset(offset).limit(limit))
    ticket_list = [
        {
            "ticketid": t.ticketid,
            "subject": t.subject,
            "status": t.status,
            "priority": t.priority,
            "createdat": t.createdat,
            "organizationname": t.organizationname
        } for t in tickets.scalars().all()
    ]
    return {
        "tickets": ticket_list,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count
        }
    }


@admin_router.get("/tickets/{ticket_id}", summary="Get ticket details", tags=["Admin Ticket"], operation_id="get_admin_ticket_details")
async def get_admin_ticket_details(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_required)):
    ticket_result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    messages_result = await db.execute(select(TicketMessage).where(TicketMessage.ticketid == ticket_id))
    messages = messages_result.scalars().all()
    return {
        "ticket": {
            "ticketid": ticket.ticketid,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "createdat": ticket.createdat,
            "organizationname": ticket.organizationname,
            "messages": [
                {
                    "id": m.messageid,
                    "content": m.content,
                    "is_admin": m.isadminreply,
                    "created_at": m.createdat
                } for m in messages
            ]
        }
    }


@admin_router.get("/active-conversations", summary="Get active conversations", tags=["Admin Ticket"], operation_id="get_active_conversations")
async def get_active_conversations(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_required)):
    result = await db.execute(
        select(Ticket)
        .where(Ticket.status.in_(["open", "in_progress", "escalated"]))
        .order_by(desc(Ticket.updatedat))
    )
    tickets = result.scalars().all()
    return {
        "active_conversations": [
            {
                "ticketid": t.ticketid,
                "subject": t.subject,
                "status": t.status,
                "updatedat": t.updatedat
            } for t in tickets
        ]
    }


@admin_router.put("/tickets/{ticket_id}/status", summary="Update ticket status", tags=["Admin Ticket"], operation_id="update_ticket_status")
async def update_ticket_status(ticket_id: int, status: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_required)):
    ticket_result = await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        log_user_activity(
            current_user.uuid,
            "TICKET_STATUS_UPDATE_FAILED",
            f"ticket_id: {ticket_id} | reason: ticket_not_found"
        )
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = status
    ticket.updatedat = datetime.utcnow()
    await db.commit()

    log_user_activity(
        current_user.uuid,
        "TICKET_STATUS_UPDATED",
        f"ticket_id: {ticket_id} | old_status: {old_status} | new_status: {status}"
    )

    return {"status": "success", "ticket_id": ticket_id, "new_status": status}

# --- Admin Analytics ---


@admin_router.get("/analytics", summary="Get analytics data", tags=["Admin Analytics"], operation_id="get_admin_analytics")
async def get_analytics(db: AsyncSession = Depends(get_db), current_user: User = Depends(admin_required)):
    total_result = await db.execute(select(func.count(Ticket.ticketid)))
    total_tickets = total_result.scalar_one()
    statuses = ["open", "in_progress", "resolved", "closed"]
    tickets_by_status = {}
    for status_val in statuses:
        res = await db.execute(select(func.count()).where(Ticket.status == status_val))
        tickets_by_status[status_val] = res.scalar_one()
    # Use updatedat as the end date for analytics
    res = await db.execute(select(Ticket.createdat, Ticket.updatedat).where(Ticket.updatedat.isnot(None)))
    times = [((row[1] - row[0]).total_seconds() / 3600)
             for row in res.all() if row[0] and row[1]]
    avg_resolution_time = round(sum(times) / len(times), 2) if times else None
    cat_stats = await db.execute(
        select(Category.name, func.count(Ticket.ticketid))
        .join(Ticket, Category.categoryid == Ticket.categoryid)
        .group_by(Category.name)
        .order_by(func.count(Ticket.ticketid).desc())
    )
    cat_data = cat_stats.all()
    top_categories = [
        {"category": c[0], "count": c[1]} for c in cat_data[:3]
    ]
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    tickets_per_day = {}
    for day in days:
        next_day = day + timedelta(days=1)
        res = await db.execute(
            select(func.count()).where(
                Ticket.createdat >= day,
                Ticket.createdat < next_day
            )
        )
        tickets_per_day[str(day)] = res.scalar_one()
    return {
        "total_tickets": total_tickets,
        "tickets_by_status": tickets_by_status,
        "average_resolution_time_hours": avg_resolution_time,
        "top_categories": top_categories,
        "tickets_created_per_day": tickets_per_day
    }

# Example: Only admins with 'manage_users' can access this endpoint


@admin_router.get("/admin-users", summary="List all admin users", tags=["Admin"], operation_id="list_admin_users")
async def list_admin_users(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role_permission('manage', 'users'))):
    result = await db.execute(select(User).where(User.isadmin == True))
    admins = result.scalars().all()
    return [
        {
            "userid": admin.userid,
            "email": admin.email,
            "admin_access_roles": admin.admin_access_roles
        }
        for admin in admins
    ]

# Example protected endpoint


@admin_router.get("/protected-admin-action", summary="Protected admin action", tags=["Admin"], operation_id="protected_admin_action")
async def protected_admin_action(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_permission('manage', 'users'))
):
    return {"message": f"User {current_user.email} performed a protected admin action."}
