from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from .yshop_schemas import ProductSearchResponse, CartResponse, OrderRequest, OrderResponse, OrderStatusResponse, MessageResponse
from .yshop_dbactions import (
    search_products, get_trending_products, get_recommended_products, get_product_by_id,
    add_to_cart, remove_from_cart, get_cart, place_order, get_order_status
)

router = APIRouter(prefix="/yshop", tags=["YouShop Chatbot"])

# Product Discovery


@router.get("/products/search", response_model=ProductSearchResponse)
async def api_search_products(
    name: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    results = await search_products(db, name, category, brand)
    return {"results": results}


@router.get("/products/trending", response_model=ProductSearchResponse)
async def api_trending_products(db: AsyncSession = Depends(get_db)):
    results = await get_trending_products(db)
    return {"results": results}


@router.get("/products/recommended", response_model=ProductSearchResponse)
async def api_recommended_products(db: AsyncSession = Depends(get_db)):
    results = await get_recommended_products(db)
    return {"results": results}

# Product Details


@router.get("/products/{product_id}", response_model=ProductSearchResponse)
async def api_product_details(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await get_product_by_id(db, product_id)
    if product:
        return {"results": [product]}
    raise HTTPException(status_code=404, detail="Product not found")

# Cart Management


@router.post("/cart/add/{product_id}", response_model=CartResponse)
async def api_add_to_cart(product_id: int, db: AsyncSession = Depends(get_db)):
    success = await add_to_cart(db, product_id)
    if success:
        cart = await get_cart(db)
        return {"cart": [item.product for item in cart]}
    raise HTTPException(status_code=404, detail="Product not found")


@router.post("/cart/remove/{product_id}", response_model=CartResponse)
async def api_remove_from_cart(product_id: int, db: AsyncSession = Depends(get_db)):
    success = await remove_from_cart(db, product_id)
    if success:
        cart = await get_cart(db)
        return {"cart": [item.product for item in cart]}
    raise HTTPException(status_code=404, detail="Product not in cart")


@router.get("/cart", response_model=CartResponse)
async def api_view_cart(db: AsyncSession = Depends(get_db)):
    cart = await get_cart(db)
    return {"cart": [item.product for item in cart]}

# Order Placement


@router.post("/order/place", response_model=OrderResponse)
async def api_place_order(order: OrderRequest, db: AsyncSession = Depends(get_db)):
    order_id = await place_order(db, order.address, order.payment_method)
    if order_id:
        return {"message": "Order placed", "order_id": order_id}
    raise HTTPException(status_code=400, detail="Cart is empty")
