"""Create a realistic demo database for a fish processing factory."""
import os
import random
import sqlite3
from datetime import datetime, timedelta

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

        -- Production ERP tables (detailed pack-level tracking)
        DROP TABLE IF EXISTS prod_lines;
        DROP TABLE IF EXISTS prod_products;
        DROP TABLE IF EXISTS prod_runs;
        DROP TABLE IF EXISTS prod_transactions;
        DROP TABLE IF EXISTS prod_run_totals;
        DROP TABLE IF EXISTS prod_traceability;
        DROP TABLE IF EXISTS prod_temperature_logs;
        DROP TABLE IF EXISTS prod_non_conformance;
        DROP TABLE IF EXISTS prod_case_verification;
        DROP TABLE IF EXISTS prod_despatch;
        DROP TABLE IF EXISTS prod_shifts;

        CREATE TABLE prod_lines (
            line_id INTEGER PRIMARY KEY,
            line_name TEXT NOT NULL,
            line_type TEXT,
            area TEXT,
            max_capacity_kg REAL,
            active INTEGER DEFAULT 1,
            created_date TEXT
        );

        CREATE TABLE prod_products (
            product_code TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            category TEXT,
            species TEXT,
            customer TEXT,
            pack_size_g REAL,
            shelf_life_days INTEGER,
            allergens TEXT,
            hazard_class TEXT DEFAULT 'HIGH',
            active INTEGER DEFAULT 1
        );

        CREATE TABLE prod_traceability (
            trace_id TEXT PRIMARY KEY,
            batch_code TEXT NOT NULL,
            supplier TEXT,
            species TEXT,
            catch_area TEXT,
            catch_method TEXT,
            vessel_name TEXT,
            landing_date TEXT,
            kill_date TEXT,
            received_date TEXT,
            received_temp_c REAL,
            use_by_date TEXT,
            country_origin TEXT,
            certified TEXT,
            allergen_check INTEGER DEFAULT 0,
            created_date TEXT
        );

        CREATE TABLE prod_runs (
            run_number TEXT PRIMARY KEY,
            production_date TEXT NOT NULL,
            shift_code TEXT,
            shift_date TEXT,
            prod_line INTEGER REFERENCES prod_lines(line_id),
            product_code TEXT REFERENCES prod_products(product_code),
            spec TEXT,
            prog_id TEXT,
            target_qty_kg REAL,
            actual_qty_kg REAL,
            waste_kg REAL DEFAULT 0,
            yield_pct REAL,
            status TEXT DEFAULT 'active',
            complete INTEGER DEFAULT 0,
            kill_date TEXT,
            trace_id TEXT,
            created_by TEXT,
            created_date TEXT,
            updated_by TEXT,
            updated_date TEXT
        );

        CREATE TABLE prod_transactions (
            trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_number TEXT REFERENCES prod_runs(run_number),
            trans_date TEXT NOT NULL,
            product_code TEXT,
            weight_g REAL NOT NULL,
            target_weight_g REAL,
            tare_g REAL DEFAULT 0,
            net_weight_g REAL,
            overweight_g REAL,
            barcode TEXT,
            label_printed INTEGER DEFAULT 1,
            scanner_pass INTEGER DEFAULT 1,
            prod_line INTEGER,
            operator_id TEXT
        );

        CREATE TABLE prod_run_totals (
            run_number TEXT PRIMARY KEY REFERENCES prod_runs(run_number),
            total_packs INTEGER,
            total_weight_kg REAL,
            avg_weight_g REAL,
            min_weight_g REAL,
            max_weight_g REAL,
            std_dev_g REAL,
            giveaway_kg REAL,
            giveaway_pct REAL,
            reject_count INTEGER DEFAULT 0,
            downtime_mins INTEGER DEFAULT 0,
            updated_date TEXT
        );

        CREATE TABLE prod_temperature_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            reading_time TEXT NOT NULL,
            temp_celsius REAL NOT NULL,
            target_min REAL DEFAULT -1.0,
            target_max REAL DEFAULT 4.0,
            in_range INTEGER,
            alert_raised INTEGER DEFAULT 0,
            recorded_by TEXT
        );

        CREATE TABLE prod_non_conformance (
            nc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            nc_date TEXT NOT NULL,
            run_number TEXT,
            product_code TEXT,
            nc_type TEXT,
            severity TEXT,
            description TEXT,
            root_cause TEXT,
            corrective_action TEXT,
            raised_by TEXT,
            closed_by TEXT,
            closed_date TEXT,
            status TEXT DEFAULT 'open'
        );

        CREATE TABLE prod_case_verification (
            verify_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_number TEXT,
            case_barcode TEXT,
            expected_plu TEXT,
            scanned_plu TEXT,
            match INTEGER,
            scan_time TEXT,
            scanner_id TEXT,
            prod_line INTEGER
        );

        CREATE TABLE prod_despatch (
            despatch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT,
            customer TEXT,
            product_code TEXT,
            qty_cases INTEGER,
            qty_kg REAL,
            despatch_date TEXT,
            delivery_date TEXT,
            vehicle_temp_c REAL,
            status TEXT DEFAULT 'pending'
        );

        CREATE TABLE prod_shifts (
            shift_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_date TEXT NOT NULL,
            shift_code TEXT NOT NULL,
            line_id INTEGER,
            headcount INTEGER,
            planned_hours REAL,
            actual_hours REAL,
            overtime_hours REAL DEFAULT 0,
            output_kg REAL,
            kg_per_head REAL
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

    # === PRODUCTION ERP SEED DATA ===

    # Production lines
    prod_lines = [
        (1, 'Line 1', 'filleting', 'fresh', 5000),
        (2, 'Line 2', 'filleting', 'fresh', 4500),
        (3, 'Line 3', 'packing', 'fresh', 6000),
        (4, 'Smoke Line', 'smoking', 'smoked', 2000),
        (5, 'VA Line', 'value-added', 'value-added', 3000),
        (6, 'Packing A', 'packing', 'fresh', 5500),
    ]
    for pl in prod_lines:
        c.execute('INSERT INTO prod_lines (line_id, line_name, line_type, area, max_capacity_kg) VALUES (?,?,?,?,?)', pl)

    # Production products (PLU)
    prod_products = [
        ('COD-200-R01', 'Cod Fillet Skinless 200g', 'fillet', 'cod', 'Retail A', 200, 7, 'fish'),
        ('COD-280-R02', 'Cod Loin 280g', 'loin', 'cod', 'Retail B', 280, 7, 'fish'),
        ('SAL-130-R01', 'Salmon Fillet Portion 130g', 'fillet', 'salmon', 'Retail A', 130, 7, 'fish'),
        ('SAL-200-R03', 'Salmon Darnes 200g', 'portion', 'salmon', 'Retail C', 200, 6, 'fish'),
        ('HAD-170-R02', 'Smoked Haddock Fillet 170g', 'smoked', 'haddock', 'Retail B', 170, 10, 'fish'),
        ('MAC-150-R01', 'Mackerel Fillet Peppered 150g', 'smoked', 'mackerel', 'Retail A', 150, 14, 'fish, mustard'),
        ('FCA-300-R02', 'Fish Cakes Cod & Parsley 300g', 'value-add', 'cod', 'Retail B', 300, 5, 'fish, wheat, egg'),
        ('FCA-400-R03', 'Fish Cakes Premium 400g', 'value-add', 'cod', 'Retail C', 400, 5, 'fish, wheat, egg, milk'),
        ('PRN-200-R01', 'King Prawns 200g', 'shellfish', 'prawn', 'Retail A', 200, 5, 'crustaceans'),
        ('SEA-500-R02', 'Seafood Selection 500g', 'mixed', 'mixed', 'Retail B', 500, 4, 'fish, crustaceans, molluscs'),
    ]
    for pp in prod_products:
        c.execute('INSERT INTO prod_products (product_code, description, category, species, customer, pack_size_g, shelf_life_days, allergens) VALUES (?,?,?,?,?,?,?,?)', pp)

    # Traceability batches
    trace_data = [
        ('TR-0401', 'BC-COD-8831', 'North Sea Catch Ltd', 'cod', 'North Sea IV', 'trawl', 'Harvest Moon', '2025-03-28', '2025-03-28', '2025-03-30', 1.2, '2025-04-06', 'UK', 'MSC'),
        ('TR-0402', 'BC-SAL-4421', 'Highland Salmon Co', 'salmon', 'Scotland West', 'farmed', None, '2025-03-29', '2025-03-29', '2025-03-31', 0.8, '2025-04-07', 'UK', 'ASC'),
        ('TR-0403', 'BC-HAD-7712', 'Nordic Fish Supply', 'haddock', 'Norwegian Sea', 'line caught', 'Polar Star', '2025-03-27', '2025-03-27', '2025-03-30', 1.5, '2025-04-08', 'Norway', 'MSC'),
        ('TR-0404', 'BC-COD-8832', 'North Sea Catch Ltd', 'cod', 'North Sea IV', 'trawl', 'Sea Ranger', '2025-04-01', '2025-04-01', '2025-04-02', 1.0, '2025-04-09', 'UK', 'MSC'),
        ('TR-0405', 'BC-MAC-2201', 'Cornish Pelagic Ltd', 'mackerel', 'Celtic Sea VII', 'purse seine', 'Atlantic Spirit', '2025-03-30', '2025-03-30', '2025-04-01', 0.5, '2025-04-14', 'UK', 'MSC'),
        ('TR-0406', 'BC-PRN-5501', 'Pacific Shellfish Co', 'prawn', 'Indian Ocean', 'farmed', None, '2025-02-15', '2025-02-15', '2025-03-20', -18.0, '2025-08-15', 'Vietnam', 'ASC'),
    ]
    for t in trace_data:
        c.execute('INSERT INTO prod_traceability (trace_id, batch_code, supplier, species, catch_area, catch_method, vessel_name, landing_date, kill_date, received_date, received_temp_c, use_by_date, country_origin, certified) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)', t)

    # Production runs (30 days of data)
    run_operators = ['AMORGAN', 'MKOWALSKI', 'PDESAI', 'AKAZLAUSKIENE', 'RPOPESCU']
    run_id = 7200
    run_records = []
    for day_offset in range(30):
        date = today - timedelta(days=day_offset)
        date_str = date.strftime('%Y-%m-%d')
        trace = random.choice(trace_data)

        for run_in_day in range(random.randint(3, 6)):
            run_id += 1
            run_num = f'{run_id:06d}'
            pp = random.choice(prod_products)
            line = random.choice(prod_lines)
            shift = random.choice(['DAY', 'NIGHT'])
            target = round(random.uniform(300, 1200), 0)
            actual = round(target * random.uniform(0.88, 0.99), 1)
            waste = round(target - actual, 1)
            yld = round(actual / target * 100, 1)
            op = random.choice(run_operators)

            c.execute('''INSERT INTO prod_runs
                (run_number, production_date, shift_code, shift_date, prod_line,
                 product_code, spec, prog_id, target_qty_kg, actual_qty_kg,
                 waste_kg, yield_pct, status, complete, kill_date, trace_id,
                 created_by, created_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (run_num, date_str, shift, date_str, line[0],
                 pp[0], f'SP-{pp[3][:3].upper()}-01', f'P{random.randint(1,10):03d}',
                 target, actual, waste, yld, 'complete', 1,
                 trace[7], trace[0], op, date_str))
            run_records.append((run_num, pp, line, actual, target, date_str, op))

            # Generate pack-level transactions (~15-25 per run)
            pack_count = random.randint(15, 25)
            target_wt = pp[5]  # pack_size_g
            for _ in range(pack_count):
                wt = round(target_wt + random.uniform(-8, 12), 1)
                tare = round(random.uniform(3, 8), 1)
                net = round(wt - tare, 1)
                over = round(net - target_wt, 1)
                c.execute('''INSERT INTO prod_transactions
                    (run_number, trans_date, product_code, weight_g,
                     target_weight_g, tare_g, net_weight_g, overweight_g,
                     barcode, prod_line, operator_id)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (run_num, date_str, pp[0], wt, target_wt,
                     tare, net, over, f'5012345{random.randint(100000,999999)}',
                     line[0], op))

            # Run totals (aggregated)
            c.execute('''INSERT INTO prod_run_totals
                (run_number, total_packs, total_weight_kg, avg_weight_g,
                 giveaway_kg, giveaway_pct, reject_count, downtime_mins)
                VALUES (?,?,?,?,?,?,?,?)''',
                (run_num, pack_count, round(actual, 1),
                 round(target_wt + random.uniform(-2, 5), 1),
                 round(waste * 0.3, 1), round(waste / target * 100, 1),
                 random.randint(0, 3), random.randint(0, 15)))

            # Case verification (~5 per run, 95% match rate)
            for _ in range(random.randint(3, 7)):
                scanned = pp[0] if random.random() < 0.95 else random.choice(prod_products)[0]
                c.execute('''INSERT INTO prod_case_verification
                    (run_number, case_barcode, expected_plu, scanned_plu,
                     match, scan_time, scanner_id, prod_line)
                    VALUES (?,?,?,?,?,?,?,?)''',
                    (run_num, f'CS{random.randint(100000,999999)}',
                     pp[0], scanned, 1 if scanned == pp[0] else 0,
                     date_str, f'SCN-{line[0]}', line[0]))

    # Temperature logs (production-specific locations)
    prod_locations = {
        'chiller_1': (-1.0, 4.0, 2.0),
        'chiller_2': (-1.0, 4.0, 2.5),
        'blast_freezer': (-25.0, -18.0, -21.0),
        'goods_in': (-1.0, 5.0, 1.5),
        'despatch': (-1.0, 5.0, 2.0),
    }
    for day_offset in range(30):
        date = today - timedelta(days=day_offset)
        for hour in [6, 10, 14, 18]:
            for loc, (tmin, tmax, base) in prod_locations.items():
                temp = round(base + random.uniform(-1.0, 1.0), 1)
                if random.random() < 0.03:
                    temp = round(tmax + random.uniform(0.5, 3.0), 1)
                in_range = 1 if tmin <= temp <= tmax else 0
                reading_time = date.replace(hour=hour).strftime('%Y-%m-%d %H:%M')
                c.execute('''INSERT INTO prod_temperature_logs
                    (location, reading_time, temp_celsius, target_min, target_max,
                     in_range, recorded_by)
                    VALUES (?,?,?,?,?,?,?)''',
                    (loc, reading_time, temp, tmin, tmax, in_range,
                     random.choice(run_operators)))

    # Non-conformance records
    nc_types = ['weight', 'label', 'foreign_body', 'temp', 'allergen']
    severities = ['minor', 'minor', 'minor', 'major', 'critical']
    nc_statuses = ['closed', 'closed', 'closed', 'investigating', 'open']
    for day_offset in range(30):
        if random.random() < 0.3:
            date = today - timedelta(days=day_offset)
            date_str = date.strftime('%Y-%m-%d')
            run = random.choice(run_records) if run_records else None
            nc_type = random.choice(nc_types)
            sev = random.choice(severities)
            stat = random.choice(nc_statuses)
            closed_date = (date + timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d') if stat == 'closed' else None
            c.execute('''INSERT INTO prod_non_conformance
                (nc_date, run_number, product_code, nc_type, severity,
                 description, raised_by, closed_by, closed_date, status)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (date_str, run[0] if run else None, run[1][0] if run else None,
                 nc_type, sev, f'{nc_type} issue on {date_str}',
                 random.choice(run_operators),
                 random.choice(run_operators) if stat == 'closed' else None,
                 closed_date, stat))

    # Despatch records
    desp_customers = ['Retail A', 'Retail B', 'Retail C', 'Wholesale D']
    for day_offset in range(30):
        if random.random() < 0.6:
            date = today - timedelta(days=day_offset)
            pp = random.choice(prod_products)
            c.execute('''INSERT INTO prod_despatch
                (order_number, customer, product_code, qty_cases, qty_kg,
                 despatch_date, delivery_date, vehicle_temp_c, status)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                (f'ORD-{random.randint(10000,99999)}', random.choice(desp_customers),
                 pp[0], random.randint(20, 200), round(random.uniform(100, 800), 1),
                 date.strftime('%Y-%m-%d'),
                 (date + timedelta(days=1)).strftime('%Y-%m-%d'),
                 round(random.uniform(0.5, 3.5), 1),
                 random.choice(['delivered', 'delivered', 'loaded', 'pending'])))

    # Shift records
    for day_offset in range(30):
        date = today - timedelta(days=day_offset)
        for shift in ['DAY', 'NIGHT']:
            for line in prod_lines[:4]:
                hc = random.randint(6, 12)
                planned = hc * 8.0
                actual = round(planned + random.uniform(-2, 4), 1)
                ot = max(0, round(actual - planned, 1))
                output = round(random.uniform(300, 1000), 1)
                c.execute('''INSERT INTO prod_shifts
                    (shift_date, shift_code, line_id, headcount,
                     planned_hours, actual_hours, overtime_hours,
                     output_kg, kg_per_head)
                    VALUES (?,?,?,?,?,?,?,?,?)''',
                    (date.strftime('%Y-%m-%d'), shift, line[0], hc,
                     planned, actual, ot, output,
                     round(output / hc, 1)))

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
    print('  --- Production ERP tables ---')
    print(f'  Prod lines: {len(prod_lines)}')
    print(f'  Prod products (PLU): {len(prod_products)}')
    print(f'  Prod runs: {len(run_records)}')
    print(f'  Prod traceability: {len(trace_data)}')
    print(f'  Prod temperature logs: {30 * 4 * 5}')
    print('  Total tables: 19')


if __name__ == '__main__':
    seed()
