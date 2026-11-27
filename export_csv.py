"""Export all Dress 2 Decor SQLite tables to separate CSV files in dataset_csv/."""

import csv
from pathlib import Path
from app.core.database import SessionLocal
from app.models.models import (
    Customer,
    Vendor,
    Product,
    Order,
    OrderItem,
    Payment,
    Delivery,
    Meeting,
)

EXPORT_DIR = Path(__file__).resolve().parent / "dataset_csv"

TABLES = [
    ("customers.csv", Customer),
    ("vendors.csv", Vendor),
    ("products.csv", Product),
    ("orders.csv", Order),
    ("order_items.csv", OrderItem),
    ("payments.csv", Payment),
    ("deliveries.csv", Delivery),
    ("meetings.csv", Meeting),
]


def export_all_to_csv():
    EXPORT_DIR.mkdir(exist_ok=True)
    db = SessionLocal()
    try:
        for filename, model in TABLES:
            rows = db.query(model).all()
            cols = [c.name for c in model.__table__.columns]
            out_path = EXPORT_DIR / filename
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(cols)
                for row in rows:
                    vals = []
                    for c in cols:
                        v = getattr(row, c)
                        if hasattr(v, "value"):
                            v = v.value
                        vals.append(v)
                    writer.writerow(vals)
            print(f"Exported {len(rows):>3} rows -> {out_path}")
    finally:
        db.close()


if __name__ == "__main__":
    export_all_to_csv()
