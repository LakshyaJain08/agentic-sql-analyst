"""Synthetic e-commerce database generator and seeder."""

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import text

from app.database.connection import get_engine, init_database


# Deterministic seed for reproducible evaluation across runs
SEED_RANDOM = 42

REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["Consumer", "Corporate", "Small Business"]
ORDER_STATUSES = ["Completed", "Completed", "Completed", "Completed", "Completed", "Completed", "Cancelled", "Returned", "Processing"]
PAYMENT_METHODS = ["Credit Card", "PayPal", "Bank Transfer", "UPI"]

CITIES_BY_REGION = {
    "North": ["New York", "Boston", "Chicago", "Philadelphia"],
    "South": ["Atlanta", "Miami", "Dallas", "Houston", "Austin"],
    "East": ["Washington DC", "Baltimore", "Charlotte", "Richmond"],
    "West": ["Los Angeles", "San Francisco", "Seattle", "Denver", "Phoenix"],
    "Central": ["Minneapolis", "St. Louis", "Kansas City", "Indianapolis"]
}

PRODUCT_CATALOG = [
    # Electronics
    ("Apex Pro Smartphone 5G", "Electronics", 450.00, 799.00),
    ("UltraBook Slim 14 Laptop", "Electronics", 650.00, 1199.00),
    ("AcousticMax Wireless ANC Headphones", "Electronics", 90.00, 199.00),
    ("VisionCraft 27-inch 4K Monitor", "Electronics", 180.00, 349.00),
    ("PulseTrack Smartwatch Pro", "Electronics", 75.00, 149.00),
    ("KeyFlow Mechanical Wireless Keyboard", "Electronics", 45.00, 89.00),
    # Apparel
    ("Heritage Leather Bomber Jacket", "Apparel", 85.00, 189.00),
    ("Classic Comfort Denim Jeans", "Apparel", 22.00, 59.00),
    ("Organic Cotton Crew T-Shirt 3-Pack", "Apparel", 12.00, 34.00),
    ("AeroStride Breathable Running Shoes", "Apparel", 40.00, 110.00),
    ("Merino Wool Winter Sweater", "Apparel", 35.00, 79.00),
    ("StormShield Waterproof Raincoat", "Apparel", 45.00, 99.00),
    # Home & Kitchen
    ("BaristaTouch Espresso Machine", "Home & Kitchen", 220.00, 499.00),
    ("CrispAir Digital Air Fryer XL", "Home & Kitchen", 55.00, 129.00),
    ("ChefMaster 10-Piece Stainless Cookware", "Home & Kitchen", 110.00, 249.00),
    ("RoboClean Laser Smart Vacuum", "Home & Kitchen", 140.00, 299.00),
    ("NutriVortex High-Speed Blender", "Home & Kitchen", 48.00, 99.00),
    ("Damascus Steel 8-inch Chef Knife", "Home & Kitchen", 32.00, 69.00),
    # Beauty
    ("HydraGlow Peptide Anti-Aging Serum", "Beauty", 14.00, 48.00),
    ("Ceramide Barrier Rich Moisturizer", "Beauty", 10.00, 32.00),
    ("Velvet Noir Eau de Parfum 50ml", "Beauty", 28.00, 85.00),
    ("Gentle Herbal Cleansing Foam", "Beauty", 7.00, 22.00),
    ("Invisible Zinc Mineral Sunscreen SPF 50", "Beauty", 9.00, 26.00),
    ("Argan & Rosehip Botanical Hair Oil", "Beauty", 11.00, 29.00),
    # Sports
    ("EcoGrip Non-Slip Pro Yoga Mat", "Sports", 18.00, 45.00),
    ("PowerFit 5-Level Resistance Bands Set", "Sports", 8.00, 24.00),
    ("Apex Trail Hardtail Mountain Bike", "Sports", 320.00, 699.00),
    ("FlexWeight Adjustable Dumbbell Set 50lb", "Sports", 110.00, 229.00),
    ("ProTour Graphite Tennis Racket", "Sports", 55.00, 139.00),
    ("AlpineShelter 4-Person Waterproof Tent", "Sports", 95.00, 199.00),
    # Books
    ("Designing Data-Intensive Applications", "Books", 18.00, 42.00),
    ("The Pragmatic Programmer (20th Anniv)", "Books", 20.00, 45.00),
    ("Principles of Modern Economics", "Books", 25.00, 55.00),
    ("Deep Learning with PyTorch", "Books", 22.00, 49.00),
    ("Atomic Habits & Executive Focus", "Books", 11.00, 25.00),
    ("Clean Architecture in Practice", "Books", 17.00, 39.00)
]

