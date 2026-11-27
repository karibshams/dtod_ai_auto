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


def get_revenue_by_category(db: Session) -> list[dict]:
    """Return gross revenue and units sold grouped by product category."""
    rows = (
        db.query(
            Product.category,
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.category)
        .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
        .all()
    )
    return [
        {
            "category": r.category.value if hasattr(r.category, "value") else str(r.category),
            "units_sold": int(r.units_sold or 0),
            "revenue": round(float(r.revenue or 0), 2),
            "order_count": int(r.order_count or 0),
        }
        for r in rows
    ]


def get_low_stock_products(db: Session, threshold: int = 15) -> list[dict]:
    """Return active products whose stock is at or below threshold."""
    rows = (
        db.query(Product)
        .filter(Product.is_active == True, Product.stock <= threshold)  # noqa: E712
        .order_by(Product.stock.asc())
        .limit(20)
        .all()
    )
    return [
        {
            "product_id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category.value if hasattr(p.category, "value") else str(p.category),
            "stock": p.stock,
            "price": round(float(p.price), 2),
            "vendor_id": p.vendor_id,
        }
        for p in rows
    ]


def get_vendor_performance_report(db: Session) -> list[dict]:
    """Return per-vendor orders, delivered/cancelled counts, sales, and platform commission."""
    vendors = db.query(Vendor).all()
    report = []
    for v in vendors:
        orders = db.query(Order).filter(Order.vendor_id == v.id).all()
        total_orders = len(orders)
        delivered = sum(1 for o in orders if o.status == OrderStatus.DELIVERED)
        cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        gross_sales = sum(float(o.total_amount or 0) for o in orders if o.status != OrderStatus.CANCELLED)
        commission_earned = gross_sales * (float(v.commission_rate or 0) / 100.0)
        report.append(
            {
                "vendor_id": v.id,
                "company": v.company,
                "name": v.name,
                "commission_rate": v.commission_rate,
                "total_orders": total_orders,
                "delivered_orders": delivered,
                "cancelled_orders": cancelled,
                "cancellation_rate_pct": round((cancelled / total_orders) * 100, 1) if total_orders else 0.0,
                "gross_sales": round(gross_sales, 2),
                "platform_commission_earned": round(commission_earned, 2),
            }
        )
    report.sort(key=lambda x: x["gross_sales"], reverse=True)
    return report


def get_payment_and_delivery_breakdown(db: Session) -> dict:
    """Return payment status/method breakdown and delivery carrier/status breakdown."""
    from app.models.models import Payment, Delivery

    pay_by_method = (
        db.query(Payment.method, func.count(Payment.id), func.sum(Payment.amount))
        .group_by(Payment.method)
        .all()
    )
    pay_by_status = (
        db.query(Payment.status, func.count(Payment.id), func.sum(Payment.amount))
        .group_by(Payment.status)
        .all()
    )
    deliv_by_carrier = (
        db.query(Delivery.carrier, Delivery.status, func.count(Delivery.id))
        .group_by(Delivery.carrier, Delivery.status)
        .all()
    )
    return {
        "payments_by_method": [
            {"method": m or "unknown", "count": int(c), "amount": round(float(a or 0), 2)}
            for m, c, a in pay_by_method
        ],
        "payments_by_status": [
            {
                "status": s.value if hasattr(s, "value") else str(s),
                "count": int(c),
                "amount": round(float(a or 0), 2),
            }
            for s, c, a in pay_by_status
        ],
        "deliveries_by_carrier": [
            {"carrier": car or "unknown", "status": st or "unknown", "count": int(c)}
            for car, st, c in deliv_by_carrier
        ],
    }


def get_top_customers(db: Session, limit: int = 10) -> list[dict]:
    """Return top customers by total spend and order count."""
    from app.models.models import Customer

    rows = (
        db.query(
            Customer.id,
            Customer.name,
            Customer.city,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_spent"),
        )
        .join(Order, Order.customer_id == Customer.id)
        .group_by(Customer.id, Customer.name, Customer.city)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "customer_id": r.id,
            "name": r.name,
            "city": r.city,
            "order_count": int(r.order_count or 0),
            "total_spent": round(float(r.total_spent or 0), 2),
        }
        for r in rows
    ]
