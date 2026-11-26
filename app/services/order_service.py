"""Service layer for order operations."""

from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.models import (
    Order, OrderItem, Customer, Payment, Delivery,
    Product, Vendor, OrderStatus,
)


def _order_item_to_dict(item: OrderItem) -> dict:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": item.product.name if item.product else None,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "subtotal": round((item.unit_price or 0) * (item.quantity or 0), 2),
    }


def _payment_to_dict(payment):
    if payment is None:
        return None
    return {
        "id": payment.id,
        "amount": payment.amount,
        "method": payment.method,
        "status": payment.status.value if payment.status else None,
        "transaction_id": payment.transaction_id,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


def _delivery_to_dict(delivery):
    if delivery is None:
        return None
    return {
        "id": delivery.id,
        "tracking_number": delivery.tracking_number,
        "carrier": delivery.carrier,
        "estimated_date": delivery.estimated_date.isoformat() if delivery.estimated_date else None,
        "delivered_date": delivery.delivered_date.isoformat() if delivery.delivered_date else None,
        "status": delivery.status,
    }


def _order_to_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer": {
            "id": order.customer.id,
            "name": order.customer.name,
            "email": order.customer.email,
            "phone": order.customer.phone,
        } if order.customer else None,
        "vendor": {
            "id": order.vendor.id,
            "name": order.vendor.name,
            "company": order.vendor.company,
        } if order.vendor else None,
        "status": order.status.value if order.status else None,
        "total_amount": order.total_amount,
        "shipping_address": order.shipping_address,
        "notes": order.notes,
        "items": [_order_item_to_dict(i) for i in order.items] if order.items else [],
        "payment": _payment_to_dict(order.payment),
        "delivery": _delivery_to_dict(order.delivery),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


def _eager_order_query(db: Session):
    """Return a base query with all order relationships eagerly loaded."""
    return db.query(Order).options(
        joinedload(Order.customer),
        joinedload(Order.vendor),
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.payment),
        joinedload(Order.delivery),
    )


def get_order_by_number(db: Session, order_number: str) -> dict:
    """Return a single order with all related data, or None."""
    order = _eager_order_query(db).filter(Order.order_number == order_number).first()
    if order is None:
        return None
    return _order_to_dict(order)


def get_orders_by_customer_email(db: Session, email: str) -> list:
    """Return all orders belonging to a customer identified by email."""
    orders = (
        _eager_order_query(db)
        .join(Customer, Order.customer_id == Customer.id)
        .filter(Customer.email == email)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_order_to_dict(o) for o in orders]


def get_orders_by_status(db: Session, status: str) -> list:
    """Return orders filtered by status string (e.g. 'pending')."""
    orders = (
        _eager_order_query(db)
        .filter(Order.status == status)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_order_to_dict(o) for o in orders]


def get_recent_orders(db: Session, limit: int = 20) -> list:
    """Return the most recent orders."""
    orders = (
        _eager_order_query(db)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_order_to_dict(o) for o in orders]


def update_order_status(db: Session, order_number: str, new_status: str) -> dict:
    """Update an order's status and return the updated order dict."""
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if order is None:
        return None
    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    # Re-fetch with eager loading
    return get_order_by_number(db, order_number)


def get_order_stats(db: Session) -> dict:
    """Return aggregate order statistics."""
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_revenue = db.query(func.sum(Order.total_amount)).scalar() or 0.0

    status_counts = {}
    rows = (
        db.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .all()
    )
    for status, count in rows:
        key = status.value if hasattr(status, "value") else str(status)
        status_counts[key] = count

    avg_order_value = round(total_revenue / total_orders, 2) if total_orders else 0.0

    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "average_order_value": avg_order_value,
        "orders_by_status": status_counts,
    }