CUSTOMER_FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "James", "Sophia", "Oliver", "Isabella", "Lucas",
    "Mia", "Benjamin", "Charlotte", "Ethan", "Amelia", "Henry", "Harper", "Alexander", "Evelyn", "Daniel",
    "Abigail", "Matthew", "Emily", "Jackson", "Elizabeth", "Sebastian", "Sofia", "David", "Avery", "Carter",
    "Ella", "Wyatt", "Scarlett", "Jayden", "Grace", "John", "Chloe", "Owen", "Camila", "Dylan",
    "Penelope", "Luke", "Riley", "Gabriel", "Layla", "Anthony", "Lillian", "Isaac", "Nora", "Grayson"
]

CUSTOMER_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]


def seed_database(force_reseed: bool = False) -> dict:
    """Generate and insert realistic synthetic data for e-commerce analytics."""
    random.seed(SEED_RANDOM)
    init_database()
    engine = get_engine()

    with engine.connect() as conn:
        customer_count = conn.execute(text("SELECT COUNT(*) FROM customers")).scalar() or 0
        if customer_count > 0 and not force_reseed:
            order_count = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar() or 0
            item_count = conn.execute(text("SELECT COUNT(*) FROM order_items")).scalar() or 0
            product_count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar() or 0
            return {
                "status": "already_seeded",
                "customers": customer_count,
                "products": product_count,
                "orders": order_count,
                "order_items": item_count
            }

    # 1. Generate Customers (60 customers)
    customers_data = []
    start_signup = datetime(2023, 1, 1)
    end_signup = datetime(2024, 6, 30)
    signup_days_span = (end_signup - start_signup).days

    for i in range(1, 61):
        first = CUSTOMER_FIRST_NAMES[(i - 1) % len(CUSTOMER_FIRST_NAMES)]
        last = CUSTOMER_LAST_NAMES[(i * 3) % len(CUSTOMER_LAST_NAMES)]
        full_name = f"{first} {last}"
        region = REGIONS[i % len(REGIONS)]
        city = random.choice(CITIES_BY_REGION[region])
        signup_date = (start_signup + timedelta(days=random.randint(0, signup_days_span))).strftime("%Y-%m-%d")
        segment = random.choices(SEGMENTS, weights=[0.60, 0.25, 0.15])[0]
        customers_data.append({
            "customer_id": i,
            "name": full_name,
            "city": city,
            "region": region,
            "signup_date": signup_date,
            "segment": segment
        })

    # 2. Generate Products (36 items)
    products_data = []
    for i, (name, category, cost, retail) in enumerate(PRODUCT_CATALOG, 1):
        products_data.append({
            "product_id": i,
            "product_name": name,
            "category": category,
            "cost_price": float(cost),
            "retail_price": float(retail)
        })

    # 3. Generate Orders & Order Items (650 orders from 2024-01-01 to 2025-12-31)
    orders_data = []
    order_items_data = []
    order_start = datetime(2024, 1, 1)
    order_end = datetime(2025, 12, 31)
    total_order_days = (order_end - order_start).days

    order_item_id_counter = 1

    for order_id in range(1, 651):
        customer = random.choice(customers_data)
        cust_signup = datetime.strptime(customer["signup_date"], "%Y-%m-%d")
        
        # Order date must be on or after customer signup date
        earliest_order = max(order_start, cust_signup)
        day_offset = random.randint(0, max(1, (order_end - earliest_order).days))
        order_date_dt = earliest_order + timedelta(days=day_offset)
        order_date = order_date_dt.strftime("%Y-%m-%d")

        # Status distribution: ~80% Completed, ~8% Cancelled, ~7% Returned, ~5% Processing
        status = random.choices(
            ["Completed", "Cancelled", "Returned", "Processing"],
            weights=[0.80, 0.08, 0.07, 0.05]
        )[0]
        payment_method = random.choice(PAYMENT_METHODS)

        orders_data.append({
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "order_date": order_date,
            "status": status,
            "payment_method": payment_method
        })

        # Number of distinct products in this order: 1 to 4
        num_items = random.choices([1, 2, 3, 4], weights=[0.45, 0.35, 0.15, 0.05])[0]
        selected_products = random.sample(products_data, num_items)

        for prod in selected_products:
            qty = random.choices([1, 2, 3, 4, 5], weights=[0.60, 0.25, 0.08, 0.05, 0.02])[0]
            # Baseline retail price with occasional small promotional variance
            retail = prod["retail_price"]
            # Realistic discount: 0% (most common), 5%, 10%, 15%, 20%
            discount = random.choices([0.0, 0.05, 0.10, 0.15, 0.20], weights=[0.55, 0.15, 0.15, 0.10, 0.05])[0]

            order_items_data.append({
                "order_item_id": order_item_id_counter,
                "order_id": order_id,
                "product_id": prod["product_id"],
                "quantity": qty,
                "unit_price": retail,
                "discount": discount
            })
            order_item_id_counter += 1

    # Insert into database using transactional connection
    with engine.begin() as conn:
        # Clear existing if force_reseed
        if force_reseed:
            conn.execute(text("DELETE FROM order_items;"))
            conn.execute(text("DELETE FROM orders;"))
            conn.execute(text("DELETE FROM products;"))
            conn.execute(text("DELETE FROM customers;"))

        # Insert Customers
        for c in customers_data:
            conn.execute(text("""
                INSERT INTO customers (customer_id, name, city, region, signup_date, segment)
                VALUES (:customer_id, :name, :city, :region, :signup_date, :segment)
            """), c)

        # Insert Products
        for p in products_data:
            conn.execute(text("""
                INSERT INTO products (product_id, product_name, category, cost_price)
                VALUES (:product_id, :product_name, :category, :cost_price)
            """), {"product_id": p["product_id"], "product_name": p["product_name"], "category": p["category"], "cost_price": p["cost_price"]})

        # Insert Orders
        for o in orders_data:
            conn.execute(text("""
                INSERT INTO orders (order_id, customer_id, order_date, status, payment_method)
                VALUES (:order_id, :customer_id, :order_date, :status, :payment_method)
            """), o)

        # Insert Order Items
        for item in order_items_data:
            conn.execute(text("""
                INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, discount)
                VALUES (:order_item_id, :order_id, :product_id, :quantity, :unit_price, :discount)
            """), item)

    # Also export SQL seed file for PostgreSQL Docker initialization
    export_sql_seed_file(customers_data, products_data, orders_data, order_items_data)

    return {
        "status": "seeded_successfully",
        "customers": len(customers_data),
        "products": len(products_data),
        "orders": len(orders_data),
        "order_items": len(order_items_data)
    }


