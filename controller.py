from sqlalchemy import select
import logging
from models import Category, CommonQuery, Ticket, TicketMessage, Feedback, User
from fastapi import HTTPException, status
from models import Category, CommonQuery, Ticket, TicketMessage, Feedback
from sqlalchemy.future import select
import os
from fastapi import UploadFile
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from schemas import UserRegisterRequest, UserLoginRequest, TokenResponse


# Set up logging
logging.basicConfig(
    filename='user_activity.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
)

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


async def get_current_user(db=Depends(lambda: None), token: str = Depends(oauth2_scheme)):
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
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(payload.password)
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
        isadmin=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"status": "success", "user_id": user.userid}

# User login


async def login_user_controller(db, payload: UserLoginRequest):
    from models import User
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.passwordhash):
        logging.error(f"FAILED LOGIN | email: {payload.email}")
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
    logging.info(
        f"TICKET CREATED | subject: {payload.subject} | createdby: {payload.name} | ticket_id: {ticket.ticketid}")

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
        logging.info(
            f"TICKET MESSAGE CREATED | ticket_id: {ticket.ticketid} | content: {payload.message}")
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
