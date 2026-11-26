"""
Seed script for Dress 2 Decor e-commerce database.
Generates ~500 realistic but fictional records for demo / development.

Usage:
    python seed_data.py
"""

import random
import sys
from datetime import datetime, timedelta, date

from faker import Faker

# ── Deterministic seeds ──────────────────────────────────────────
random.seed(42)
Faker.seed(42)
fake = Faker()

# ── App imports ──────────────────────────────────────────────────
from app.core.database import engine, SessionLocal, init_db, Base
from app.models.models import (
    Customer,
    Vendor,
    Product,
    Order,
    OrderItem,
    Payment,
    Delivery,
    Meeting,
    OrderStatus,
    PaymentStatus,
    MeetingStatus,
    ProductCategory,
)


# ── Realistic product names per category ─────────────────────────

PRODUCT_NAMES = {
    ProductCategory.CURTAINS: [
        "Velvet Blackout Curtains",
        "Sheer Linen Drapes",
        "Thermal Insulated Curtains",
        "Embroidered Silk Curtains",
        "Cotton Tab-Top Curtains",
        "Jacquard Damask Curtains",
        "Grommet Panel Curtains",
        "Pinch Pleat Velvet Drapes",
        "Floral Print Curtains",
        "Ombre Gradient Curtains",
        "Woven Stripe Curtains",
        "Moroccan Lattice Curtains",
        "Room Darkening Curtains",
    ],
    ProductCategory.BLINDS: [
        "Bamboo Roman Blinds",
        "Faux Wood Venetian Blinds",
        "Cordless Cellular Shades",
        "Motorised Roller Blinds",
        "Wooden Slat Blinds",
        "Blackout Roller Blinds",
        "Pleated Day-Night Blinds",
        "Aluminium Mini Blinds",
        "Vertical Fabric Blinds",
        "Woven Wood Shades",
        "Solar Screen Blinds",
        "Top-Down Bottom-Up Shades",
    ],
    ProductCategory.WALLPAPER: [
        "Botanical Garden Wallpaper",
        "Geometric Peel & Stick Wallpaper",
        "Textured Grasscloth Wallpaper",
        "Vintage Floral Wallpaper",
        "Art Deco Metallic Wallpaper",
        "Brick Effect Wallpaper",
        "Tropical Leaf Wallpaper",
        "Damask Heritage Wallpaper",
        "Marble Effect Wallpaper",
        "Abstract Watercolour Wallpaper",
        "Linen Texture Wallpaper",
        "Nordic Minimalist Wallpaper",
        "3D Embossed Panel Wallpaper",
    ],
    ProductCategory.RUGS: [
        "Hand-Knotted Persian Rug",
        "Shaggy Faux Fur Area Rug",
        "Flatweave Kilim Runner",
        "Jute Braided Round Rug",
        "Moroccan Berber Rug",
        "Wool Herringbone Rug",
        "Vintage Distressed Rug",
        "Tufted Cotton Dhurrie",
        "Sisal Natural Fibre Rug",
        "Geometric Pattern Area Rug",
        "Outdoor Indoor Polypropylene Rug",
        "Handloom Silk Rug",
    ],
    ProductCategory.CUSHIONS: [
        "Velvet Throw Pillow",
        "Embroidered Boho Cushion",
        "Linen Lumbar Pillow",
        "Faux Fur Accent Cushion",
        "Block Print Cotton Cushion",
        "Knitted Cable Throw Pillow",
        "Silk Ikat Cushion Cover",
        "Outdoor Waterproof Cushion",
        "Tasselled Corner Cushion",
        "Round Floor Cushion",
        "Patchwork Quilted Pillow",
        "Leather Accent Cushion",
    ],
    ProductCategory.LIGHTING: [
        "Rattan Pendant Light",
        "Crystal Chandelier",
        "Industrial Table Lamp",
        "Brass Arc Floor Lamp",
        "Ceramic Bedside Lamp",
        "Woven Basket Pendant",
        "LED Strip Light Kit",
        "Stained Glass Tiffany Lamp",
        "Scandinavian Wooden Desk Lamp",
        "Moroccan Lantern Pendant",
        "Smart RGB Bulb Pack",
        "Minimalist Wall Sconce",
        "Paper Globe Pendant Light",
    ],
    ProductCategory.FURNITURE: [
        "Mid-Century Console Table",
        "Rattan Accent Chair",
        "Marble Top Side Table",
        "Modular Bookshelf Unit",
        "Upholstered Ottoman",
        "Solid Oak Coffee Table",
        "Floating Wall Shelf Set",
        "Velvet Bench Seat",
        "Nesting Tables Set of 3",
        "Wicker Storage Basket",
        "Teak Entryway Bench",
        "Glass Display Cabinet",
        "Live Edge Wood Shelf",
    ],
    ProductCategory.ACCESSORIES: [
        "Macramé Wall Hanging",
        "Ceramic Vase Set",
        "Scented Soy Candle Trio",
        "Decorative Mirror Frame",
        "Brass Candle Holder",
        "Woven Throw Blanket",
        "Photo Frame Gallery Set",
        "Artificial Eucalyptus Stems",
        "Clock Wall Art",
        "Marble Bookend Pair",
        "Incense Holder Tray",
        "Terracotta Planter Pot",
    ],
}

