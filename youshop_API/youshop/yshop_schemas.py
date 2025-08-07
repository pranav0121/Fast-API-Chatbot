from datetime import datetime
from pydantic import BaseModel
from pydantic import BaseModel, EmailStr
from typing import List, Optional


class Product(BaseModel):
    id: int
    name: str
    category: str
    brand: str
    price: float
    description: str
    stock: int


class ProductSearchResponse(BaseModel):
    results: List[Product]


class CartItem(BaseModel):
    product_id: int
    quantity: int = 1


class CartResponse(BaseModel):
    cart: List[Product]


class OrderRequest(BaseModel):
    address: str
    payment_method: str


class OrderResponse(BaseModel):
    message: str
    order_id: int


class OrderStatusResponse(BaseModel):
    order_id: int
    status: str


class MessageResponse(BaseModel):
    message: str
    order_id: Optional[int] = None

# Admin schemas


class CSVUploadResponse(BaseModel):
    imported: int


class AnalyticsResponse(BaseModel):
    total_products: int
    total_orders: int
    total_revenue: float


class InventoryResponse(BaseModel):
    low_stock_count: int
    out_of_stock_count: int


class CustomerMixed(BaseModel):
    userid: Optional[int]
    name: Optional[str]
    email: Optional[str]
    address: Optional[str]

    class Config:
        from_attributes = True


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int


class OrderOut(BaseModel):
    id: int
    address: str
    payment_method: str
    status: str
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True

# YouShop-specific customer schemas


class YShopCustomerCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class YShopCustomerLogin(BaseModel):
    email: EmailStr
    password: str


class YShopCustomerResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
