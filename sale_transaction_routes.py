from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils import get_db_connection, log_activity
from datetime import datetime
import sqlite3
from collections import defaultdict

sale_transaction_bp = Blueprint('sale_transaction', __name__)

@sale_transaction_bp.route('/sale_transaction', methods=['GET', 'POST'])
def sale_transaction_page():
    if request.method == 'POST':
        error = add_sale_transaction_page(request.form)
        if error:
            return render_template('sale_transaction.html', error_message=error)

    transactions = fetch_filtered_transactions(request.args)
    # transactions = fetch_all_transactions()
    return render_template('sale_transaction.html', sale_transactions=transactions)

# Route to add a sale transaction
@sale_transaction_bp.route('/add-sale-transaction', methods=['GET', 'POST'])
def add_sale_transaction_page():
    if request.method == 'POST':
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            customer_name = request.form['customer_name']
            prescription_notes = request.form['prescription_notes']
            transaction_date = request.form['transaction_date']

            products = request.form.getlist('product[]')  # List of selected product IDs
            quantities = request.form.getlist('quantity[]')  # List of quantities sold
            expiry_dates = request.form.getlist('expiry_date[]')  # List of selected expiry dates

            total_price = 0
            inventory_details = get_inventory_details()

            # Calculate total price and validate inventory
            for i, product_id in enumerate(products):
                quantity = int(quantities[i])
                product = next((item for item in inventory_details if item['product_id'] == int(product_id)), None)
                if product:
                    total_price += product['price'] * quantity
                else:
                    return render_template('add_sale_transaction.html', error_message=f"Product ID {product_id} not found.")

            # Insert transaction
            cursor.execute('''
                INSERT INTO sale_transactions (customer_name, prescription_notes, transaction_date, total_price)
                VALUES (?, ?, ?, ?)
            ''', (customer_name, prescription_notes, transaction_date, total_price))

            # Get the last inserted transaction ID
            cursor.execute('SELECT last_insert_rowid()')
            sale_transaction_id = cursor.fetchone()[0]

            log_activity(f"added the sale transaction ID: {sale_transaction_id}")

            # Insert transaction items
            for i, product_id in enumerate(products):
                expiry_date = expiry_dates[i]
                quantity = int(quantities[i])
                price = next((item["price"] for item in inventory_details if item["product_id"] == int(product_id)), 0)

                # Retrieve the inventory_id
                cursor.execute('''
                    SELECT inventory_id FROM inventory
                    WHERE product_id = ? AND expiry_date = ?
                ''', (product_id, expiry_date))
                inventory_id_row = cursor.fetchone()
                
                if not inventory_id_row:
                    raise ValueError(f"No inventory record found for Product ID {product_id} with Expiry Date {expiry_date}.")
                
                inventory_id = inventory_id_row[0]

                cursor.execute('''
                    INSERT INTO sale_transaction_items (sale_transaction_id, inventory_id, price, quantity, expiry_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (sale_transaction_id, inventory_id, price, quantity, expiry_date))

                # Update the inventory quantity
                cursor.execute('''
                    UPDATE inventory
                    SET quantity = quantity - ?
                    WHERE inventory_id = ?
                ''', (quantity, inventory_id))

                # Retrieve product name using product_id
                cursor.execute('''
                    SELECT name FROM products
                    WHERE id = ?
                ''', (product_id,))
                product_name_row = cursor.fetchone()

                if not product_name_row:
                    raise ValueError(f"No product found with Product ID {product_id}.")
                
                product_name = product_name_row[0]

                log_activity(f"removed {quantity} {product_name} (ID: {sale_transaction_id})")

            conn.commit()
            return redirect(url_for('sale_transaction.sale_transaction_page'))

        except Exception as e:
            print(f"Error in transaction: {e}")
            if conn:
                conn.rollback()
            return render_template('add_sale_transaction.html', error_message="An error occurred during the transaction.")

        finally:
            if conn:
                conn.close()

    return render_template(
        'add_sale_transaction.html',
        manufacturers=get_manufacturers(),
        inventory=get_inventory_details() or []
    )

def fetch_all_transactions():
    with get_db_connection() as conn:
        return conn.execute('''
            SELECT sale_transaction_id AS id, customer_name, prescription_notes, transaction_date, total_price
            FROM sale_transactions
        ''').fetchall()

@sale_transaction_bp.route('/sale_transaction/products/<int:transaction_id>', methods=['GET'])
def get_sale_transaction_products(transaction_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT 
                    p.name AS product_name, 
                    si.price, 
                    si.quantity, 
                    si.expiry_date
                FROM sale_transaction_items si
                JOIN inventory i ON si.inventory_id = i.inventory_id
                JOIN products p ON i.product_id = p.id
                WHERE si.sale_transaction_id = ?
            '''
            rows = cursor.execute(query, (transaction_id,)).fetchall()

        products = [
            {
                'product_name': row['product_name'],
                'price': row['price'],
                'quantity': row['quantity'],
                'expiry_date': row['expiry_date']
            }
            for row in rows
        ]

        return jsonify(products)

    except Exception as e:
        print(f"Error fetching products for transaction {transaction_id}: {e}")
        return jsonify({'error': 'An error occurred while fetching the products.'}), 500

def get_inventory_details():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            p.id AS product_id,
            p.name AS product_name,
            p.price AS price,
            m.id AS manufacturer_id,
            m.name AS manufacturer_name,
            i.expiry_date AS expiry_date,
            i.quantity AS quantity
        FROM 
            products p
        JOIN 
            manufacturers m ON p.manufacturer_id = m.id
        JOIN 
            inventory i ON i.product_id = p.id
        WHERE 
            i.quantity > 0
    ''')
    
    raw_inventory = cursor.fetchall()
    conn.close()

    grouped_inventory = defaultdict(lambda: {
        "product_id": None,
        "product_name": None,
        "price": None,
        "manufacturer_id": None,
        "manufacturer_name": None,
        "expiry_dates": []
    })
    
    for row in raw_inventory:
        product = grouped_inventory[row["product_id"]]
        product.update({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "price": row["price"],
            "manufacturer_id": row["manufacturer_id"],
            "manufacturer_name": row["manufacturer_name"]
        })
        product["expiry_dates"].append({
            "expiry_date": row["expiry_date"],
            "quantity": row["quantity"]
        })
    
    return list(grouped_inventory.values())

def get_manufacturers():
    with get_db_connection() as conn:
        return conn.execute('SELECT id, name FROM manufacturers WHERE removed = 0').fetchall()

def fetch_filtered_transactions(args):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Base query with correct aliasing
    query = '''
        SELECT 
            sale_transaction_id AS id, 
            customer_name, 
            prescription_notes, 
            transaction_date, 
            total_price
        FROM sale_transactions
        WHERE 1=1
    '''
    params = []

    # Apply filters
    if 'customer' in args and args['customer']:
        query += " AND customer_name LIKE ?"
        params.append(f"%{args['customer']}%")
    if 'prescription' in args and args['prescription']:
        query += " AND prescription_notes LIKE ?"
        params.append(f"%{args['prescription']}%")
    if 'from_date' in args and args['from_date']:
        query += " AND transaction_date >= ?"
        params.append(args['from_date'])
    if 'to_date' in args and args['to_date']:
        query += " AND transaction_date <= ?"
        params.append(args['to_date'])

    # Execute the query
    cursor.execute(query, params)
    transactions = cursor.fetchall()

    conn.close()
    return transactions
