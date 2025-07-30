

from fastapi import FastAPI
from router import public_router
from models import Base
from db import engine
import asyncio

app = FastAPI(title="Chatbot Cloud Public API")

@app.on_event("startup")
async def on_startup():
    # Create tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(public_router, prefix="/api")
