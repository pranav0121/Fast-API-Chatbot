# Imports grouped by type for clarity
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, RolePermission
from db import get_db
from schemas import (
    TicketCreateRequest, TicketMessageRequest, FeedbackRequest,
    UserRegisterRequest, UserLoginRequest, TokenResponse
)

# Controller imports
from controller import (
    get_categories_controller,
    get_common_queries_controller,
    create_ticket_controller,
    get_ticket_details_controller,
    get_ticket_messages_controller,
    add_ticket_message_controller,
    upload_file_controller,
    submit_feedback_controller,
    test_database_controller,
    get_users_controller,
    get_user_by_uuid_controller,
    register_user_controller,
    login_user_controller,
    get_current_user
)
# YouShop API imports (import only if needed for youshop functionality)

from youshop_API.youshop.yshop_router import router as youshop_router

router = APIRouter()

# =====================
# User Endpoints
# =====================


def require_role_permission(permission: str, module: str):
    async def dependency(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
        roleid = getattr(current_user, 'roleid', None)
        if not roleid:
            raise HTTPException(
                status_code=403, detail="No role assigned to user")
        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == roleid,
                RolePermission.permission == permission,
                RolePermission.module == module
            )
        )
        if not result.scalar():
            raise HTTPException(
                status_code=403, detail=f"Role does not have '{permission}' permission for module '{module}'")
        return current_user
    return dependency


# Only admin (with manage-users) can create users
@router.post("/register", summary="Register a new user", tags=["Users"])
async def register_user(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_permission('manage', 'users'))
):
    return await register_user_controller(db, payload)


@router.post("/login", response_model=TokenResponse, summary="User login and get JWT token", tags=["Users"])
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    return await login_user_controller(db, form_data)


# Only users with read permission on users module can view users
@router.get("/users", summary="Get all users", tags=["Users"])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_permission('read', 'users'))
):
    return await get_users_controller(db)


@router.get("/users/uuid/{user_uuid}", summary="Get user by UUID", tags=["Users"])
async def get_user_by_uuid(
    user_uuid: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role_permission('read', 'users'))
):
    return await get_user_by_uuid_controller(db, user_uuid)

# =====================
# Category Endpoints
# =====================


@router.get("/categories", summary="Get all support categories", tags=["Categories"])
async def get_categories(request: Request, db: AsyncSession = Depends(get_db)):
    return await get_categories_controller(db)


@router.get("/common-queries/{category_id}", summary="Get common queries for category", tags=["Categories"])
async def get_common_queries(category_id: int, db: AsyncSession = Depends(get_db)):
    return await get_common_queries_controller(db, category_id)

# =====================
# Ticket Endpoints
# =====================
# Only users with create permission on tickets module can create tickets


@router.post("/tickets", summary="Create new ticket", tags=["Tickets"])
async def create_ticket(
    payload: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await create_ticket_controller(db, payload)


@router.get("/tickets/{ticket_id}", summary="Get ticket details", tags=["Tickets"])
async def get_ticket_details(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_details_controller(db, ticket_id)


@router.get("/tickets/{ticket_id}/messages", summary="Get messages for ticket", tags=["Tickets"])
async def get_ticket_messages(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_messages_controller(db, ticket_id)


@router.post("/tickets/{ticket_id}/messages", summary="Add message to ticket", tags=["Tickets"])
async def add_ticket_message(ticket_id: int, payload: TicketMessageRequest, db: AsyncSession = Depends(get_db)):
    return await add_ticket_message_controller(db, ticket_id, payload)


@router.delete("/tickets/{ticket_id}", summary="Delete ticket", tags=["Tickets"])
async def delete_ticket(ticket_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    from models import Ticket, TicketMessage, Feedback, TicketStatusLog
    await db.execute(TicketMessage.__table__.delete().where(TicketMessage.ticketid == ticket_id))
    await db.execute(Feedback.__table__.delete().where(Feedback.ticketid == ticket_id))
    await db.execute(TicketStatusLog.__table__.delete().where(TicketStatusLog.ticket_id == ticket_id))
    ticket = (await db.execute(select(Ticket).where(Ticket.ticketid == ticket_id))).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.delete(ticket)
    await db.commit()
    return {"message": f"Ticket {ticket_id} and all related data deleted successfully"}

# =====================
# File Upload
# =====================


@router.post("/upload", summary="Upload file", tags=["File Upload"])
async def upload_file(file: UploadFile = File(...)):
    return await upload_file_controller(file)

# =====================
# Feedback
# =====================


@router.post("/feedback", summary="Submit feedback/rating", tags=["Feedback"])
async def submit_feedback(payload: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    return await submit_feedback_controller(db, payload)


# =====================
# Health Check
# =====================


@router.get("/database/test", summary="Test system health", tags=["Health Check"])
async def test_database(db: AsyncSession = Depends(get_db)):
    return await test_database_controller(db)
