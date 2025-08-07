from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .yshop_models import YShopProduct, YShopOrder, YShopOrderItem, YShopCartItem
from models import User as CoreUser
from fastapi import UploadFile
from sqlalchemy import func
# no core user import needed
import csv
from io import StringIO
from .yshop_models import YShopCustomer
from controller import get_password_hash, verify_password, create_access_token
from sqlalchemy import select

# Product DB actions


async def search_products(db: AsyncSession, name: Optional[str], category: Optional[str], brand: Optional[str]) -> List[YShopProduct]:
    query = select(YShopProduct)
    if name:
        query = query.where(YShopProduct.name.ilike(f"%{name}%"))
    if category:
        query = query.where(YShopProduct.category.ilike(f"%{category}%"))
    if brand:
        query = query.where(YShopProduct.brand.ilike(f"%{brand}%"))
    result = await db.execute(query)
    return result.scalars().all()


async def get_trending_products(db: AsyncSession) -> List[YShopProduct]:
    result = await db.execute(select(YShopProduct).limit(2))
    return result.scalars().all()


async def get_recommended_products(db: AsyncSession) -> List[YShopProduct]:
    result = await db.execute(select(YShopProduct).offset(1))
    return result.scalars().all()


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[YShopProduct]:
    result = await db.execute(select(YShopProduct).where(YShopProduct.id == product_id))
    return result.scalar_one_or_none()

# Cart DB actions


async def add_to_cart(db: AsyncSession, product_id: int, quantity: int = 1):
    product = await get_product_by_id(db, product_id)
    if not product:
        return False
    cart_item = await db.execute(select(YShopCartItem).where(YShopCartItem.product_id == product_id))
    cart_item = cart_item.scalar_one_or_none()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = YShopCartItem(product_id=product_id, quantity=quantity)
        db.add(cart_item)
    await db.commit()
    return True


async def remove_from_cart(db: AsyncSession, product_id: int):
    cart_item = await db.execute(select(YShopCartItem).where(YShopCartItem.product_id == product_id))
    cart_item = cart_item.scalar_one_or_none()
    if cart_item:
        await db.delete(cart_item)
        await db.commit()
        return True
    return False


async def get_cart(db: AsyncSession) -> List[YShopCartItem]:
    result = await db.execute(select(YShopCartItem).options(selectinload(YShopCartItem.product)))
    return result.scalars().all()

# Order DB actions


async def place_order(db: AsyncSession, address: str, payment_method: str, user_id: int):
    cart_items = await get_cart(db)
    if not cart_items:
        return None
    # Create order with associated user
    order = YShopOrder(
        address=address, payment_method=payment_method, user_id=user_id)
    db.add(order)
    await db.flush()  # get order.id
    for item in cart_items:
        order_item = YShopOrderItem(
            order_id=order.id, product_id=item.product_id, quantity=item.quantity)
        db.add(order_item)
    await db.execute(YShopCartItem.__table__.delete())  # clear cart
    await db.commit()
    return order.id


async def get_order_status(db: AsyncSession, order_id: int) -> Optional[str]:
    result = await db.execute(select(YShopOrder).where(YShopOrder.id == order_id))
    order = result.scalar_one_or_none()
    if order:
        return order.status
    return None

# Admin DB actions


async def list_all_products(db: AsyncSession) -> List[YShopProduct]:
    result = await db.execute(select(YShopProduct).where(YShopProduct.is_active == True))
    return result.scalars().all()


