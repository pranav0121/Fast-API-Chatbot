from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from .yshop_schemas import ProductSearchResponse, CartResponse, OrderRequest, OrderResponse, OrderStatusResponse, MessageResponse
from .yshop_controller import (
    get_current_shop_customer,
    controller_search_products,
    controller_get_trending,
    controller_get_recommended,
    controller_get_product_details,
    controller_add_to_cart,
    controller_remove_from_cart,
    controller_view_cart,
    controller_place_order
)

router = APIRouter(
    prefix="/yshop",
    tags=["YouShop Chatbot"],
    dependencies=[Depends(get_current_shop_customer)]
)

# Product Discovery


@router.get("/products/search", response_model=ProductSearchResponse)
async def api_search_products(
    name: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    results = await controller_search_products(name, category, brand, db)
    return {"results": results}


@router.get("/products/trending", response_model=ProductSearchResponse)
async def api_trending_products(db: AsyncSession = Depends(get_db)):
    results = await controller_get_trending(db)
    return {"results": results}


@router.get("/products/recommended", response_model=ProductSearchResponse)
async def api_recommended_products(db: AsyncSession = Depends(get_db)):
    results = await controller_get_recommended(db)
    return {"results": results}

# Product Details


@router.get("/products/{product_id}", response_model=ProductSearchResponse)
async def api_product_details(product_id: int, db: AsyncSession = Depends(get_db)):
    product = await controller_get_product_details(product_id, db)
    return {"results": [product]}

# Cart Management


@router.post("/cart/add/{product_id}", response_model=CartResponse)
async def api_add_to_cart(product_id: int, db: AsyncSession = Depends(get_db)):
    cart_items = await controller_add_to_cart(product_id, db)
    return {"cart": [item.product for item in cart_items]}


@router.post("/cart/remove/{product_id}", response_model=CartResponse)
async def api_remove_from_cart(product_id: int, db: AsyncSession = Depends(get_db)):
    cart_items = await controller_remove_from_cart(product_id, db)
    return {"cart": [item.product for item in cart_items]}


@router.get("/cart", response_model=CartResponse)
async def api_view_cart(db: AsyncSession = Depends(get_db)):
    cart_items = await controller_view_cart(db)
    return {"cart": [item.product for item in cart_items]}

# Order Placement


@router.post("/order/place", response_model=OrderResponse)
async def api_place_order(
    order: OrderRequest,
    db: AsyncSession = Depends(get_db),
    current_customer=Depends(get_current_shop_customer)
):
    order_id = await controller_place_order(order, db, current_customer)
    return {"message": "Order placed", "order_id": order_id}