CATEGORY_SKU_PREFIX = {
    ProductCategory.CURTAINS: "CUR",
    ProductCategory.BLINDS: "BLD",
    ProductCategory.WALLPAPER: "WLP",
    ProductCategory.RUGS: "RUG",
    ProductCategory.CUSHIONS: "CSH",
    ProductCategory.LIGHTING: "LGT",
    ProductCategory.FURNITURE: "FRN",
    ProductCategory.ACCESSORIES: "ACC",
}

VENDOR_COMPANIES = [
    "Luxe Fabrics Co",
    "Modern Blinds Ltd",
    "Artisan Rugs Studio",
    "GreenLeaf Wallpapers",
    "Cozy Cushion Works",
    "Bright Homes Lighting",
    "Timber & Stone Furniture",
    "Décor Essentials Inc",
    "Silk Road Textiles",
    "Urban Nest Interiors",
    "Heritage Weaves",
    "CasaBlanca Home",
    "Nordic Living Co",
    "Sunrise Drapery",
    "EcoHome Accessories",
]

MEETING_TYPES = [
    ("Vendor Onboarding: {}", "New vendor onboarding session for {}"),
    ("Product Review: {}", "Quarterly product line review with {}"),
    ("Customer Consultation: {}", "Design consultation for {}"),
    ("Team Meeting: {}", "Internal team sync – {}"),
    ("Quality Inspection: {}", "Product quality check for {}"),
    ("Marketing Strategy: {}", "Campaign planning – {}"),
]

CARRIERS = ["FedEx", "UPS", "DHL", "Local Courier"]
PAYMENT_METHODS = ["credit_card", "bank_transfer", "cash"]


# ═════════════════════════════════════════════════════════════════
# Generator functions
# ═════════════════════════════════════════════════════════════════


def create_customers(session, n: int = 50):
    """Create n Customer rows."""
    print(f"  Creating {n} customers …")
    customers = []
    for _ in range(n):
        c = Customer(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            address=fake.street_address(),
            city=fake.city(),
            created_at=fake.date_time_between(start_date="-1y", end_date="now"),
        )
        customers.append(c)
    session.add_all(customers)
    session.flush()
    return customers


def create_vendors(session, n: int = 15):
    """Create n Vendor rows with home-décor themed company names."""
    print(f"  Creating {n} vendors …")
    vendors = []
    for i in range(n):
        v = Vendor(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],
            company=VENDOR_COMPANIES[i % len(VENDOR_COMPANIES)],
            commission_rate=round(random.uniform(10, 20), 1),
            is_active=True,
            joined_at=fake.date_time_between(start_date="-2y", end_date="-3M"),
        )
        vendors.append(v)
    session.add_all(vendors)
    session.flush()
    return vendors


