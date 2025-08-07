from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from .yshop_dbactions import (
    search_products, get_trending_products, get_recommended_products, get_product_by_id,
    add_to_cart, remove_from_cart, get_cart, place_order, get_order_status,
    list_all_products, update_product, delete_product, import_products_csv, export_products_csv,
    get_admin_analytics, get_inventory_overview, activate_product,
    list_all_orders, get_order_details, update_order_status as update_order_status_admin,
    list_all_customers, list_shop_customers, export_shop_customers_csv, create_shop_customer
)
# Auth dependencies implemented directly in this controller (no yshop_utils)
from .yshop_schemas import (
    ProductSearchResponse, CartResponse, OrderRequest, OrderResponse, OrderStatusResponse,
    CSVUploadResponse, AnalyticsResponse, InventoryResponse, OrderOut,
    YShopCustomerCreate, YShopCustomerResponse
)
# Import shop customer actions
from .yshop_dbactions import create_shop_customer, authenticate_shop_customer
from .yshop_schemas import YShopCustomerLogin
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from db import get_db
from .yshop_models import YShopCustomer
from models import User as CoreUser

# JWT configuration for YouShop
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 schemes
oauth2_scheme_customer = OAuth2PasswordBearer(tokenUrl="/yshop/login")
oauth2_scheme_admin = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_shop_customer(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme_customer)
) -> YShopCustomer:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    result = await db.execute(select(YShopCustomer).where(YShopCustomer.email == email))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise credentials_exception
    return customer


async def get_current_shop_admin(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme_admin)
) -> CoreUser:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    result = await db.execute(select(CoreUser).where(CoreUser.email == email))
    user = result.scalar_one_or_none()
    if user is None or not getattr(user, "isadmin", False):
        raise HTTPException(
            status_code=403, detail="Admin privileges required")
    return user

# Public YouShop operations


async def controller_search_products(name: str, category: str, brand: str, db: AsyncSession):
    return await search_products(db, name, category, brand)


async def controller_get_trending(db: AsyncSession):
    return await get_trending_products(db)


async def controller_get_recommended(db: AsyncSession):
    return await get_recommended_products(db)


async def controller_get_product_details(product_id: int, db: AsyncSession):
    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


async def controller_add_to_cart(product_id: int, db: AsyncSession):
    success = await add_to_cart(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return await get_cart(db)


async def controller_remove_from_cart(product_id: int, db: AsyncSession):
    success = await remove_from_cart(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not in cart")
    return await get_cart(db)


async def controller_view_cart(db: AsyncSession):
    return await get_cart(db)


async def controller_place_order(order: OrderRequest, db: AsyncSession, current_customer):
    order_id = await place_order(db, order.address, order.payment_method, current_customer.id)
    if not order_id:
        raise HTTPException(status_code=400, detail="Cart is empty")
    return order_id

# Admin YouShop operations


async def controller_list_products(db: AsyncSession):
    return await list_all_products(db)


async def controller_update_product(product_id: int, payload, db: AsyncSession):
    updated = await update_product(db, product_id, payload)
    if not updated:
        raise HTTPException(404, detail="Product not found or not updated")
    return updated


async def controller_delete_product(product_id: int, db: AsyncSession):
    success = await delete_product(db, product_id)
    if not success:
        raise HTTPException(404, detail="Product not found")
    return success


async def controller_import_products(file, db: AsyncSession):
    return await import_products_csv(db, file)


async def controller_export_products(db: AsyncSession):
    return await export_products_csv(db)


async def controller_analytics(db: AsyncSession):
    return await get_admin_analytics(db)


async def controller_inventory(db: AsyncSession):
    return await get_inventory_overview(db)


async def controller_activate_product(product_id: int, active: bool, db: AsyncSession):
    success = await activate_product(db, product_id, active)
    if not success:
        raise HTTPException(404, detail="Product not found")
    return success


async def controller_list_orders(db: AsyncSession):
    return await list_all_orders(db)


async def controller_order_details(order_id: int, db: AsyncSession):
    order = await get_order_details(db, order_id)
    if not order:
        raise HTTPException(404, detail="Order not found")
    return order


async def controller_update_order_status(order_id: int, status: str, db: AsyncSession):
    updated = await update_order_status_admin(db, order_id, status)
    if not updated:
        raise HTTPException(
            404, detail="Order not found or status not updated")
    return updated


async def controller_list_customers(db: AsyncSession):
    return await list_all_customers(db)


async def controller_list_shop_customers(db: AsyncSession):
    return await list_shop_customers(db)


async def controller_export_shop_customers(db: AsyncSession):
    return await export_shop_customers_csv(db)


async def controller_create_shop_customer(payload: YShopCustomerCreate, db: AsyncSession):
    return await create_shop_customer(db, payload)


async def controller_authenticate_shop_customer(payload: YShopCustomerLogin, db: AsyncSession):
    """Authenticate a YouShop customer and return a JWT token."""
    token = await authenticate_shop_customer(db, payload)
    if not token:
        raise HTTPException(
            status_code=401, detail="Invalid email or password")
    return token