async def update_product(db: AsyncSession, product_id: int, data):
    product = await db.get(YShopProduct, product_id)
    if not product:
        return None
    for field, value in data.dict(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    product = await db.get(YShopProduct, product_id)
    if not product:
        return False
    await db.delete(product)
    await db.commit()
    return True


async def import_products_csv(db: AsyncSession, file: UploadFile) -> int:
    content = await file.read()
    reader = csv.DictReader(StringIO(content.decode()))
    count = 0
    for row in reader:
        product = YShopProduct(
            name=row.get('name'), category=row.get('category'), brand=row.get('brand'),
            price=float(row.get('price', 0)), description=row.get('description'),
            stock=int(row.get('stock', 0)), is_active=row.get('is_active', 'True') == 'True'
        )
        db.add(product)
        count += 1
    await db.commit()
    return count


async def export_products_csv(db: AsyncSession) -> str:
    products = await list_all_products(db)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'category', 'brand',
                    'price', 'description', 'stock', 'is_active'])
    for p in products:
        writer.writerow([p.id, p.name, p.category, p.brand,
                        p.price, p.description, p.stock, p.is_active])
    return output.getvalue()


async def get_admin_analytics(db: AsyncSession) -> dict:
    total_products = (await db.execute(select(func.count()).select_from(YShopProduct))).scalar_one()
    total_orders = (await db.execute(select(func.count()).select_from(YShopOrder))).scalar_one()
    revenue = 0.0
    return {'total_products': total_products, 'total_orders': total_orders, 'total_revenue': revenue}


async def get_inventory_overview(db: AsyncSession) -> dict:
    low_stock = (await db.execute(select(func.count()).where(YShopProduct.stock < 10))).scalar_one()
    out_of_stock = (await db.execute(select(func.count()).where(YShopProduct.stock == 0))).scalar_one()
    return {'low_stock_count': low_stock, 'out_of_stock_count': out_of_stock}


async def activate_product(db: AsyncSession, product_id: int, active: bool) -> bool:
    product = await db.get(YShopProduct, product_id)
    if not product:
        return False
    product.is_active = active
    await db.commit()
    return True


async def list_all_orders(db: AsyncSession) -> List[YShopOrder]:
    result = await db.execute(select(YShopOrder).options(selectinload(YShopOrder.items)))
    return result.scalars().all()


async def get_order_details(db: AsyncSession, order_id: int) -> Optional[YShopOrder]:
    # Eagerly load items to avoid IO during response validation
    result = await db.execute(
        select(YShopOrder)
        .options(selectinload(YShopOrder.items))
        .where(YShopOrder.id == order_id)
    )
    return result.scalar_one_or_none()


async def update_order_status(db: AsyncSession, order_id: int, status: str) -> bool:
    order = await db.get(YShopOrder, order_id)
    if not order:
        return False
    order.status = status
    await db.commit()
    return True


async def list_all_customers(db: AsyncSession) -> List[CoreUser]:
    # Return distinct users who have placed a YouShop order
    stmt = (select(CoreUser)
            .join(YShopOrder, CoreUser.userid == YShopOrder.user_id)
            .distinct())
    result = await db.execute(stmt)
    return result.scalars().all()


async def list_legacy_addresses(db: AsyncSession) -> List[str]:
    # Return addresses for orders with no user_id
    stmt = select(YShopOrder.address).where(
        YShopOrder.user_id == None).distinct()
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]

# YouShop Customer actions


async def create_shop_customer(db: AsyncSession, payload) -> YShopCustomer:
    hashed = get_password_hash(payload.password)
    customer = YShopCustomer(
        name=payload.name, email=payload.email, passwordhash=hashed)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


async def authenticate_shop_customer(db: AsyncSession, payload) -> Optional[str]:
    result = await db.execute(select(YShopCustomer).where(YShopCustomer.email == payload.email))
    cust = result.scalar_one_or_none()
    if not cust or not verify_password(payload.password, cust.passwordhash):
        return None
    # Include is_admin flag in token for admin routes
    token = create_access_token({
        "sub": cust.email,
        "cust_id": cust.id,
        "is_admin": cust.is_admin
    })
    return token


async def list_shop_customers(db: AsyncSession) -> List[YShopCustomer]:
    result = await db.execute(select(YShopCustomer))
    return result.scalars().all()


async def export_shop_customers_csv(db: AsyncSession) -> str:
    customers = await list_shop_customers(db)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'email', 'passwordhash', 'created_at'])
    for c in customers:
        writer.writerow([c.id, c.name, c.email, c.passwordhash, c.created_at])
    return output.getvalue()