def create_products(session, vendors, n: int = 100):
    """Create n Product rows spread across all 8 categories."""
    print(f"  Creating {n} products …")
    categories = list(ProductCategory)
    # Track counter per category for SKU numbering
    sku_counters = {cat: 0 for cat in categories}
    products = []

    for i in range(n):
        cat = categories[i % len(categories)]
        names_pool = PRODUCT_NAMES[cat]
        # Cycle through the name pool, adding colour/size suffix for uniqueness
        base_name = names_pool[i // len(categories) % len(names_pool)]
        suffix = ""
        if i // len(categories) >= len(names_pool):
            suffix = f" - {fake.color_name()}"
        product_name = base_name + suffix

        sku_counters[cat] += 1
        sku = f"{CATEGORY_SKU_PREFIX[cat]}-{sku_counters[cat]:03d}"

        p = Product(
            name=product_name,
            description=fake.sentence(nb_words=12),
            category=cat,
            price=round(random.uniform(15, 500), 2),
            stock=random.randint(0, 200),
            sku=sku,
            vendor_id=random.choice(vendors).id,
            is_active=random.random() > 0.05,  # 95 % active
            created_at=fake.date_time_between(start_date="-1y", end_date="now"),
        )
        products.append(p)
    session.add_all(products)
    session.flush()
    return products


def create_orders_items_payments_deliveries(
    session, customers, vendors, products,
    n_orders: int = 200,
):
    """Create orders, order-items, payments, and deliveries."""
    print(f"  Creating {n_orders} orders with items, payments & deliveries …")

    # Realistic status distribution weights
    status_weights = {
        OrderStatus.DELIVERED: 40,
        OrderStatus.SHIPPED: 20,
        OrderStatus.PROCESSING: 15,
        OrderStatus.CONFIRMED: 8,
        OrderStatus.PENDING: 10,
        OrderStatus.CANCELLED: 5,
        OrderStatus.RETURNED: 2,
    }
    statuses = list(status_weights.keys())
    weights = list(status_weights.values())

    orders = []
    all_items = []
    payments = []
    deliveries = []

    for i in range(1, n_orders + 1):
        status = random.choices(statuses, weights=weights, k=1)[0]
        customer = random.choice(customers)
        vendor = random.choice(vendors)
        order_date = fake.date_time_between(start_date="-6M", end_date="now")

        order = Order(
            order_number=f"ORD-{i:03d}",
            customer_id=customer.id,
            vendor_id=vendor.id,
            status=status,
            total_amount=0.0,  # will be updated below
            shipping_address=fake.address().replace("\n", ", "),
            notes=fake.sentence() if random.random() > 0.6 else None,
            created_at=order_date,
            updated_at=order_date + timedelta(hours=random.randint(1, 72)),
        )
        session.add(order)
        session.flush()  # get order.id

        # 1-4 items per order
        num_items = random.randint(1, 4)
        order_total = 0.0
        chosen_products = random.sample(products, min(num_items, len(products)))
        for prod in chosen_products:
            qty = random.randint(1, 5)
            unit_price = prod.price
            item = OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=qty,
                unit_price=unit_price,
            )
            all_items.append(item)
            order_total += qty * unit_price

        order.total_amount = round(order_total, 2)
        orders.append(order)

        # ── Payment (one per order) ──────────────────────────────
        if status in (OrderStatus.PENDING,):
            pay_status = PaymentStatus.PENDING
            paid_at = None
        elif status == OrderStatus.CANCELLED:
            pay_status = random.choice([PaymentStatus.REFUNDED, PaymentStatus.FAILED])
            paid_at = order_date + timedelta(hours=random.randint(1, 24))
        else:
            pay_status = PaymentStatus.PAID
            paid_at = order_date + timedelta(hours=random.randint(1, 24))

        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            method=random.choice(PAYMENT_METHODS),
            status=pay_status,
            transaction_id=fake.uuid4()[:12].upper() if pay_status == PaymentStatus.PAID else None,
            paid_at=paid_at,
        )
        payments.append(payment)

        # ── Delivery (skip cancelled & pending orders) ───────────
        if status not in (OrderStatus.CANCELLED, OrderStatus.PENDING):
            carrier = random.choice(CARRIERS)
            est = order_date.date() + timedelta(days=random.randint(3, 14))
            delivered_dt = est if status == OrderStatus.DELIVERED else None
            if status == OrderStatus.RETURNED:
                delivered_dt = est

            delivery_status = {
                OrderStatus.CONFIRMED: "pending",
                OrderStatus.PROCESSING: "pending",
                OrderStatus.SHIPPED: "in_transit",
                OrderStatus.DELIVERED: "delivered",
                OrderStatus.RETURNED: "delivered",
            }.get(status, "pending")

            delivery = Delivery(
                order_id=order.id,
                tracking_number=fake.bothify("???#########").upper(),
                carrier=carrier,
                estimated_date=est,
                delivered_date=delivered_dt,
                status=delivery_status,
            )
            deliveries.append(delivery)

    session.add_all(all_items)
    session.add_all(payments)
    session.add_all(deliveries)
    session.flush()

    return orders, all_items, payments, deliveries


