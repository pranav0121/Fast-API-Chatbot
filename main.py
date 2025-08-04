from sqlalchemy.ext.asyncio import AsyncSession
from controller import sync_existing_tickets_with_sla
from db import get_db
from fastapi import FastAPI
from router import router
from admin_router import admin_router
from sla_router import sla_router
from models import Base
from db import engine
import asyncio

app = FastAPI(title="Chatbot Cloud Public API")


@app.on_event("startup")
async def on_startup():
    # Create tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Sync existing tickets with SLA
    async with AsyncSession(engine) as session:
        await sync_existing_tickets_with_sla(session)

app.include_router(router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(sla_router)
