from fastapi import APIRouter, Request, Depends, status, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
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
    get_users_controller
)
from schemas import (
    TicketCreateRequest, TicketMessageRequest, FeedbackRequest
)
from db import get_db

public_router = APIRouter()

@public_router.get("/categories", summary="Get all support categories")
async def get_categories(request: Request, db: AsyncSession = Depends(get_db)):
    return await get_categories_controller(db)

@public_router.get("/common-queries/{category_id}", summary="Get common queries for category")
async def get_common_queries(category_id: int, db: AsyncSession = Depends(get_db)):
    return await get_common_queries_controller(db, category_id)

@public_router.post("/tickets", summary="Create new ticket")
async def create_ticket(payload: TicketCreateRequest, db: AsyncSession = Depends(get_db)):
    return await create_ticket_controller(db, payload)

@public_router.get("/tickets/{ticket_id}", summary="Get ticket details")
async def get_ticket_details(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_details_controller(db, ticket_id)

@public_router.get("/tickets/{ticket_id}/messages", summary="Get messages for ticket")
async def get_ticket_messages(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_messages_controller(db, ticket_id)

@public_router.post("/tickets/{ticket_id}/messages", summary="Add message to ticket")
async def add_ticket_message(ticket_id: int, payload: TicketMessageRequest, db: AsyncSession = Depends(get_db)):
    return await add_ticket_message_controller(db, ticket_id, payload)

@public_router.post("/upload", summary="Upload file")
async def upload_file(file: UploadFile = File(...)):
    return await upload_file_controller(file)

@public_router.post("/feedback", summary="Submit feedback/rating")
async def submit_feedback(payload: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    return await submit_feedback_controller(db, payload)

@public_router.get("/database/test", summary="Test system health")
async def test_database(db: AsyncSession = Depends(get_db)):
    return await test_database_controller(db)
@public_router.get("/users", summary="Get all users")
async def get_users(db: AsyncSession = Depends(get_db)):
    return await get_users_controller(db)
