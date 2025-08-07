from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from .yshop_schemas import YShopCustomerCreate, YShopCustomerLogin, YShopCustomerResponse, CustomerTokenResponse
from .yshop_controller import controller_create_shop_customer, controller_authenticate_shop_customer

router = APIRouter(prefix="/yshop", tags=["YouShop Customers"])


@router.post("/register", response_model=YShopCustomerResponse)
async def yshop_register(
    payload: YShopCustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    # Create a new YouShop-specific customer
    return await controller_create_shop_customer(payload, db)


@router.post("/login", response_model=CustomerTokenResponse)
async def yshop_login(
    payload: YShopCustomerLogin,
    db: AsyncSession = Depends(get_db)
):
    token = await controller_authenticate_shop_customer(payload, db)
    return {"access_token": token, "token_type": "bearer"}
