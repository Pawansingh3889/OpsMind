"""Create a realistic demo database for a fish processing factory."""
import sqlite3
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'demo.db')


def seed():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # === SCHEMA ===
    c.executescript('''
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS raw_materials;
        DROP TABLE IF EXISTS production;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS waste_log;
        DROP TABLE IF EXISTS temp_logs;
        DROP TABLE IF EXISTS staff;
        DROP TABLE IF EXISTS documents;

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            species TEXT,
            category TEXT,
            unit_cost_per_kg REAL,
            sell_price_per_kg REAL,
            allergens TEXT
        );

        CREATE TABLE raw_materials (
            id INTEGER PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            batch_code TEXT,
            supplier TEXT,
            quantity_kg REAL,
            received_date TEXT,
            expiry_date TEXT,
            temperature_on_arrival REAL
        );

        CREATE TABLE production (
            id INTEGER PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            batch_code TEXT,
            date TEXT,
            raw_input_kg REAL,
            finished_output_kg REAL,
            waste_kg REAL,
            yield_pct REAL,
            line_number INTEGER,
            shift TEXT,
            operator TEXT
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer TEXT,
            product_id INTEGER REFERENCES products(id),
            quantity_kg REAL,
            order_date TEXT,
            delivery_date TEXT,
            status TEXT DEFAULT 'pending',
            price_per_kg REAL
        );

        CREATE TABLE waste_log (
            id INTEGER PRIMARY KEY,
            production_id INTEGER REFERENCES production(id),
            waste_type TEXT,
            quantity_kg REAL,
            reason TEXT,
            date TEXT
        );

        CREATE TABLE temp_logs (
            id INTEGER PRIMARY KEY,
            location TEXT,
            temperature REAL,
            recorded_at TEXT,
            recorded_by TEXT
        );

        CREATE TABLE staff (
            id INTEGER PRIMARY KEY,
            name TEXT,
            role TEXT,
            shift_pattern TEXT,
            hours_this_week REAL,
            hourly_rate REAL
        );

        CREATE TABLE documents (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            category TEXT,
            uploaded_at TEXT,
            description TEXT
        );
    ''')

    # === PRODUCTS ===
    products = [
        (1, 'Atlantic Salmon Fillet', 'Salmon', 'fresh_fillet', 8.50, 14.20, 'Fish'),
        (2, 'Cod Fillet', 'Cod', 'fresh_fillet', 7.20, 12.50, 'Fish'),
        (3, 'Haddock Fillet', 'Haddock', 'fresh_fillet', 6.80, 11.90, 'Fish'),
        (4, 'Smoked Salmon', 'Salmon', 'smoked', 12.00, 22.50, 'Fish'),
        (5, 'Breaded Cod', 'Cod', 'breaded', 5.50, 9.80, 'Fish, Wheat, Egg'),
        (6, 'Fish Pie Mix', 'Mixed', 'value_added', 4.20, 7.50, 'Fish, Milk'),
        (7, 'Prawn Ring', 'Prawn', 'value_added', 6.00, 11.00, 'Crustaceans'),
        (8, 'Smoked Haddock', 'Haddock', 'smoked', 9.50, 16.80, 'Fish'),
        (9, 'Sea Bass Fillet', 'Sea Bass', 'fresh_fillet', 11.00, 18.50, 'Fish'),
        (10, 'Salmon Portions 140g', 'Salmon', 'portions', 9.00, 15.50, 'Fish'),
    ]
    c.executemany('INSERT INTO products VALUES (?,?,?,?,?,?,?)', products)

    # === SUPPLIERS ===
    suppliers = ['Nordic Catch Ltd', 'Scottish Seafoods', 'Grimsby Fish Co', 'Iceland Fresh', 'Norwegian Select']

    # === CUSTOMERS ===
    customers = ['Lidl UK', 'Iceland Foods', 'Tesco', 'Morrisons', 'Aldi UK', 'Costco UK', 'Booker Wholesale']

    # === STAFF ===
    staff_data = [
        (1, 'Alex Morgan', 'Shift Manager', 'Days', 44, 14.50),
        (2, 'Marek Kowalski', 'Line Operator', 'Days', 40, 11.44),
        (3, 'Agne Kazlauskiene', 'Line Operator', 'Days', 40, 11.44),
        (4, 'Radu Popescu', 'Line Operator', 'Nights', 48, 12.50),
        (5, 'Priya Desai', 'Quality Control', 'Days', 38, 13.00),
        (6, 'Tomasz Nowak', 'Forklift Driver', 'Days', 42, 12.00),
        (7, 'Elena Gheorghe', 'Packer', 'Days', 40, 11.44),
        (8, 'James Wilson', 'Maintenance', 'Days', 45, 15.00),
        (9, 'Aisha Khan', 'Line Operator', 'Nights', 40, 12.50),
        (10, 'Vytautas Barkus', 'Line Operator', 'Nights', 50, 12.50),
        (11, 'Sofia Ivanova', 'Packer', 'Days', 36, 11.44),
    ]
    c.executemany('INSERT INTO staff VALUES (?,?,?,?,?,?)', staff_data)

    # === GENERATE 60 DAYS OF DATA ===
    today = datetime.now()
    shifts = ['Morning', 'Afternoon', 'Night']
    operators = [s[1] for s in staff_data if 'Operator' in s[2] or 'Packer' in s[2]]

    prod_id = 0
    waste_id = 0
    rm_id = 0
    order_id = 0

    for day_offset in range(60):
        date = today - timedelta(days=day_offset)
        date_str = date.strftime('%Y-%m-%d')

        # Raw materials received (3-6 deliveries per day)
        for _ in range(random.randint(3, 6)):
            rm_id += 1
            prod = random.choice(products)
            qty = round(random.uniform(200, 2000), 1)
            temp = round(random.uniform(-1.5, 4.5), 1)
            expiry = (date + timedelta(days=random.randint(3, 14))).strftime('%Y-%m-%d')
            c.execute('INSERT INTO raw_materials VALUES (?,?,?,?,?,?,?,?)',
                      (rm_id, prod[0], f'RM-{date.strftime("%y%m%d")}-{rm_id}',
                       random.choice(suppliers), qty, date_str, expiry, temp))

        # Production runs (8-15 per day)
        for _ in range(random.randint(8, 15)):
            prod_id += 1
            prod = random.choice(products)
            raw_kg = round(random.uniform(100, 800), 1)

            # Yield varies by product type with realistic variation
            base_yield = {'fresh_fillet': 0.62, 'smoked': 0.55, 'breaded': 0.72,
                         'value_added': 0.68, 'portions': 0.65}
            avg_yield = base_yield.get(prod[3], 0.65)
            # Add realistic variation (+/- 8%)
            actual_yield = avg_yield + random.uniform(-0.08, 0.05)
            actual_yield = max(0.40, min(0.85, actual_yield))

            output_kg = round(raw_kg * actual_yield, 1)
            waste_kg = round(raw_kg - output_kg, 1)
            yield_pct = round(actual_yield * 100, 1)

            shift = random.choice(shifts)
            operator = random.choice(operators)

            c.execute('INSERT INTO production VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                      (prod_id, prod[0], f'PR-{date.strftime("%y%m%d")}-{prod_id}',
                       date_str, raw_kg, output_kg, waste_kg, yield_pct,
                       random.randint(1, 4), shift, operator))

            # Waste log entry
            waste_id += 1
            waste_types = ['Trim', 'Skin', 'Bones', 'Rejected', 'Overproduction', 'Damaged']
            waste_reasons = ['Normal processing', 'Quality rejection', 'Size spec failure',
                           'Temperature excursion', 'Overproduction', 'Equipment issue',
                           'Late delivery', 'Customer cancellation']
            c.execute('INSERT INTO waste_log VALUES (?,?,?,?,?,?)',
                      (waste_id, prod_id, random.choice(waste_types),
                       waste_kg, random.choice(waste_reasons), date_str))

        # Orders (5-10 per day)
        for _ in range(random.randint(5, 10)):
            order_id += 1
            prod = random.choice(products)
            qty = round(random.uniform(50, 500), 1)
            delivery = (date + timedelta(days=random.randint(1, 5))).strftime('%Y-%m-%d')
            status = random.choice(['delivered', 'delivered', 'delivered', 'pending', 'in_production', 'cancelled'])
            price = prod[5] + random.uniform(-1.0, 2.0)
            c.execute('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)',
                      (order_id, random.choice(customers), prod[0], qty,
                       date_str, delivery, status, round(price, 2)))

        # Temperature logs (every 2 hours, 5 locations)
        locations = ['Cold Room 1', 'Cold Room 2', 'Freezer 1', 'Production Floor', 'Dispatch Bay']
        base_temps = {'Cold Room 1': 2.0, 'Cold Room 2': 2.5, 'Freezer 1': -18.0,
                     'Production Floor': 12.0, 'Dispatch Bay': 5.0}
        for hour in range(0, 24, 2):
            for loc in locations:
                temp = base_temps[loc] + random.uniform(-1.5, 1.5)
                # Occasional excursion
                if random.random() < 0.02:
                    temp += random.uniform(3, 8)
                recorded_at = date.replace(hour=hour).strftime('%Y-%m-%d %H:%M')
                recorder = random.choice([s[1] for s in staff_data])
                c.execute('INSERT INTO temp_logs (location, temperature, recorded_at, recorded_by) VALUES (?,?,?,?)',
                          (loc, round(temp, 1), recorded_at, recorder))

    # === DOCUMENTS ===
    docs = [
        (1, 'HACCP_Plan_2024.pdf', 'HACCP', today.strftime('%Y-%m-%d'), 'Hazard Analysis and Critical Control Points plan'),
        (2, 'BRC_Audit_Report_2024.pdf', 'Audit', today.strftime('%Y-%m-%d'), 'BRC Global Standard for Food Safety audit report'),
        (3, 'SOP_Cold_Room_Temperature.pdf', 'SOP', today.strftime('%Y-%m-%d'), 'Standard operating procedure for cold room temperature monitoring'),
        (4, 'SOP_Allergen_Management.pdf', 'SOP', today.strftime('%Y-%m-%d'), 'Allergen management and labelling procedures'),
        (5, 'Lidl_Product_Spec_Salmon.pdf', 'Customer Spec', today.strftime('%Y-%m-%d'), 'Lidl product specification for salmon fillets'),
        (6, 'Iceland_Product_Spec_Cod.pdf', 'Customer Spec', today.strftime('%Y-%m-%d'), 'Iceland product specification for breaded cod'),
        (7, 'Staff_Handbook_2024.pdf', 'HR', today.strftime('%Y-%m-%d'), 'Employee handbook with health and safety procedures'),
        (8, 'Cleaning_Schedule.pdf', 'SOP', today.strftime('%Y-%m-%d'), 'Daily and weekly cleaning schedule for all areas'),
    ]
    c.executemany('INSERT INTO documents VALUES (?,?,?,?,?)', docs)

    conn.commit()
    conn.close()

    print(f'Demo database created at {DB_PATH}')
    print(f'  Products: {len(products)}')
    print(f'  Staff: {len(staff_data)}')
    print(f'  Raw materials: {rm_id}')
    print(f'  Production runs: {prod_id}')
    print(f'  Waste records: {waste_id}')
    print(f'  Orders: {order_id}')
    print(f'  Temperature logs: {60 * 12 * 5}')
    print(f'  Documents: {len(docs)}')


if __name__ == '__main__':
    seed()
