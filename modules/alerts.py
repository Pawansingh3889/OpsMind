"""Smart alerts and anomaly detection for operations."""
from config import MAX_WEEKLY_HOURS, PROD_YIELD_MIN, YIELD_DROP_THRESHOLD
from modules.database import query
from modules.sql_dialect import days_ago, days_ahead, days_until


def check_all_alerts():
    """Run all alert checks and return a list of active alerts."""
    alerts = []
    alerts.extend(check_yield_drops())
    alerts.extend(check_temperature_excursions())
    alerts.extend(check_overtime())
    alerts.extend(check_expiring_stock())
    alerts.extend(check_order_shortfalls())
    alerts.extend(check_prod_yield_drops())
    alerts.extend(check_prod_temp_breaches())
    alerts.extend(check_open_critical_ncs())
    return sorted(alerts, key=lambda a: {'critical': 0, 'warning': 1, 'info': 2}[a['level']])


def check_yield_drops():
    """Alert if any product's yield dropped significantly vs 30-day average."""
    df = query(f"""
        SELECT pr.name, pr.unit_cost_per_kg,
               ROUND(AVG(CASE WHEN p.date >= {days_ago(7)} THEN p.yield_pct END), 1) as this_week,
               ROUND(AVG(CASE WHEN p.date >= {days_ago(30)} THEN p.yield_pct END), 1) as monthly_avg,
               COALESCE(SUM(CASE WHEN p.date >= {days_ago(7)} THEN p.waste_kg END), 0) as week_waste_kg
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        WHERE p.date >= {days_ago(30)}
        GROUP BY pr.name, pr.unit_cost_per_kg
        HAVING AVG(CASE WHEN p.date >= {days_ago(7)} THEN p.yield_pct END) IS NOT NULL
    """)

    alerts = []
    for _, row in df.iterrows():
        if row['monthly_avg'] is None or row['this_week'] is None:
            continue
        drop = row['monthly_avg'] - row['this_week']
        if drop > YIELD_DROP_THRESHOLD:
            waste_cost = row['week_waste_kg'] * row['unit_cost_per_kg']
            alerts.append({
                'level': 'warning',
                'icon': 'chart-line-down',
                'title': f"Yield drop on {row['name']} — GBP {waste_cost:,.0f} lost this week",
                'message': f"This week: {row['this_week']}% vs 30-day avg: {row['monthly_avg']}% (down {drop:.1f}%). Waste cost: GBP {waste_cost:,.0f}.",
                'category': 'yield'
            })
    return alerts


def check_temperature_excursions():
    """Alert on recent temperature excursions."""
    df = query(f"""
        SELECT location, temperature, recorded_at
        FROM temp_logs
        WHERE recorded_at >= {days_ago(1)}
        AND (
            (location LIKE '%Cold Room%' AND temperature > 5)
            OR (location LIKE '%Freezer%' AND temperature > -15)
        )
        ORDER BY recorded_at DESC
    """)

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
    threshold = MAX_WEEKLY_HOURS - 4
    df = query(f"""
        SELECT name, role, hours_this_week, shift_pattern
        FROM staff
        WHERE hours_this_week > {threshold}
    """)

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
    df = query(f"""
        SELECT rm.batch_code, pr.name, rm.quantity_kg, rm.expiry_date,
               {days_until('rm.expiry_date')} as days_left
        FROM raw_materials rm
        JOIN products pr ON rm.product_id = pr.id
        WHERE rm.expiry_date <= {days_ahead(2)}
        AND rm.expiry_date >= {days_ago(0)}
        ORDER BY rm.expiry_date
    """)

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
    df = query(f"""
        SELECT o.customer, pr.name,
               SUM(o.quantity_kg) as ordered_kg,
               COALESCE((
                   SELECT SUM(rm2.quantity_kg)
                   FROM raw_materials rm2
                   WHERE rm2.product_id = o.product_id
                   AND rm2.expiry_date > {days_ago(0)}
               ), 0) as available_kg
        FROM orders o
        JOIN products pr ON o.product_id = pr.id
        WHERE o.status = 'pending'
        AND o.delivery_date <= {days_ahead(3)}
        GROUP BY o.customer, pr.name, o.product_id
    """)

    alerts = []
    for _, row in df.iterrows():
        if row['ordered_kg'] > row['available_kg']:
            shortfall = row['ordered_kg'] - row['available_kg']
            alerts.append({
                'level': 'critical',
                'icon': 'box-open',
                'title': f"Order shortfall: {row['customer']}",
                'message': f"Need {row['ordered_kg']:.0f}kg {row['name']} but only {row['available_kg']:.0f}kg available. Short by {shortfall:.0f}kg.",
                'category': 'orders'
            })
    return alerts


def check_prod_yield_drops():
    """Alert on production runs with yield below threshold."""
    df = query(f"""
        SELECT r.run_number, r.production_date, r.yield_pct,
               pp.description as product, pp.customer, r.waste_kg
        FROM prod_runs r
        JOIN prod_products pp ON r.product_code = pp.product_code
        WHERE r.status = 'complete'
          AND r.yield_pct < {PROD_YIELD_MIN}
          AND r.production_date >= {days_ago(7)}
        ORDER BY r.yield_pct ASC
    """)

    alerts = []
    for _, row in df.iterrows():
        alerts.append({
            'level': 'warning',
            'icon': 'chart-line-down',
            'title': f"Low yield: {row['product']} (Run {row['run_number']})",
            'message': f"Yield {row['yield_pct']}% (threshold {PROD_YIELD_MIN}%). Waste: {row['waste_kg']}kg. Customer: {row['customer']}.",
            'category': 'production'
        })
    return alerts


def check_prod_temp_breaches():
    """Alert on production temperature breaches in last 24 hours."""
    df = query(f"""
        SELECT location, reading_time, temp_celsius,
               target_max, recorded_by
        FROM prod_temperature_logs
        WHERE in_range = 0
          AND reading_time >= {days_ago(1)}
        ORDER BY reading_time DESC
    """)

    alerts = []
    for _, row in df.iterrows():
        alerts.append({
            'level': 'critical',
            'icon': 'temperature-high',
            'title': f"Production temp breach: {row['location']}",
            'message': f"{row['temp_celsius']}C (max {row['target_max']}C) at {row['reading_time']}. Recorded by {row['recorded_by']}.",
            'category': 'temperature'
        })
    return alerts


def check_open_critical_ncs():
    """Alert on critical non-conformances open beyond threshold."""
    df = query("""
        SELECT nc_id, nc_date, nc_type, severity,
               description, raised_by, status
        FROM prod_non_conformance
        WHERE severity = 'critical'
          AND status != 'closed'
    """)

    alerts = []
    for _, row in df.iterrows():
        level = 'critical' if row['status'] == 'open' else 'warning'
        alerts.append({
            'level': level,
            'icon': 'triangle-exclamation',
            'title': f"Critical NC open: {row['nc_type']} (#{row['nc_id']})",
            'message': f"{row['description']}. Raised by {row['raised_by']}. Status: {row['status']}.",
            'category': 'compliance'
        })
    return alerts