def create_meetings(session, n: int = 30):
    """Create n Meeting rows spread over the next 30 days."""
    print(f"  Creating {n} meetings …")
    today = date.today()
    meetings = []
    for _ in range(n):
        mt_template = random.choice(MEETING_TYPES)
        topic = fake.bs().title()
        title = mt_template[0].format(topic)
        description = mt_template[1].format(topic)

        meeting_date = today + timedelta(days=random.randint(1, 30))
        start_hour = random.randint(9, 16)
        start_time = f"{start_hour:02d}:00"
        end_time = f"{start_hour + 1:02d}:00"

        m = Meeting(
            title=title[:200],
            description=description,
            organizer=fake.name(),
            attendees=", ".join(fake.name() for _ in range(random.randint(2, 5))),
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            location=random.choice([
                "Conference Room A",
                "Conference Room B",
                "Virtual – Zoom",
                "Virtual – Google Meet",
                "Main Office",
                "Showroom Floor",
            ]),
            status=MeetingStatus.SCHEDULED,
            created_at=datetime.utcnow(),
        )
        meetings.append(m)
    session.add_all(meetings)
    session.flush()
    return meetings


# ═════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Dress 2 Decor — Database Seeder")
    print("=" * 60)

    # Drop all tables & recreate (clean slate)
    print("\n[1/2] Dropping existing tables …")
    Base.metadata.drop_all(bind=engine)
    print("[2/2] Creating tables …")
    init_db()

    session = SessionLocal()
    try:
        print("\nGenerating seed data:\n")

        customers = create_customers(session, 50)
        vendors = create_vendors(session, 15)
        products = create_products(session, vendors, 100)
        orders, items, payments, deliveries = create_orders_items_payments_deliveries(
            session, customers, vendors, products, 200,
        )
        meetings = create_meetings(session, 30)

        session.commit()

        # ── Summary ──────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("  Seed data loaded successfully!")
        print("=" * 60)
        print(f"  Customers  : {len(customers)}")
        print(f"  Vendors    : {len(vendors)}")
        print(f"  Products   : {len(products)}")
        print(f"  Orders     : {len(orders)}")
        print(f"  Order Items: {len(items)}")
        print(f"  Payments   : {len(payments)}")
        print(f"  Deliveries : {len(deliveries)}")
        print(f"  Meetings   : {len(meetings)}")
        total = (
            len(customers) + len(vendors) + len(products)
            + len(orders) + len(items) + len(payments)
            + len(deliveries) + len(meetings)
        )
        print(f"  ─────────────────────────────")
        print(f"  Total rows : {total}")
        print("=" * 60)

    except Exception as exc:
        session.rollback()
        print(f"\n✖ Error seeding database: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
