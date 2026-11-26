"""Service layer for product operations."""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from app.models.models import Product, Vendor, ProductCategory


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
        "vendor_name": product.vendor.name if product.vendor else None,
        "is_active": product.is_active,
        "created_at": product.created_at.isoformat() if product.created_at else None,
    }


def get_product_by_id(db: Session, product_id: int) -> dict:
    product = (
        db.query(Product)
        .options(joinedload(Product.vendor))
        .filter(Product.id == product_id)
        .first()
    )
    if product is None:
        return None
    return _product_to_dict(product)


def search_products(db: Session, query: str, category: str = None) -> list:
    """Search products by name/description with optional category filter."""
    q = db.query(Product).options(joinedload(Product.vendor))
    pattern = f"%{query}%"
    q = q.filter(
        or_(
            Product.name.ilike(pattern),
            Product.description.ilike(pattern),
        )
    )
    if category:
        q = q.filter(Product.category == category)
    products = q.order_by(Product.name).all()
    return [_product_to_dict(p) for p in products]


def get_products_by_category(db: Session, category: str) -> list:
    products = (
        db.query(Product)
        .options(joinedload(Product.vendor))
        .filter(Product.category == category)
        .order_by(Product.name)
        .all()
    )
    return [_product_to_dict(p) for p in products]


def get_all_products(db: Session, limit: int = 50) -> list:
    products = (
        db.query(Product)
        .options(joinedload(Product.vendor))
        .order_by(Product.name)
        .limit(limit)
        .all()
    )
    return [_product_to_dict(p) for p in products]


def get_product_stats(db: Session) -> dict:
    total = db.query(func.count(Product.id)).scalar() or 0

    # Count by category
    category_counts = {}
    rows = (
        db.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .all()
    )
    for cat, count in rows:
        key = cat.value if hasattr(cat, "value") else str(cat)
        category_counts[key] = count

    avg_price = db.query(func.avg(Product.price)).scalar()
    avg_price = round(avg_price, 2) if avg_price else 0.0

    total_stock = db.query(func.sum(Product.stock)).scalar() or 0

    active = (
        db.query(func.count(Product.id))
        .filter(Product.is_active == True)  # noqa: E712
        .scalar()
    ) or 0

    return {
        "total_products": total,
        "active_products": active,
        "products_by_category": category_counts,
        "average_price": avg_price,
        "total_stock": total_stock,
    }
