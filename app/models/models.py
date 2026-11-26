"""SQLAlchemy models for Dress 2 Decor e-commerce system."""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, Date, ForeignKey, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


# ── Enums ────────────────────────────────────────────────────────

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class MeetingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProductCategory(str, enum.Enum):
    CURTAINS = "curtains"
    BLINDS = "blinds"
    WALLPAPER = "wallpaper"
    RUGS = "rugs"
    CUSHIONS = "cushions"
    LIGHTING = "lighting"
    FURNITURE = "furniture"
    ACCESSORIES = "accessories"


# ── Models ───────────────────────────────────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    city = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(20))
    company = Column(String(100))
    commission_rate = Column(Float, default=15.0)  # percentage
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="vendor")
    orders = relationship("Order", back_populates="vendor")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    category = Column(SAEnum(ProductCategory), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    sku = Column(String(30), unique=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(20), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float, default=0.0)
    shipping_address = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders")
    vendor = relationship("Vendor", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    payment = relationship("Payment", back_populates="order", uselist=False)
    delivery = relationship("Delivery", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String(30))  # credit_card, bank_transfer, cash
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    transaction_id = Column(String(50))
    paid_at = Column(DateTime)

    order = relationship("Order", back_populates="payment")


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    tracking_number = Column(String(50))
    carrier = Column(String(50))
    estimated_date = Column(Date)
    delivered_date = Column(Date)
    status = Column(String(30), default="pending")  # pending, in_transit, delivered

    order = relationship("Order", back_populates="delivery")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    organizer = Column(String(100))
    attendees = Column(Text)  # comma-separated
    meeting_date = Column(Date, nullable=False)
    start_time = Column(String(5), nullable=False)  # HH:MM
    end_time = Column(String(5), nullable=False)
    location = Column(String(200))
    status = Column(SAEnum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String(50), nullable=False)  # order_agent, vendor_agent, meeting_agent
    action = Column(String(100), nullable=False)
    details = Column(Text)
    user_query = Column(Text)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
