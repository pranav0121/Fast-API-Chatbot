from pydantic import BaseModel
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
