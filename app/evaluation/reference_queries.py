"""Verified reference SQL queries covering core business analytics scenarios."""

from typing import List, Dict, Any

REFERENCE_QUERIES: List[Dict[str, Any]] = [
    {
        "id": "REF-01",
        "question": "What is the total gross sales across all completed orders?",
        "category": "aggregation",
        "sql": """
            SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gross_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status = 'Completed'
        """
    },
    {
        "id": "REF-02",
        "question": "What is the total net sales after discounts for completed orders?",
        "category": "aggregation",
        "sql": """
            SELECT ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status = 'Completed'
        """
    },
    {
        "id": "REF-03",
        "question": "How many eligible completed orders were placed in total?",
        "category": "aggregation",
        "sql": """
            SELECT COUNT(DISTINCT order_id) AS completed_orders
            FROM orders
            WHERE status = 'Completed'
        """
    },
    {
        "id": "REF-04",
        "question": "What is the overall Average Order Value (AOV) for completed orders?",
        "category": "aggregation",
        "sql": """
            SELECT ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)) / COUNT(DISTINCT o.order_id), 2) AS average_order_value
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed'
        """
    },
    {
        "id": "REF-05",
        "question": "How many distinct active customers have placed at least one completed order?",
        "category": "aggregation",
        "sql": """
            SELECT COUNT(DISTINCT customer_id) AS active_customers
            FROM orders
            WHERE status = 'Completed'
        """
    },
    {
        "id": "REF-06",
        "question": "What was the total net sales by product category in 2025?",
        "category": "joins_and_filters",
        "sql": """
            SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.status = 'Completed' AND o.order_date >= '2025-01-01' AND o.order_date <= '2025-12-31'
            GROUP BY p.category
            ORDER BY net_sales DESC
        """
    },
    {
        "id": "REF-07",
        "question": "What are the top 5 products by net revenue in 2024?",
        "category": "ranking",
        "sql": """
            SELECT p.product_name, p.category, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.status = 'Completed' AND o.order_date >= '2024-01-01' AND o.order_date <= '2024-12-31'
            GROUP BY p.product_name, p.category
            ORDER BY net_revenue DESC
            LIMIT 5
        """
    },
    {
        "id": "REF-08",
        "question": "What is the monthly net sales trend for 2025?",
        "category": "time_series",
        "sql": """
            SELECT SUBSTR(o.order_date, 1, 7) AS month, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS monthly_net_sales
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed' AND o.order_date >= '2025-01-01' AND o.order_date <= '2025-12-31'
            GROUP BY SUBSTR(o.order_date, 1, 7)
            ORDER BY month ASC
        """
    },
    {
        "id": "REF-09",
        "question": "What is the breakdown of net sales by customer segment?",
        "category": "joins_and_filters",
        "sql": """
            SELECT c.segment, COUNT(DISTINCT o.order_id) AS order_count, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_sales
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed'
            GROUP BY c.segment
            ORDER BY net_sales DESC
        """
    },
    {
        "id": "REF-10",
        "question": "What is the customer count and total net sales by geographic region?",
        "category": "joins_and_filters",
        "sql": """
            SELECT c.region, COUNT(DISTINCT c.customer_id) AS customer_count, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS regional_net_sales
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed'
            GROUP BY c.region
            ORDER BY regional_net_sales DESC
        """
    },
    {
        "id": "REF-11",
        "question": "Who are the top 10 customers by lifetime net spend?",
        "category": "ranking",
        "sql": """
            SELECT c.customer_id, c.name, c.region, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS total_spend
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed'
            GROUP BY c.customer_id, c.name, c.region
            ORDER BY total_spend DESC
            LIMIT 10
        """
    },
    {
        "id": "REF-12",
        "question": "How many orders were placed with each payment method?",
        "category": "aggregation",
        "sql": """
            SELECT payment_method, COUNT(order_id) AS order_count
            FROM orders
            GROUP BY payment_method
            ORDER BY order_count DESC
        """
    },
    {
        "id": "REF-13",
        "question": "What was the month-over-month revenue growth for 2025?",
        "category": "comparison",
        "sql": """
            WITH monthly_sales AS (
                SELECT SUBSTR(o.order_date, 1, 7) AS month, SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)) AS net_sales
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
                WHERE o.status = 'Completed' AND o.order_date >= '2025-01-01' AND o.order_date <= '2025-12-31'
                GROUP BY SUBSTR(o.order_date, 1, 7)
            )
            SELECT month, ROUND(net_sales, 2) AS current_sales,
                   ROUND(LAG(net_sales, 1) OVER (ORDER BY month), 2) AS previous_month_sales,
                   ROUND(((net_sales - LAG(net_sales, 1) OVER (ORDER BY month)) / LAG(net_sales, 1) OVER (ORDER BY month)) * 100.0, 2) AS mom_growth_pct
            FROM monthly_sales
            ORDER BY month ASC
        """
    },
    {
        "id": "REF-14",
        "question": "Which product categories have an average discount rate exceeding 5%?",
        "category": "aggregation_having",
        "sql": """
            SELECT p.category, ROUND(AVG(oi.discount) * 100.0, 2) AS avg_discount_pct
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status = 'Completed'
            GROUP BY p.category
            HAVING AVG(oi.discount) > 0.05
            ORDER BY avg_discount_pct DESC
        """
    },
    {
        "id": "REF-15",
        "question": "How many orders were cancelled or returned versus completed?",
        "category": "aggregation",
        "sql": """
            SELECT status, COUNT(*) AS count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) AS percentage
            FROM orders
            GROUP BY status
            ORDER BY count DESC
        """
    },
    {
        "id": "REF-16",
        "question": "What was the total net sales from Electronics in Q1 2025?",
        "category": "filtering",
        "sql": """
            SELECT ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS q1_electronics_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.status = 'Completed' AND p.category = 'Electronics' AND o.order_date >= '2025-01-01' AND o.order_date <= '2025-03-31'
        """
    },
    {
        "id": "REF-17",
        "question": "What is the estimated profit by product category?",
        "category": "joins_and_filters",
        "sql": """
            SELECT p.category,
                   ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS net_revenue,
                   ROUND(SUM(oi.quantity * p.cost_price), 2) AS total_cost,
                   ROUND(SUM(oi.quantity * (oi.unit_price * (1.0 - oi.discount) - p.cost_price)), 2) AS profit
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status = 'Completed'
            GROUP BY p.category
            ORDER BY profit DESC
        """
    },
    {
        "id": "REF-18",
        "question": "How many completed orders were placed by customers in the West region?",
        "category": "joins_and_filters",
        "sql": """
            SELECT COUNT(DISTINCT o.order_id) AS west_completed_orders
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.status = 'Completed' AND c.region = 'West'
        """
    },
    {
        "id": "REF-19",
        "question": "What are the least ordered products by quantity?",
        "category": "ranking",
        "sql": """
            SELECT p.product_name, p.category, COALESCE(SUM(oi.quantity), 0) AS units_sold
            FROM products p
            LEFT JOIN order_items oi ON p.product_id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status = 'Completed'
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY units_sold ASC
            LIMIT 5
        """
    },
    {
        "id": "REF-20",
        "question": "Which completed orders had a total net value exceeding $1000?",
        "category": "filtering",
        "sql": """
            SELECT o.order_id, o.order_date, c.name AS customer_name, ROUND(SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)), 2) AS order_total
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.status = 'Completed'
            GROUP BY o.order_id, o.order_date, c.name
            HAVING SUM(oi.quantity * oi.unit_price * (1.0 - oi.discount)) > 1000
            ORDER BY order_total DESC
        """
    }
]


