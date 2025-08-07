from datetime import datetime
import os
import logging
from models import User, Category, CommonQuery, Ticket, TicketMessage, Feedback
from sla_controller import match_ticket_to_sla_policy
from sqlalchemy.future import select
from schemas import UserRegisterRequest, UserLoginRequest, TokenResponse, SLAPolicyCreate, SLAPolicyUpdate, SLAPolicyOut, SLAStatusOut, SLAViolationOut, SLAReportOut
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, UploadFile
from dbactions import register_user, get_user_by_uuid, get_categories, get_common_queries, submit_feedback, create_ticket, get_tickets, get_ticket_details, update_ticket_status, delete_ticket, get_ticket_messages, add_ticket_message
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy import select
from db import get_db
from models import User


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/login"))):
    credentials_exception = HTTPException(
        status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, "your_secret_key_here",
                             algorithms=["HS256"])
        email: str = payload.get("sub")
        assert email is not None
    except:
        raise credentials_exception
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception
    return user


async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Ensure the current user is an admin."""
    if not getattr(current_user, 'isadmin', False):
        raise HTTPException(
            status_code=403, detail="Admin privileges required")
    return current_user

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def upload_file_controller(file: UploadFile):
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_location = os.path.join(uploads_dir, file.filename)
    content = await file.read()
    with open(file_location, "wb") as f:
        f.write(content)
    return {"file_url": f"/uploads/{file.filename}"}


async def login_user_controller(db: AsyncSession, form_data):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(form_data.password, user.passwordhash):
        raise HTTPException(
            status_code=401, detail="Incorrect email or password")
    access_token = jwt.encode(
        {"sub": user.email}, "your_secret_key_here", algorithm="HS256")
    return {"access_token": access_token}


async def register_user_controller(db: AsyncSession, payload):
    return await register_user(db, payload)


async def get_user_by_uuid_controller(db: AsyncSession, uuid: str):
    return await get_user_by_uuid(db, uuid)


async def get_users_controller(db: AsyncSession):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [{"userid": u.userid, "uuid": u.uuid, "name": u.name, "email": u.email} for u in users]}


async def test_database_controller(db: AsyncSession):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


async def submit_feedback_controller(db: AsyncSession, payload):
    return await submit_feedback(db, payload)


async def get_categories_controller(db: AsyncSession):
    return await get_categories(db)


async def add_ticket_message_controller(db: AsyncSession, ticket_id: int, payload):
    return await add_ticket_message(db, ticket_id, payload)


async def get_ticket_messages_controller(db: AsyncSession, ticket_id: int):
    return await get_ticket_messages(db, ticket_id)


async def get_ticket_details_controller(db: AsyncSession, ticket_id: int):
    return await get_ticket_details(db, ticket_id)


async def create_ticket_controller(db: AsyncSession, payload):
    return await create_ticket(db, payload)


async def get_common_queries_controller(db: AsyncSession, category_id: int):
    return await get_common_queries(db, category_id)


async def upload_file_controller(file: UploadFile):
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_location = os.path.join(uploads_dir, file.filename)
    content = await file.read()
    with open(file_location, "wb") as f:
        f.write(content)
    return {"file_url": f"/uploads/{file.filename}"}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def login_user_controller(db: AsyncSession, form_data):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(form_data.password, user.passwordhash):
        raise HTTPException(
            status_code=401, detail="Incorrect email or password")
    access_token = jwt.encode(
        {"sub": user.email}, "your_secret_key_here", algorithm="HS256")
    return {"access_token": access_token}


async def register_user_controller(db: AsyncSession, payload):
    return await register_user(db, payload)


async def get_user_by_uuid_controller(db: AsyncSession, uuid: str):
    return await get_user_by_uuid(db, uuid)


async def get_users_controller(db: AsyncSession):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [{"userid": u.userid, "uuid": u.uuid, "name": u.name, "email": u.email} for u in users]}


async def test_database_controller(db: AsyncSession):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


async def submit_feedback_controller(db: AsyncSession, payload):
    return await submit_feedback(db, payload)


async def get_categories_controller(db: AsyncSession):
    return await get_categories(db)


async def add_ticket_message_controller(db: AsyncSession, ticket_id: int, payload):
    return await add_ticket_message(db, ticket_id, payload)


async def get_ticket_messages_controller(db: AsyncSession, ticket_id: int):
    return await get_ticket_messages(db, ticket_id)


async def get_ticket_details_controller(db: AsyncSession, ticket_id: int):
    return await get_ticket_details(db, ticket_id)


async def create_ticket_controller(db: AsyncSession, payload):
    return await create_ticket(db, payload)


async def get_common_queries_controller(db: AsyncSession, category_id: int):
    return await get_common_queries(db, category_id)


# YouShop authentication utilities
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Generate a JWT token with expiration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def register_user_controller(db: AsyncSession, payload):
    return await register_user(db, payload)


async def get_user_by_uuid_controller(db: AsyncSession, uuid: str):
    return await get_user_by_uuid(db, uuid)


async def get_users_controller(db: AsyncSession):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [{"userid": u.userid, "uuid": u.uuid, "name": u.name, "email": u.email} for u in users]}


async def test_database_controller(db: AsyncSession):
    try:
        await db.execute(select(1))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}


async def submit_feedback_controller(db: AsyncSession, payload):
    return await submit_feedback(db, payload)


async def get_categories_controller(db: AsyncSession):
    return await get_categories(db)


async def add_ticket_message_controller(db: AsyncSession, ticket_id: int, payload):
    return await add_ticket_message(db, ticket_id, payload)


async def get_ticket_messages_controller(db: AsyncSession, ticket_id: int):
    return await get_ticket_messages(db, ticket_id)


async def get_ticket_details_controller(db: AsyncSession, ticket_id: int):
    return await get_ticket_details(db, ticket_id)


async def create_ticket_controller(db: AsyncSession, payload):
    return await create_ticket(db, payload)


async def get_common_queries_controller(db: AsyncSession, category_id: int):
    return await get_common_queries(db, category_id)


def log_user_activity(user_uuid: str, action: str, details: str = ""):
    """
    Logs user activity for admin actions to admin_activity.log.
    """
    timestamp = datetime.utcnow().isoformat()
    entry = f"{timestamp} | {user_uuid} | {action} | {details}\n"
    with open("admin_activity.log", "a") as f:
        f.write(entry)
