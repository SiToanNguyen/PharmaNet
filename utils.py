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
    ''', ("admin", "toan5987ng"))

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
            manufacturer_id INTEGER,  -- Foreign key for manufacturer
            price REAL,
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
            old_price REAL,
            new_price REAL,
            change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # Create the inventory table
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique ID for each inventory entry
            product_id INTEGER NOT NULL, -- Refers to the product
            manufacturer_id INTEGER NOT NULL, -- Refers to the manufacturer
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            expiry_date DATE NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (manufacturer_id) REFERENCES manufacturers (id)
        )
    ''')

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
