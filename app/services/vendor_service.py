"""Service layer for vendor operations."""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.models import Vendor, Product, Order, OrderItem, ProductCategory


def _vendor_to_dict(vendor: Vendor) -> dict:
    return {
        "id": vendor.id,
        "name": vendor.name,
        "email": vendor.email,
        "phone": vendor.phone,
        "company": vendor.company,
        "commission_rate": vendor.commission_rate,
        "is_active": vendor.is_active,
        "joined_at": vendor.joined_at.isoformat() if vendor.joined_at else None,
    }


def _product_to_dict(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "category": product.category.value if product.category else None,
        "price": product.price,
        "stock": product.stock,
        "sku": product.sku,
        "vendor_id": product.vendor_id,
        "is_active": product.is_active,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


def _order_summary_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "customer_name": order.customer.name if order.customer else None,
        "status": order.status.value if order.status else None,
        "total_amount": order.total_amount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def get_vendor_by_id(db: Session, vendor_id: int) -> dict:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if vendor is None:
        return None
    return _vendor_to_dict(vendor)


def get_vendor_by_email(db: Session, email: str) -> dict:
    vendor = db.query(Vendor).filter(Vendor.email == email).first()
    if vendor is None:
        return None
    return _vendor_to_dict(vendor)


def get_vendor_products(db: Session, vendor_id: int) -> list:
    products = (
        db.query(Product)
        .filter(Product.vendor_id == vendor_id)
        .order_by(Product.name)
        .all()
    )
    return [_product_to_dict(p) for p in products]


def get_vendor_orders(db: Session, vendor_id: int) -> list:
    orders = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(Order.vendor_id == vendor_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_order_summary_dict(o) for o in orders]


def get_vendor_commission_summary(db: Session, vendor_id: int) -> dict:
    """Calculate total sales and commission earned for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if vendor is None:
        return {"error": "Vendor not found"}

    total_sales = (
        db.query(func.sum(Order.total_amount))
        .filter(Order.vendor_id == vendor_id)
        .scalar()
    ) or 0.0

    commission_rate = vendor.commission_rate or 0.0
    commission_earned = round(total_sales * commission_rate / 100, 2)

    total_orders = (
        db.query(func.count(Order.id))
        .filter(Order.vendor_id == vendor_id)
        .scalar()
    ) or 0

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "commission_rate": commission_rate,
        "total_sales": round(total_sales, 2),
        "commission_earned": commission_earned,
        "total_orders": total_orders,
    }


def get_all_vendors(db: Session) -> list:
    vendors = db.query(Vendor).order_by(Vendor.name).all()
    return [_vendor_to_dict(v) for v in vendors]


def get_vendor_stats(db: Session) -> dict:
    """Aggregate vendor statistics."""
    total_vendors = db.query(func.count(Vendor.id)).scalar() or 0
    active_vendors = (
        db.query(func.count(Vendor.id))
        .filter(Vendor.is_active == True)  # noqa: E712
        .scalar()
    ) or 0

    avg_commission = db.query(func.avg(Vendor.commission_rate)).scalar()
    avg_commission = round(avg_commission, 2) if avg_commission else 0.0

    # Top vendor by revenue
    top_vendor_row = (
        db.query(Vendor.name, func.sum(Order.total_amount).label("revenue"))
        .join(Order, Order.vendor_id == Vendor.id)
        .group_by(Vendor.name)
        .order_by(func.sum(Order.total_amount).desc())
        .first()
    )

    return {
        "total_vendors": total_vendors,
        "active_vendors": active_vendors,
        "inactive_vendors": total_vendors - active_vendors,
        "average_commission_rate": avg_commission,
        "top_vendor": {
            "name": top_vendor_row[0],
            "revenue": round(top_vendor_row[1], 2),
        } if top_vendor_row else None,
    }
