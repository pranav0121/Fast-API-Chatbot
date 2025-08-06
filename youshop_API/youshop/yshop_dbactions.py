from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from .yshop_models import YShopProduct, YShopOrder, YShopOrderItem, YShopCartItem

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
async def place_order(db: AsyncSession, address: str, payment_method: str):
    cart_items = await get_cart(db)
    if not cart_items:
        return None
    order = YShopOrder(address=address, payment_method=payment_method)
    db.add(order)
    await db.flush()  # get order.id
    for item in cart_items:
        order_item = YShopOrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity)
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
