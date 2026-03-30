"""Smart alerts and anomaly detection for factory operations."""
import sqlite3
import pandas as pd
from config import DATABASE_URL, YIELD_DROP_THRESHOLD, MAX_WEEKLY_HOURS


def get_db_path():
    url = DATABASE_URL
    if url.startswith('sqlite:///'):
        return url.replace('sqlite:///', '')
    return 'data/demo.db'


def check_all_alerts():
    """Run all alert checks and return a list of active alerts."""
    alerts = []
    alerts.extend(check_yield_drops())
    alerts.extend(check_temperature_excursions())
    alerts.extend(check_overtime())
    alerts.extend(check_expiring_stock())
    alerts.extend(check_order_shortfalls())
    return sorted(alerts, key=lambda a: {'critical': 0, 'warning': 1, 'info': 2}[a['level']])


def check_yield_drops():
    """Alert if any product's yield dropped significantly vs 30-day average."""
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query('''
        SELECT pr.name,
               ROUND(AVG(CASE WHEN p.date >= date('now', '-7 days') THEN p.yield_pct END), 1) as this_week,
               ROUND(AVG(CASE WHEN p.date >= date('now', '-30 days') THEN p.yield_pct END), 1) as monthly_avg
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        WHERE p.date >= date('now', '-30 days')
        GROUP BY pr.name
        HAVING this_week IS NOT NULL AND monthly_avg IS NOT NULL
    ''', conn)
    conn.close()

    alerts = []
    for _, row in df.iterrows():
        drop = row['monthly_avg'] - row['this_week']
        if drop > YIELD_DROP_THRESHOLD:
            alerts.append({
                'level': 'warning',
                'icon': 'chart-line-down',
                'title': f"Yield drop on {row['name']}",
                'message': f"This week: {row['this_week']}% vs 30-day avg: {row['monthly_avg']}% (down {drop:.1f}%)",
                'category': 'yield'
            })
    return alerts


def check_temperature_excursions():
    """Alert on recent temperature excursions."""
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query('''
        SELECT location, temperature, recorded_at
        FROM temp_logs
        WHERE recorded_at >= date('now', '-1 day')
        AND (
            (location LIKE '%Cold Room%' AND temperature > 5)
            OR (location LIKE '%Freezer%' AND temperature > -15)
        )
        ORDER BY recorded_at DESC
        LIMIT 5
    ''', conn)
    conn.close()

    alerts = []
    for _, row in df.iterrows():
        alerts.append({
            'level': 'critical',
            'icon': 'temperature-high',
            'title': f"Temperature excursion: {row['location']}",
            'message': f"{row['temperature']}°C recorded at {row['recorded_at']}",
            'category': 'temperature'
        })
    return alerts


def check_overtime():
    """Alert if staff are approaching or exceeding Working Time Regulations limits."""
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query(f'''
        SELECT name, role, hours_this_week, shift_pattern
        FROM staff
        WHERE hours_this_week > {MAX_WEEKLY_HOURS - 4}
    ''', conn)
    conn.close()

    alerts = []
    for _, row in df.iterrows():
        if row['hours_this_week'] >= MAX_WEEKLY_HOURS:
            alerts.append({
                'level': 'critical',
                'icon': 'clock',
                'title': f"Overtime breach: {row['name']}",
                'message': f"{row['hours_this_week']}h this week (max {MAX_WEEKLY_HOURS}h). Working Time Regulations violation.",
                'category': 'staff'
            })
        else:
            alerts.append({
                'level': 'warning',
                'icon': 'clock',
                'title': f"Overtime warning: {row['name']}",
                'message': f"{row['hours_this_week']}h this week, approaching {MAX_WEEKLY_HOURS}h limit.",
                'category': 'staff'
            })
    return alerts


def check_expiring_stock():
    """Alert on raw materials expiring within 2 days."""
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query('''
        SELECT rm.batch_code, pr.name, rm.quantity_kg, rm.expiry_date,
               CAST(julianday(rm.expiry_date) - julianday('now') AS INTEGER) as days_left
        FROM raw_materials rm
        JOIN products pr ON rm.product_id = pr.id
        WHERE rm.expiry_date <= date('now', '+2 days')
        AND rm.expiry_date >= date('now')
        ORDER BY rm.expiry_date
    ''', conn)
    conn.close()

    alerts = []
    for _, row in df.iterrows():
        alerts.append({
            'level': 'warning',
            'icon': 'calendar-xmark',
            'title': f"Expiring: {row['name']} ({row['batch_code']})",
            'message': f"{row['quantity_kg']}kg expires {row['expiry_date']} ({row['days_left']} days). Process or sell urgently.",
            'category': 'stock'
        })
    return alerts


def check_order_shortfalls():
    """Alert if pending orders may not be fulfilled with current stock."""
    conn = sqlite3.connect(get_db_path())
    df = pd.read_sql_query('''
        SELECT o.customer, pr.name,
               SUM(o.quantity_kg) as ordered_kg,
               COALESCE((
                   SELECT SUM(rm2.quantity_kg)
                   FROM raw_materials rm2
                   WHERE rm2.product_id = o.product_id
                   AND rm2.expiry_date > date('now')
               ), 0) as available_kg
        FROM orders o
        JOIN products pr ON o.product_id = pr.id
        WHERE o.status = 'pending'
        AND o.delivery_date <= date('now', '+3 days')
        GROUP BY o.customer, pr.name
    ''', conn)
    conn.close()

    alerts = []
    for _, row in df.iterrows():
        if row['ordered_kg'] > row['available_kg']:
            shortfall = row['ordered_kg'] - row['available_kg']
            alerts.append({
                'level': 'critical',
                'icon': 'box-open',
                'title': f"Order shortfall: {row['customer']}",
                'message': f"Need {row['ordered_kg']}kg {row['name']} but only {row['available_kg']}kg available. Short by {shortfall:.0f}kg.",
                'category': 'orders'
            })
    return alerts
