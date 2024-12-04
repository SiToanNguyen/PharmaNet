from flask import Blueprint, render_template, request, redirect, url_for
from utils import get_db_connection, log_activity
from datetime import datetime

sale_transaction_bp = Blueprint('sale_transaction', __name__)

@sale_transaction_bp.route('/sale_transaction', methods=['GET', 'POST'])
def sale_transaction_page():
    if request.method == 'POST':
        error = add_sale_transaction(request.form)
        if error:
            return render_template('sale_transaction.html', error_message=error)

    transactions = fetch_all_transactions()
    return render_template('sale_transaction.html', sale_transactions=transactions)

@sale_transaction_bp.route('/sale_transaction/add', methods=['GET', 'POST'])
def add_sale_transaction_page():
    manufacturers = fetch_manufacturers()
    inventory = fetch_inventory()

    if request.method == 'POST':
        error = add_sale_transaction(request.form)
        if error:
            return render_template('add_sale_transaction.html', manufacturers=manufacturers, inventory=inventory, error_message=error)
        return redirect(url_for('sale_transaction.sale_transaction_page'))

    return render_template('add_sale_transaction.html', manufacturers=manufacturers, inventory=inventory)

def add_sale_transaction(form):
    try:
        customer_name = form.get('customer_name')
        prescription_notes = form.get('prescription_notes')
        transaction_date = form.get('transaction_date') or datetime.now().strftime('%Y-%m-%d')

        product_data = zip(
            form.getlist('manufacturer_id[]'),
            form.getlist('product_id[]'),
            form.getlist('expiry_date[]'),
            form.getlist('quantity[]'),
        )
        
        if not product_data:
            return "Please select at least one product."

        with get_db_connection() as conn:
            cursor = conn.cursor()
            total_price = 0
            items = []

            for manufacturer_id, product_id, expiry_date, quantity in product_data:
                product = cursor.execute(
                    'SELECT p.name, p.price FROM products p WHERE p.id = ? AND p.manufacturer_id = ?',
                    (product_id, manufacturer_id)
                ).fetchone()

                if product:
                    total_price += float(product['price']) * int(quantity)
                    items.append({
                        'product_id': product_id,
                        'manufacturer_id': manufacturer_id,
                        'product_name': product['name'],
                        'price': product['price'],
                        'quantity': quantity,
                        'expiry_date': expiry_date,
                    })

            transaction_id = cursor.execute(
                'INSERT INTO sale_transactions (customer_name, prescription_notes, transaction_date, total_price) VALUES (?, ?, ?, ?)',
                (customer_name, prescription_notes, transaction_date, total_price)
            ).lastrowid

            for item in items:
                cursor.execute(
                    '''
                    INSERT INTO sale_transaction_items 
                    (sale_transaction_id, product_id, manufacturer_id, product_name, price, quantity, expiry_date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (transaction_id, item['product_id'], item['manufacturer_id'], item['product_name'], item['price'], item['quantity'], item['expiry_date'])
                )
                cursor.execute(
                    'UPDATE inventory SET quantity = quantity - ? WHERE product_id = ? AND expiry_date = ?',
                    (item['quantity'], item['product_id'], item['expiry_date'])
                )

            conn.commit()
            log_activity(f"added sale transaction ID: {transaction_id}, Customer: {customer_name}")
        return None

    except Exception as e:
        print(f"Error adding sale transaction: {e}")
        return "An error occurred while saving the transaction."

def fetch_inventory():
    with get_db_connection() as conn:
        rows = conn.execute('''
            SELECT 
                i.product_id, p.name AS product_name, p.manufacturer_id, p.price, i.expiry_date, i.quantity
            FROM inventory i
            JOIN products p ON i.product_id = p.id
            WHERE i.quantity > 0
        ''').fetchall()

        inventory = {}
        for row in rows:
            product_id = row['product_id']
            inventory.setdefault(product_id, {
                'product_id': product_id,
                'product_name': row['product_name'],
                'manufacturer_id': row['manufacturer_id'],
                'price': row['price'],
                'expiry_dates': []
            })['expiry_dates'].append({
                'expiry_date': row['expiry_date'],
                'quantity': row['quantity']
            })
        return list(inventory.values())

def fetch_all_transactions():
    with get_db_connection() as conn:
        return conn.execute('''
            SELECT sale_transaction_id AS id, customer_name, prescription_notes, transaction_date, total_price
            FROM sale_transactions
        ''').fetchall()

def fetch_manufacturers():
    with get_db_connection() as conn:
        return conn.execute('SELECT id, name FROM manufacturers WHERE removed = 0').fetchall()
