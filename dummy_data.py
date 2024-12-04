import hashlib
import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta
from utils import init_db, get_db_connection

def drop_tables():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Drop tables if they exist
        c.execute('DROP TABLE IF EXISTS users')
        print("users table has been dropped.")

        c.execute('DROP TABLE IF EXISTS manufacturers')
        print("manufacturers table has been dropped.")

        c.execute('DROP TABLE IF EXISTS products')
        print("products table has been dropped.")

        c.execute('DROP TABLE IF EXISTS price_history')
        print("price_history table has been dropped.")

        c.execute('DROP TABLE IF EXISTS inventory')
        print("inventory table has been dropped.")

        c.execute('DROP TABLE IF EXISTS purchase_transactions')
        print("purchase_transactions table has been dropped.")

        c.execute('DROP TABLE IF EXISTS purchase_transaction_items')
        print("purchase_transaction_items table has been dropped.")
        
        c.execute('DROP TABLE IF EXISTS sale_transactions')
        print("sale_transactions table has been dropped.")

        c.execute('DROP TABLE IF EXISTS sale_transaction_items')
        print("sale_transaction_items table has been dropped.")

        # Commit the changes and close the connection
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the connection is closed even if an error occurs
        if conn:
            conn.close()

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Insert users
def insert_users():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Insert the users with hashed passwords
        users = [
            ('admin', 'hsbochum!'),
            ('koehn', 'KhZamBASe18!'),
            ('toan', 'toan5987ng')
        ]

        for username, password in users:
            hashed_password = hash_password(password)
            # Insert user data into the users table
            c.execute('''
                INSERT INTO users (username, password)
                VALUES (?, ?)
            ''', (username, hashed_password))

        # Commit the changes
        conn.commit()
        print("Users have been added successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the connection is closed even if an error occurs
        if conn:
            conn.close()

# Insert dummy manufacturers
def insert_manufacturers():
    try:
        # Get the database connection
        conn = get_db_connection()
        c = conn.cursor()

        # Dummy data for manufacturers
        manufacturers = [
            ('PharmaTech', 'Specializes in high-quality pharmaceutical products for hospitals and clinics.'),
            ('MediSupply', 'Provides a wide range of over-the-counter medications and medical supplies.'),
            ('HealthPlus Pharma', 'Focuses on providing herbal supplements and wellness products.')
        ]

        # Insert the manufacturers into the manufacturers table
        c.executemany('''
            INSERT INTO manufacturers (name, description) 
            VALUES (?, ?)
        ''', manufacturers)

        print("Manufacturers have been added successfully.")

        # Commit the changes and close the connection
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the connection is closed even if an error occurs
        if conn:
            conn.close()

# Insert dummy products
def insert_products():
    try:
        # Get the database connection
        conn = get_db_connection()
        c = conn.cursor()

        # Dummy products for each manufacturer
        products_data = [
            ("Aspirin 500mg", 1, 5.99, "Pain relief medication"),
            ("Paracetamol 500mg", 1, 4.49, "Fever and pain relief"),
            ("Ibuprofen 200mg", 1, 7.99, "Anti-inflammatory medication"),
            
            ("Cough Syrup", 2, 8.99, "Cough and cold relief"),
            ("Vitamin C 1000mg", 2, 12.49, "Immune support supplement"),
            ("Cough Tablets", 2, 5.79, "Cough suppression tablets"),
            
            ("Antibiotic Ointment", 3, 3.99, "Topical antibiotic ointment"),
            ("Band-Aids", 3, 2.49, "Adhesive bandages"),
            ("Disinfectant Spray", 3, 6.99, "Surface disinfectant spray")
        ]

        # Insert each dummy product into the products table
        for product in products_data:
            name, manufacturer_id, price, description = product
            c.execute('''
                INSERT INTO products (name, manufacturer_id, price, description, removed)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, manufacturer_id, price, description, 0))  # removed set to 0

        print("Products have been added successfully.")

        # Commit the changes and close the connection
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

# Generate random date
def random_date_in_month(year, month):
    """Generate a random date within a specific month."""
    if month < 1 or month > 12:
        raise ValueError("Month must be between 1 and 12.")
        
    # Find the first day of the month
    start_date = datetime(year, month, 1)
    
    # Find the last day of the month by moving to the first day of the next month and subtracting a day
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Randomly select a day within the range
    random_days = random.randint(0, (end_date - start_date).days)
    random_date = start_date + timedelta(days=random_days)
    
    # Return the random date as a date object (it will have no time part)
    return random_date.date()

# Insert purchase transactions
def insert_purchase_transactions():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Get manufacturers
        c.execute("SELECT id FROM manufacturers")
        manufacturers = c.fetchall()

        # Insert 2 purchase transactions for each manufacturer
        for manufacturer in manufacturers:
            manufacturer_id = manufacturer[0]

            # Create two purchase transactions for this manufacturer
            for i in range(2):
                # Random transaction date in different months
                month = random.randint(1, 12)
                year = random.randint(2025, 2035)
                transaction_date = random_date_in_month(2024, month)

                # Generate invoice number
                invoice_number = f"INV{random.randint(1000, 9999)}"

                # Get random products for this manufacturer
                c.execute('''
                    SELECT id, price FROM products WHERE manufacturer_id = ?
                ''', (manufacturer_id,))
                products = c.fetchall()

                # Select random products and create purchase transaction items
                total_price = 0
                items = []
                for product in products:
                    product_id, price = product
                    quantity = random.randint(1, 50)  # Random quantity
                    expiry_date = random_date_in_month(year, month)  # Random expiry date

                    # Add to the purchase transaction items list
                    total_price += price * quantity
                    items.append((product_id, quantity, price, expiry_date))

                # Insert purchase transaction
                c.execute('''
                    INSERT INTO purchase_transactions (manufacturer_id, transaction_date, total_price, invoice_number)
                    VALUES (?, ?, ?, ?)
                ''', (manufacturer_id, transaction_date, total_price, invoice_number))
                purchase_transaction_id = c.lastrowid  # Get the ID of the inserted purchase transaction

                # Insert purchase transaction items
                for item in items:
                    product_id, quantity, price, expiry_date = item
                    c.execute('''
                        INSERT INTO purchase_transaction_items (purchase_transaction_id, product_id, quantity, price, expiry_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (purchase_transaction_id, product_id, quantity, price, expiry_date))

                    # Insert into inventory table
                    c.execute('''
                        INSERT INTO inventory (product_id, quantity, expiry_date)
                        VALUES (?, ?, ?)
                    ''', (product_id, quantity, expiry_date))

                print(f"Purchase transaction {invoice_number} for manufacturer {manufacturer_id} has been added successully.")

        # Commit the changes and close the connection
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

# Insert sale transactions
def insert_sale_transactions():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        fake = Faker('de_DE') # Generate a random German name
        name = fake.first_name() + " " + fake.last_name()

        # Create 5 sale transactions
        for i in range(5):
            # Transaction date (random day in 2024)
            transaction_date = random_date_in_month(2024, random.randint(1, 12))

            # Determine if this transaction has a customer and prescription
            if i == 4:  # 5th transaction has customer and prescription
                customer_name = name
                prescription_notes = "Prescription notes example"
            else:
                customer_name = None
                prescription_notes = None

            # Fetch inventory items with non-zero quantities
            c.execute("SELECT inventory_id, product_id, quantity, expiry_date FROM inventory WHERE quantity > 0")
            inventory_items = c.fetchall()

            if not inventory_items:
                print("No inventory items available for sale.")
                return

            total_price = 0
            items = []

            # Select random inventory items for the sale
            num_items = random.randint(1, min(3, len(inventory_items)))  # Up to 3 items per transaction
            selected_items = random.sample(inventory_items, num_items)

            for inventory_item in selected_items:
                inventory_id, product_id, available_quantity, expiry_date = inventory_item
                sold_quantity = random.randint(1, available_quantity)  # Quantity sold (<= available quantity)

                # Get the price of the product
                c.execute("SELECT price FROM products WHERE id = ?", (product_id,))
                product_price = c.fetchone()[0]

                # Calculate total price for this item
                total_price += sold_quantity * product_price

                # Prepare item for insertion into sale_transaction_items
                items.append((inventory_id, sold_quantity, product_price, expiry_date))

                # Update inventory quantity
                new_quantity = available_quantity - sold_quantity
                c.execute("UPDATE inventory SET quantity = ? WHERE inventory_id = ?", (new_quantity, inventory_id))

            # Insert sale transaction
            c.execute('''
                INSERT INTO sale_transactions (customer_name, prescription_notes, transaction_date, total_price)
                VALUES (?, ?, ?, ?)
            ''', (customer_name, prescription_notes, transaction_date, total_price))
            sale_transaction_id = c.lastrowid

            # Insert items into sale_transaction_items
            for item in items:
                inventory_id, sold_quantity, product_price, expiry_date = item
                c.execute('''
                    INSERT INTO sale_transaction_items (sale_transaction_id, inventory_id, quantity, price, expiry_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sale_transaction_id, inventory_id, sold_quantity, product_price, expiry_date))

            print(f"Sale transaction {sale_transaction_id} added successfully.")

        # Commit changes and close the connection
        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # drop_tables()
    init_db()
    insert_users()
    insert_manufacturers()
    insert_products()
    insert_purchase_transactions()
    insert_sale_transactions()
