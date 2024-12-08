from flask import Blueprint, render_template, request, redirect, url_for
from utils import get_db_connection, log_activity
from datetime import datetime

purchase_transaction_bp = Blueprint('purchase_transaction', __name__)

@purchase_transaction_bp.route('/purchase_transaction', methods=['GET', 'POST'])
def purchase_transaction_page():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Extract search parameters
    invoice = request.args.get('invoice', '').strip()
    manufacturer = request.args.get('manufacturer', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    # Base query
    query = '''
        SELECT 
            pt.purchase_transaction_id AS id, 
            pt.invoice_number, 
            m.name AS manufacturer_name, 
            pt.transaction_date, 
            pt.total_price
        FROM 
            purchase_transactions AS pt
        JOIN 
            manufacturers AS m ON pt.manufacturer_id = m.id
        WHERE 1=1
    '''
    params = []

    # Add filters for invoice
    if invoice:
        query += " AND pt.invoice_number LIKE ?"
        params.append(f"%{invoice}%")

    # Add filters for manufacturer
    if manufacturer:
        query += " AND m.name LIKE ?"
        params.append(f"%{manufacturer}%")

    # Add filters for date range
    if from_date:
        query += " AND pt.transaction_date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND pt.transaction_date <= ?"
        params.append(to_date)

    # Execute query
    cursor.execute(query, params)
    transactions = cursor.fetchall()
    conn.close()

    return render_template(
        'purchase_transaction.html',
        purchase_transactions=transactions
    )

@purchase_transaction_bp.route('/purchase_transaction/add', methods=['GET', 'POST'])
def add_purchase_transaction_page():
    manufacturers = get_all_manufacturers()
    manufacturer_products = {
        m['id']: [dict(product) for product in get_products_by_manufacturer(m['id'])]
        for m in manufacturers
    }

    if request.method == 'POST':
        error_message = handle_add_purchase_transaction(request.form)
        if error_message:
            return render_template(
                'add_purchase_transaction.html',
                manufacturers=manufacturers,
                manufacturer_products=manufacturer_products,
                error_message=error_message,
            )
        return redirect(url_for('purchase_transaction.purchase_transaction_page'))

    return render_template(
        'add_purchase_transaction.html',
        manufacturers=manufacturers,
        manufacturer_products=manufacturer_products,
    )

def handle_add_purchase_transaction(form_data):
    # Processes the form data to add a new purchase transaction
    try:
        manufacturer_id = form_data.get('manufacturer_id')
        invoice_number = form_data.get('invoice_number')
        transaction_date = form_data.get('transaction_date') or datetime.now().strftime('%Y-%m-%d')
        products = form_data.getlist('product_id[]')
        quantities = form_data.getlist('quantity[]')
        prices = form_data.getlist('price[]')
        expiry_dates = form_data.getlist('expiry_date[]')

        if not manufacturer_id or not invoice_number or not products:
            return "All fields must be filled."

        # Check if the invoice number already exists
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM purchase_transactions WHERE invoice_number = ?', (invoice_number,))
            existing_invoice = c.fetchone()
            if existing_invoice:
                return f"Invoice number {invoice_number} already exists. Please provide a unique invoice number."

            # Calculate the total price by summing up the price * quantity for each product
            total_price = sum(float(price) * int(quantity) for price, quantity in zip(prices, quantities))

            c.execute(
                'INSERT INTO purchase_transactions (manufacturer_id, invoice_number, transaction_date, total_price) VALUES (?, ?, ?, ?)',
                (manufacturer_id, invoice_number, transaction_date, total_price)
            )
            transaction_id = c.lastrowid

            # Process each product in the transaction
            for product_id, quantity, price, expiry_date in zip(products, quantities, prices, expiry_dates):
                # Insert into purchase_transaction_items
                c.execute(
                    'INSERT INTO purchase_transaction_items (purchase_transaction_id, product_id, quantity, price, expiry_date) VALUES (?, ?, ?, ?, ?)',
                    (transaction_id, product_id, quantity, price, expiry_date)
                )

                # Get the product name for logging
                c.execute('SELECT name FROM products WHERE id = ?', (product_id,))
                product_name = c.fetchone()[0]  # Fetch product name directly

                # Handle inventory update
                c.execute('''
                    SELECT inventory_id, quantity
                    FROM inventory
                    WHERE product_id = ? AND expiry_date = ?
                ''', (product_id, expiry_date))
                existing_inventory = c.fetchone()

                if existing_inventory:
                    inventory_id, current_quantity = existing_inventory
                    new_quantity = current_quantity + int(quantity)
                    c.execute('''
                        UPDATE inventory
                        SET quantity = ?
                        WHERE inventory_id = ?
                    ''', (new_quantity, inventory_id))
                    log_activity(f"updated inventory entry {inventory_id} with {quantity} {product_name} (ID: {product_id}) (New total: {new_quantity})")
                else:
                    c.execute('''
                        INSERT INTO inventory (product_id, quantity, expiry_date)
                        VALUES (?, ?, ?)
                    ''', (product_id, quantity, expiry_date))
                    log_activity(f"added new inventory entry with {quantity} {product_name} (ID: {product_id}))")

            conn.commit()
            log_activity(f"added purchase transaction ID: {transaction_id}, invoice number: {invoice_number}")
            
        return None
    except Exception as e:
        print("Error:", e)
        return "An error occurred while saving the transaction."

def get_all_manufacturers():
    # Get all active manufacturers
    with get_db_connection() as conn:
        return conn.execute('SELECT id, name FROM manufacturers WHERE removed = 0').fetchall()

def get_products_by_manufacturer(manufacturer_id):
    # Get all active products of the selected manufacturer
    with get_db_connection() as conn:
        return conn.execute(
            'SELECT id, name, purchase_price FROM products WHERE manufacturer_id = ? AND removed = 0',
            (manufacturer_id,)
        ).fetchall()

def get_all_purchase_transactions():
    # Get all purchase transactions
    with get_db_connection() as conn:
        return conn.execute(
            '''
            SELECT 
                t.purchase_transaction_id AS id,
                t.invoice_number,
                m.name AS manufacturer_name,
                t.transaction_date,
                SUM(pp.quantity * pp.price) AS total_price
            FROM 
                purchase_transactions t
            JOIN 
                manufacturers m ON t.manufacturer_id = m.id
            JOIN 
                purchase_transaction_items pp ON t.purchase_transaction_id = pp.purchase_transaction_id
            GROUP BY 
                t.purchase_transaction_id
            '''
        ).fetchall()

@purchase_transaction_bp.route('/purchase_transaction/products/<int:transaction_id>', methods=['GET'])
def get_products_by_transaction(transaction_id):
    # Get the list of products for a specific purchase transaction
    with get_db_connection() as conn:
        products = conn.execute('''
            SELECT 
                p.name, pp.price, pp.quantity, pp.expiry_date
            FROM 
                purchase_transaction_items pp
            JOIN 
                products p ON pp.product_id = p.id
            WHERE 
                pp.purchase_transaction_id = ?
        ''', (transaction_id,)).fetchall()
        return [dict(product) for product in products]