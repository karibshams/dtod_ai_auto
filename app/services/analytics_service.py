"""Service layer for analytics and dashboard operations."""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.models import (
    Order, Product, Vendor, Meeting, OrderItem,
    OrderStatus, MeetingStatus,
)


def get_dashboard_stats(db: Session) -> dict:
    """Return a combined summary for the dashboard."""
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_revenue = db.query(func.sum(Order.total_amount)).scalar() or 0.0
    pending_orders = (
        db.query(func.count(Order.id))
        .filter(Order.status == OrderStatus.PENDING)
        .scalar()
    ) or 0

    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_vendors = db.query(func.count(Vendor.id)).scalar() or 0
    active_vendors = (
        db.query(func.count(Vendor.id))
        .filter(Vendor.is_active == True)  # noqa: E712
        .scalar()
    ) or 0

    total_meetings = db.query(func.count(Meeting.id)).scalar() or 0
    from datetime import date as _date
    upcoming_meetings = (
        db.query(func.count(Meeting.id))
        .filter(
            Meeting.meeting_date >= _date.today(),
            Meeting.status == MeetingStatus.SCHEDULED,
        )
        .scalar()
    ) or 0

    return {
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "revenue": round(total_revenue, 2),
        },
        "products": {
            "total": total_products,
        },
        "vendors": {
            "total": total_vendors,
            "active": active_vendors,
        },
        "meetings": {
            "total": total_meetings,
            "upcoming": upcoming_meetings,
        },
    }


def get_revenue_by_month(db: Session) -> list[dict]:
    """Return monthly revenue figures."""
    rows = (
        db.query(
            extract("year", Order.created_at).label("year"),
            extract("month", Order.created_at).label("month"),
            func.sum(Order.total_amount).label("revenue"),
        )
        .group_by(
            extract("year", Order.created_at),
            extract("month", Order.created_at),
        )
        .order_by(
            extract("year", Order.created_at),
            extract("month", Order.created_at),
        )
        .all()
    )
    return [
        {
            "year": int(row.year),
            "month": int(row.month),
            "revenue": round(float(row.revenue or 0), 2),
        }
        for row in rows
    ]


def get_top_products(db: Session, limit: int = 10) -> list[dict]:
    """Return top products by total quantity sold."""
    rows = (
        db.query(
            Product.id,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity).label("total_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, Product.name, Product.category)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "product_id": row.id,
            "name": row.name,
            "category": row.category.value if hasattr(row.category, "value") else str(row.category),
            "total_sold": int(row.total_sold or 0),
            "total_revenue": round(float(row.total_revenue or 0), 2),
        }
        for row in rows
    ]


def get_top_vendors(db: Session, limit: int = 10) -> list[dict]:
    """Return top vendors by total revenue."""
    rows = (
        db.query(
            Vendor.id,
            Vendor.name,
            Vendor.company,
            func.sum(Order.total_amount).label("total_revenue"),
            func.count(Order.id).label("order_count"),
        )
        .join(Order, Order.vendor_id == Vendor.id)
        .group_by(Vendor.id, Vendor.name, Vendor.company)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "vendor_id": row.id,
            "name": row.name,
            "company": row.company,
            "total_revenue": round(float(row.total_revenue or 0), 2),
            "order_count": int(row.order_count or 0),
        }
        for row in rows
    ]
