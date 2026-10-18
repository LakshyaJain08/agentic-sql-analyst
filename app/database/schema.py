"""Database schema definitions, metadata, and business data dictionary."""

from typing import Dict, List, Any

# Approved table allowlist for security
APPROVED_TABLES = {"customers", "orders", "order_items", "products"}

# Relational Schema Definition
SCHEMA_DEFINITION = {
    "customers": {
        "description": "Information about customers including location and market segment.",
        "columns": {
            "customer_id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for customer"},
            "name": {"type": "VARCHAR(100)", "description": "Customer full name"},
            "city": {"type": "VARCHAR(100)", "description": "City of residence"},
            "region": {"type": "VARCHAR(50)", "description": "Geographic region (North, South, East, West, Central)"},
            "signup_date": {"type": "DATE", "description": "Date when customer created an account"},
            "segment": {"type": "VARCHAR(50)", "description": "Customer category: 'Consumer', 'Corporate', 'Small Business'"}
        }
    },
    "products": {
        "description": "Catalog of products offered, their category, and cost price.",
        "columns": {
            "product_id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for product"},
            "product_name": {"type": "VARCHAR(150)", "description": "Name of the product"},
            "category": {"type": "VARCHAR(50)", "description": "Product category: 'Electronics', 'Apparel', 'Home & Kitchen', 'Beauty', 'Sports', 'Books'"},
            "cost_price": {"type": "NUMERIC(10, 2)", "description": "Cost to acquire or manufacture the product"}
        }
    },
    "orders": {
        "description": "Orders placed by customers, their fulfillment status, and payment method.",
        "columns": {
            "order_id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for order"},
            "customer_id": {"type": "INTEGER", "foreign_key": "customers.customer_id", "description": "Customer who placed the order"},
            "order_date": {"type": "DATE", "description": "Date when the order was placed"},
            "status": {"type": "VARCHAR(30)", "description": "Order lifecycle status: 'Completed', 'Cancelled', 'Returned', 'Processing'"},
            "payment_method": {"type": "VARCHAR(50)", "description": "Method of payment: 'Credit Card', 'PayPal', 'Bank Transfer', 'UPI'"}
        }
    },
    "order_items": {
        "description": "Line items belonging to an order with historical unit price and applied discount at sale time.",
        "columns": {
            "order_item_id": {"type": "INTEGER", "primary_key": True, "description": "Unique identifier for order line item"},
            "order_id": {"type": "INTEGER", "foreign_key": "orders.order_id", "description": "Parent order ID"},
            "product_id": {"type": "INTEGER", "foreign_key": "products.product_id", "description": "Purchased product ID"},
            "quantity": {"type": "INTEGER", "description": "Number of units ordered"},
            "unit_price": {"type": "NUMERIC(10, 2)", "description": "Unit selling price at time of order"},
            "discount": {"type": "NUMERIC(5, 4)", "description": "Discount rate between 0.00 and 1.00 (e.g. 0.15 = 15% discount)"}
        }
    }
}

# Relationships
RELATIONSHIPS = [
    "customers.customer_id = orders.customer_id (One customer has many orders)",
    "orders.order_id = order_items.order_id (One order has many order items)",
    "products.product_id = order_items.product_id (One product has many order item rows)"
]

# Standard Business Metrics and Data Dictionary
METRIC_DEFINITIONS = {
    "Gross Sales": {
        "formula": "SUM(order_items.quantity * order_items.unit_price)",
        "condition": "orders.status = 'Completed'",
        "description": "Total value of items ordered before any discounts."
    },
    "Net Sales / Revenue": {
        "formula": "SUM(order_items.quantity * order_items.unit_price * (1.0 - order_items.discount))",
        "condition": "orders.status = 'Completed'",
        "description": "Actual realized revenue after deducting item-level discounts. Excludes cancelled or returned orders."
    },
    "Eligible Orders": {
        "formula": "COUNT(DISTINCT orders.order_id)",
        "condition": "orders.status = 'Completed'",
        "description": "Count of successfully completed orders."
    },
    "Average Order Value (AOV)": {
        "formula": "Net Sales / COUNT(DISTINCT orders.order_id)",
        "condition": "orders.status = 'Completed'",
        "description": "Average revenue generated per eligible order."
    },
    "Active Customers": {
        "formula": "COUNT(DISTINCT orders.customer_id)",
        "condition": "orders.status = 'Completed'",
        "description": "Number of unique customers who placed at least one eligible order in the period."
    },
    "Profit / Margin": {
        "formula": "SUM(order_items.quantity * (order_items.unit_price * (1.0 - order_items.discount) - products.cost_price))",
        "condition": "orders.status = 'Completed'",
        "description": "Net revenue minus product acquisition cost."
    },
    "Month-over-Month (MoM) Growth": {
        "formula": "((current_month_metric - previous_month_metric) / previous_month_metric) * 100.0",
        "description": "Percentage change of metric compared to the prior calendar month."
    }
}

# Business Rules
BUSINESS_RULES = [
    "Revenue and sales calculations MUST filter by `orders.status = 'Completed'` unless the user explicitly requests cancelled or returned orders.",
    "Do NOT calculate revenue from products.cost_price; unit_price is stored in order_items for point-in-time accuracy.",
    "Discount is a decimal between 0.0 and 1.0 (e.g. 0.10 means 10%). Net revenue per line is quantity * unit_price * (1.0 - discount).",
    "Dates are stored in 'YYYY-MM-DD' format.",
    "When computing Month-over-Month growth, order by year and month chronologically, and use window functions (LAG) where appropriate.",
    "Always provide meaningful column aliases (e.g., net_sales, order_count, category, month)."
]


def get_formatted_schema_context() -> str:
    """Format schema, relationships, and business metrics for LLM prompts."""
    lines = ["### DATABASE TABLES AND COLUMNS ###"]
    for table_name, table_info in SCHEMA_DEFINITION.items():
        lines.append(f"\nTable: {table_name}")
        lines.append(f"Description: {table_info['description']}")
        lines.append("Columns:")
        for col_name, col_info in table_info["columns"].items():
            pk = " [PRIMARY KEY]" if col_info.get("primary_key") else ""
            fk = f" [FOREIGN KEY -> {col_info['foreign_key']}]" if col_info.get("foreign_key") else ""
            lines.append(f"  - {col_name} ({col_info['type']}){pk}{fk}: {col_info['description']}")

    lines.append("\n### RELATIONSHIPS ###")
    for rel in RELATIONSHIPS:
        lines.append(f"- {rel}")

    lines.append("\n### BUSINESS METRIC DEFINITIONS ###")
    for metric, info in METRIC_DEFINITIONS.items():
        cond = f" (Condition: {info['condition']})" if "condition" in info else ""
        lines.append(f"- {metric}: Formula = {info['formula']}{cond} -> {info['description']}")

    lines.append("\n### BUSINESS RULES ###")
    for rule in BUSINESS_RULES:
        lines.append(f"- {rule}")

    return "\n".join(lines)
