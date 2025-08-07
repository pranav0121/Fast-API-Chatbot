from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from .yshop_controller import (
    get_current_shop_admin,
    controller_list_products,
    controller_update_product,
    controller_delete_product,
    controller_import_products,
    controller_export_products,
    controller_analytics,
    controller_inventory,
    controller_activate_product,
    controller_list_orders,
    controller_order_details,
    controller_update_order_status,
    # mixed customers logic remains inline
    controller_list_shop_customers,
    controller_export_shop_customers,
    controller_create_shop_customer
)
from .yshop_schemas import (
    Product, ProductSearchResponse, CSVUploadResponse,
    AnalyticsResponse, InventoryResponse, OrderOut, CustomerMixed,
    YShopCustomerResponse, YShopCustomerCreate
)
from controller import log_user_activity

router = APIRouter(
    prefix="/yshop/admin",
    tags=["YouShop Admin"],
    dependencies=[Depends(get_current_shop_admin)]
)

# Product CRUD


@router.get("/products", response_model=ProductSearchResponse)
async def admin_list_products(db: AsyncSession = Depends(get_db)):
    products = await controller_list_products(db)
    return {"results": products}


@router.put("/products/{product_id}", response_model=Product)
async def admin_update_product(product_id: int, payload: Product, db: AsyncSession = Depends(get_db)):
    updated = await controller_update_product(product_id, payload, db)
    if not updated:
        raise HTTPException(404, "Product not found or not updated")
    return updated


@router.delete("/products/{product_id}", response_model=dict)
async def admin_delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    success = await controller_delete_product(product_id, db)
    if not success:
        raise HTTPException(404, "Product not found")
    return {"message": "Product deleted"}

# Bulk Import/Export


@router.post("/products/import", response_model=CSVUploadResponse)
async def admin_import_products(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    count = await controller_import_products(file, db)
    return {"imported": count}


@router.get("/products/export")
async def admin_export_products(db: AsyncSession = Depends(get_db)):
    csv_data = await controller_export_products(db)
    return Response(content=csv_data, media_type="text/csv")

# Analytics & Inventory


@router.get("/analytics", response_model=AnalyticsResponse)
async def admin_analytics(db: AsyncSession = Depends(get_db)):
    return await controller_analytics(db)


@router.get("/inventory", response_model=InventoryResponse)
async def admin_inventory(db: AsyncSession = Depends(get_db)):
    return await controller_inventory(db)

# Activate/Deactivate


@router.post("/products/{product_id}/activate", response_model=dict)
async def admin_activate_product(product_id: int, active: bool, db: AsyncSession = Depends(get_db)):
    success = await controller_activate_product(product_id, active, db)
    if not success:
        raise HTTPException(404, "Product not found")
    return {"message": f"Product {'activated' if active else 'deactivated'}"}

# Order Management


@router.get("/orders", response_model=List[OrderOut])
async def admin_list_orders(db: AsyncSession = Depends(get_db)):
    return await controller_list_orders(db)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def admin_order_details(order_id: int, db: AsyncSession = Depends(get_db)):
    order = await controller_order_details(order_id, db)
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.put("/orders/{order_id}/status", response_model=dict)
async def admin_update_order_status(order_id: int, status: str, db: AsyncSession = Depends(get_db)):
    updated = await controller_update_order_status(order_id, status, db)
    if not updated:
        raise HTTPException(404, "Order not found or status not updated")
    return {"message": f"Order status updated to {status}"}

# Customers


# Customers (mix of logged-in users and legacy addresses)
@router.get("/customers", response_model=List[CustomerMixed])
async def admin_list_customers(db: AsyncSession = Depends(get_db)):
    result: List[CustomerMixed] = []
    # 1. YouShop users who placed orders
    users = await list_all_customers(db)
    for u in users:
        result.append(CustomerMixed(
            userid=u.userid,
            name=u.name,
            email=u.email,
            address=None
        ))
    # 2. Legacy orders without user_id
    from .yshop_dbactions import list_legacy_addresses
    addresses = await list_legacy_addresses(db)
    for addr in addresses:
        result.append(CustomerMixed(
            userid=None,
            uuid=None,
            name=None,
            email=None,
            address=addr
        ))
    return result

# Shop-specific customer management


@router.get("/shop-customers", response_model=List[YShopCustomerResponse])
async def admin_list_shop_customers(db: AsyncSession = Depends(get_db)):
    # List all YouShop-specific customers
    return await controller_list_shop_customers(db)


@router.get("/shop-customers/export")
async def admin_export_shop_customers(db: AsyncSession = Depends(get_db)):
    csv_data = await controller_export_shop_customers(db)
    return Response(content=csv_data, media_type="text/csv")

# Create a new YouShop-specific customer


@router.post("/shop-customers", response_model=YShopCustomerResponse)
async def admin_create_shop_customer(
    payload: YShopCustomerCreate,
    db: AsyncSession = Depends(get_db)
):
    customer = await controller_create_shop_customer(payload, db)
    # Log the creation event
    log_user_activity(customer.email, "create_shop_customer",
                      f"id={customer.id}")
    return customer
