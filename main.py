from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from fastapi import FastAPI

from router import router
from admin_router import admin_router
from sla_router import sla_router
from models import Base
from youshop_API.youshop.yshop_models import YShopProduct, YShopOrder, YShopOrderItem, YShopCartItem
from db import engine
import asyncio
from youshop_API.youshop.yshop_router import router as yshop_router

app = FastAPI(title="Chatbot Cloud Public API")


@app.on_event("startup")
async def on_startup():
    # Create tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(sla_router)

# YouShop Chatbot endpoints
app.include_router(yshop_router)
