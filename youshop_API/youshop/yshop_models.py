from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from models import Base

class YShopProduct(Base):
    __tablename__ = "yshop_products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    brand = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(255))
    stock = Column(Integer, default=0)

class YShopOrder(Base):
    __tablename__ = "yshop_orders"
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(255), nullable=False)
    payment_method = Column(String(50), nullable=False)
    status = Column(String(30), default="Processing")
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("YShopOrderItem", back_populates="order")

class YShopOrderItem(Base):
    __tablename__ = "yshop_order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("yshop_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("yshop_products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    order = relationship("YShopOrder", back_populates="items")
    product = relationship("YShopProduct")

class YShopCartItem(Base):
    __tablename__ = "yshop_cart_items"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("yshop_products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    product = relationship("YShopProduct")
