# Here are the common functions that may be used in different files
import sqlite3, hashlib
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
            purchase_price DECIMAL(10, 2) NOT NULL,
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
            quantity INTEGER NOT NULL DEFAULT 0,
            expiry_date DATE NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id)
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

    c.execute('CREATE INDEX IF NOT EXISTS idx_purchase_transaction_items_product_id ON purchase_transaction_items(product_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_purchase_transaction_items_purchase_transaction_id ON purchase_transaction_items(purchase_transaction_id)')

    # Create the sale transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sale_transactions (
            sale_transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,                            -- Customer name (can be empty)
            prescription_notes TEXT,                       -- Prescription notes (can be empty)
            transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- Date of transaction
            total_price DECIMAL(10, 2) NOT NULL,           -- Total cost of the products sold
            FOREIGN KEY (customer_name) REFERENCES customers(name) -- If customers table exists
        )
    ''')

    # Create the sale transaction items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sale_transaction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_transaction_id INTEGER NOT NULL,         -- Link to the sale transaction
            inventory_id INTEGER NOT NULL,                 -- Inventory reference (instead of product_id)
            quantity INTEGER NOT NULL,                     -- Quantity of the product sold
            price DECIMAL(10, 2) NOT NULL,                        -- Price per unit
            expiry_date DATE NOT NULL,
            FOREIGN KEY (sale_transaction_id) REFERENCES sale_transactions(sale_transaction_id),
            FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id)
        )
    ''')

    # c.execute('CREATE INDEX IF NOT EXISTS idx_sale_transaction_items_product_id ON sale_transaction_items(product_id)')
    # c.execute('CREATE INDEX IF NOT EXISTS idx_sale_transaction_items_sale_transaction_id ON sale_transaction_items(sale_transaction_id)')


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


def hash_password(password):
    # Hash a password using SHA256.
    return hashlib.sha256(password.encode('utf-8')).hexdigest()