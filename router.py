
from schemas import (
    TicketCreateRequest, TicketMessageRequest, FeedbackRequest,
    UserRegisterRequest, UserLoginRequest, TokenResponse
)
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
    get_user_by_uuid_controller
)
from sqlalchemy.ext.asyncio import AsyncSession
from controller import register_user_controller, login_user_controller
from db import get_db
from fastapi import APIRouter, Request, Depends, status, HTTPException, UploadFile, File
router = APIRouter()

# =====================
# User Endpoints
# =====================
@router.post("/register", summary="Register a new user", tags=["Users"])
async def register_user(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_user_controller(db, payload)

@router.post("/login", response_model=TokenResponse, summary="User login and get JWT token", tags=["Users"])
async def login_user(payload: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    return await login_user_controller(db, payload)

@router.get("/users", summary="Get all users", tags=["Users"])
async def get_users(db: AsyncSession = Depends(get_db)):
    return await get_users_controller(db)

@router.get("/users/uuid/{user_uuid}", summary="Get user by UUID", tags=["Users"])
async def get_user_by_uuid(user_uuid: str, db: AsyncSession = Depends(get_db)):
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
@router.post("/tickets", summary="Create new ticket", tags=["Tickets"])
async def create_ticket(payload: TicketCreateRequest, db: AsyncSession = Depends(get_db)):
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
