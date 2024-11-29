# Here are the common functions that may be used in different files
import sqlite3
from flask import session
from datetime import datetime

# Initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Create the users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            removed BOOLEAN NOT NULL DEFAULT 0 -- Do not remove the user in database, because it is needed to generate reports dynamically
        )
    ''')

    # Create the admin user
    c.execute('''
        INSERT INTO users (username, password)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET password = excluded.password
    ''', ("admin", "hsbochum!"))

    # Create the manufacturers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            removed BOOLEAN NOT NULL DEFAULT 0 -- Do not remove the manufacturer in database, because it is needed to generate reports dynamically
        )
    ''')
    
    # Create the products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            manufacturer_id INTEGER NOT NULL,  -- Foreign key for manufacturer
            price DECIMAL(10, 2) NOT NULL,
            description TEXT,
            removed BOOLEAN NOT NULL DEFAULT 0, -- Do not remove the product in database, because it is needed to generate reports dynamically              
            FOREIGN KEY (manufacturer_id) REFERENCES manufacturers (id)
        )
    ''')

    # Create the price history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price DECIMAL(10, 2),
            new_price DECIMAL(10, 2) NOT NULL,
            change_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # Create the inventory table
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique ID for each inventory entry
            product_id INTEGER NOT NULL, -- Refers to the product
            manufacturer_id INTEGER NOT NULL, -- Refers to the manufacturer
            price DECIMAL(10, 2) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            expiry_date DATE NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (manufacturer_id) REFERENCES manufacturers (id)
        )
    ''')

    # Create the purchase transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_transactions (
            purchase_transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer_id INTEGER NOT NULL,    -- Reference to manufacturer (supplier)
            transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            total_price DECIMAL(10, 2) NOT NULL, -- Total cost of the purchased products
            invoice_number TEXT NOT NULL UNIQUE,        -- Invoice number for external reference
            FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
        )
    ''')

    # Create the purchase transaction items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_transaction_id INTEGER NOT NULL,   -- Link to the purchase transaction
            product_id INTEGER NOT NULL,                -- Product purchased
            quantity INTEGER NOT NULL,                  -- Quantity of the product
            price DECIMAL(10, 2) NOT NULL,                        -- Price per unit
            expiry_date DATE NOT NULL,
            FOREIGN KEY (purchase_transaction_id) REFERENCES purchase_transactions(purchase_transaction_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Add indexes to improve performance when querying by product_id and purchase_transaction_id
    c.execute('CREATE INDEX IF NOT EXISTS idx_purchase_transaction_items_product_id ON purchase_transaction_items(product_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_purchase_transaction_items_purchase_transaction_id ON purchase_transaction_items(purchase_transaction_id)')

    conn.commit()
    conn.close()

# Connect to the database
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Write an action in the activity log
def log_activity(activity):
    username = session.get('username', 'Unknown User')
    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    with open('activity_log.txt', 'a') as f:
        f.write(f'{timestamp} {username} {activity}\n')

# Add products to inventory, be used by Import Inventory and Add Purchase Transaction
def handle_import_inventory(product_id, quantity, expiry_date):
    with get_db_connection() as conn:
        c = conn.cursor()

        # Get product_name, manufacturer_id and price from product_id
        c.execute('''
            SELECT name, manufacturer_id, price
            FROM products
            WHERE id = ?
        ''', (product_id,))
        product_data = c.fetchone()

        if not product_data:
            raise ValueError(f"Product with ID {product_id} does not exist.")

        product_name, manufacturer_id, price = product_data

        # Check if the same product with the same expiry date exists in inventory
        c.execute('''
            SELECT inventory_id, quantity
            FROM inventory
            WHERE product_id = ? AND expiry_date = ?
        ''', (product_id, expiry_date))
        existing_inventory = c.fetchone()

        if existing_inventory:
            inventory_id, current_quantity = existing_inventory
            new_quantity = current_quantity + quantity
            # Update the quantity
            c.execute('''
                UPDATE inventory
                SET quantity = ?
                WHERE inventory_id = ?
            ''', (new_quantity, inventory_id))
            log_activity(f"imported additional {quantity} {product_name} (ID: {product_id}) with expiry date {expiry_date} (New total: {new_quantity})")
        else:
            # Insert a new inventory record
            c.execute('''
                INSERT INTO inventory (product_id, manufacturer_id, price, quantity, expiry_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, manufacturer_id, price, quantity, expiry_date))
            log_activity(f"imported {quantity} {product_name} (ID: {product_id}) with expiry date {expiry_date}")

        conn.commit()
