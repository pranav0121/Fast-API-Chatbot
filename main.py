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
from youshop_API.youshop.yshop_admin_router import router as yshop_admin_router
from sqlalchemy import text
from youshop_API.youshop.yshop_controller import get_password_hash

app = FastAPI(title="Chatbot Cloud Public API")


@app.on_event("startup")
async def on_startup():
    # Create tables if they do not exist
    async with engine.begin() as conn:
        # Create tables if they do not exist
        await conn.run_sync(Base.metadata.create_all)
        # Ensure 'is_active' column exists in yshop_products
        # Ensure 'is_active' column exists in yshop_products
        # Ensure 'is_active' column exists in yshop_products
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS yshop_products
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
                """
            )
        )
        # Ensure 'user_id' column exists in yshop_orders
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS yshop_orders
                ADD COLUMN IF NOT EXISTS user_id INTEGER;
                """
            )
        )
        # Ensure yshop_customers table exists
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS yshop_customers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    passwordhash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_admin BOOLEAN DEFAULT FALSE
                );
                """
            )
        )
        # Ensure 'is_admin' column exists in yshop_customers (for existing tables)
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS yshop_customers
                ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
                """
            )
        )
        # Ensure default YouShop admin user exists
        admin_pw = get_password_hash("password-admin123")
        await conn.execute(
            text(
                """
                INSERT INTO yshop_customers (name, email, passwordhash, is_admin)
                SELECT :name, CAST(:email AS VARCHAR), :passwordhash, TRUE
                WHERE NOT EXISTS (
                  SELECT 1 FROM yshop_customers WHERE email = CAST(:email AS VARCHAR)
                );
                """
            ),
            {
                "name": "Admin",
                "email": "username-admin@youshop.com",
                "passwordhash": admin_pw,
            }
        )

app.include_router(router, prefix="/api")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(sla_router)

# YouShop Chatbot endpoints
app.include_router(yshop_router)
app.include_router(yshop_admin_router)