def verify_reference_queries() -> Dict[str, Any]:
    """Execute all reference queries against the database and verify success."""
    from app.database.executor import execute_query
    from app.security.sql_validator import validate_and_sanitize_sql

    results = []
    failed = 0

    for item in REFERENCE_QUERIES:
        val_res = validate_and_sanitize_sql(item["sql"])
        if not val_res.is_valid:
            results.append({
                "id": item["id"],
                "status": "validation_failed",
                "error": val_res.error_message
            })
            failed += 1
            continue

        exec_res = execute_query(val_res.sanitized_sql)
        if exec_res.status != "success":
            results.append({
                "id": item["id"],
                "status": "execution_failed",
                "error": exec_res.error_message
            })
            failed += 1
        else:
            results.append({
                "id": item["id"],
                "status": "passed",
                "row_count": exec_res.row_count,
                "first_row": exec_res.rows[0] if exec_res.rows else None,
                "execution_ms": exec_res.execution_time_ms
            })

    return {
        "total": len(REFERENCE_QUERIES),
        "passed": len(REFERENCE_QUERIES) - failed,
        "failed": failed,
        "details": results
    }


if __name__ == "__main__":
    report = verify_reference_queries()
    print(f"Reference Query Verification: {report['passed']}/{report['total']} passed.")
    if report["failed"] > 0:
        for d in report["details"]:
            if d["status"] != "passed":
                print(f"  FAILED: {d['id']} -> {d['error']}")