def export_sql_seed_file(customers, products, orders, order_items):
    """Write sql/seed_data.sql for Docker container automated initialization."""
    sql_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "sql",
        "seed_data.sql"
    )
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("-- Seed Data for E-Commerce Analytics Database\n\n")
        f.write("-- Insert Customers\n")
        for c in customers:
            clean_name = c['name'].replace("'", "''")
            f.write(f"INSERT INTO customers (customer_id, name, city, region, signup_date, segment) VALUES ({c['customer_id']}, '{clean_name}', '{c['city']}', '{c['region']}', '{c['signup_date']}', '{c['segment']}') ON CONFLICT (customer_id) DO NOTHING;\n")

        f.write("\n-- Insert Products\n")
        for p in products:
            clean_pname = p['product_name'].replace("'", "''")
            f.write(f"INSERT INTO products (product_id, product_name, category, cost_price) VALUES ({p['product_id']}, '{clean_pname}', '{p['category']}', {p['cost_price']}) ON CONFLICT (product_id) DO NOTHING;\n")

        f.write("\n-- Insert Orders\n")
        for o in orders:
            f.write(f"INSERT INTO orders (order_id, customer_id, order_date, status, payment_method) VALUES ({o['order_id']}, {o['customer_id']}, '{o['order_date']}', '{o['status']}', '{o['payment_method']}') ON CONFLICT (order_id) DO NOTHING;\n")

        f.write("\n-- Insert Order Items\n")
        for it in order_items:
            f.write(f"INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, discount) VALUES ({it['order_item_id']}, {it['order_id']}, {it['product_id']}, {it['quantity']}, {it['unit_price']}, {it['discount']}) ON CONFLICT (order_item_id) DO NOTHING;\n")


if __name__ == "__main__":
    result = seed_database(force_reseed=True)
    print(f"Seeding completed: {result}")
