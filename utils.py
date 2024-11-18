# Here are the common functions that may be used in different files
import sqlite3
from flask import session
from datetime import datetime

# Initialize the database
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Delete the database when start
    c.execute('DROP TABLE IF EXISTS products')

    # Create the products table
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            manufacturer TEXT,
            price REAL,
            description TEXT,
            removed BOOLEAN NOT NULL DEFAULT 0
        )
    ''')

    # Create the manufacturers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    # Create the warehouse inventory table
    c.execute('''
        CREATE TABLE IF NOT EXISTS warehouse (
            id INTEGER PRIMARY KEY,
            quantity INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (id) REFERENCES products (id)
        )
    ''')
    
    # Create the users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create the admin user
    c.execute('''
        INSERT INTO users (username, password)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET password = excluded.password
    ''', ("admin", "toan5987ng"))

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
