from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils import get_db_connection, log_activity

inventory_bp = Blueprint('inventory', __name__)

# Route to display the inventory page
@inventory_bp.route('/inventory', methods=['GET'])
def inventory_page():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT i.inventory_id, p.name AS product_name, m.name AS manufacturer_name, 
                   i.price, i.quantity, i.expiry_date
            FROM inventory i
            JOIN products p ON i.product_id = p.id
            JOIN manufacturers m ON p.manufacturer_id = m.id
            WHERE i.quantity > 0
        ''')
        inventory = c.fetchall()
    return render_template('inventory.html', inventory=inventory)

# Route to display the "Import Inventory" page and handle form submission
@inventory_bp.route('/inventory/import', methods=['GET', 'POST'])
def import_inventory_page():
    if request.method == 'GET':
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT p.id, p.name, p.price, m.name AS manufacturer_name
                FROM products p
                JOIN manufacturers m ON p.manufacturer_id = m.id
                WHERE p.removed = 0
            ''')
            products = c.fetchall()

        product_details = {
            product[0]: {
                'manufacturer_name': product[3],
                'price': product[2]
            }
            for product in products
        }
        return render_template('import_inventory.html', products=products, product_details=product_details)

    # Handle form submission for importing inventory
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity'))
    expiry_date = request.form.get('expiry_date')

    if not product_id or not quantity or not expiry_date:
        return jsonify({'error': 'All fields are required.'}), 400

    with get_db_connection() as conn:
        c = conn.cursor()

        # Get the product name for logging
        c.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product_name = c.fetchone()[0]

        # Check if the same product with the same expiry date exists
        c.execute('''
            SELECT inventory_id, quantity
            FROM inventory
            WHERE product_id = ? AND expiry_date = ?
        ''', (product_id, expiry_date))
        existing_inventory = c.fetchone()

        if existing_inventory:
            # Update the quantity for the existing entry
            inventory_id, current_quantity = existing_inventory
            new_quantity = current_quantity + quantity
            c.execute('''
                UPDATE inventory
                SET quantity = ?
                WHERE inventory_id = ?
            ''', (new_quantity, inventory_id))
            log_activity(f"imported additional {quantity} {product_name} (ID: {product_id}) with expiry date {expiry_date} (New total: {new_quantity})")
        else:
            # Insert a new entry if no matching product and expiry date exist
            c.execute('''
                INSERT INTO inventory (product_id, manufacturer_id, price, quantity, expiry_date)
                VALUES (
                    ?, 
                    (SELECT manufacturer_id FROM products WHERE id = ?), 
                    (SELECT price FROM products WHERE id = ?), 
                    ?, ?
                )
            ''', (product_id, product_id, product_id, quantity, expiry_date))
            log_activity(f"imported {quantity} {product_name} (ID: {product_id}) with expiry date {expiry_date}")

        conn.commit()

    return redirect(url_for('inventory.inventory_page'))

# Route to display the "Export Inventory" page and handle form submission
@inventory_bp.route('/inventory/export', methods=['GET', 'POST'])
def export_inventory_page():
    if request.method == 'GET':
        with get_db_connection() as conn:
            c = conn.cursor()
            # Get unique product names with quantity > 0
            c.execute('''
                SELECT DISTINCT p.id, p.name
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                WHERE i.quantity > 0
            ''')
            products = c.fetchall()

            # Prepare inventory details for dropdown updates
            c.execute('''
                SELECT p.id, p.name, i.expiry_date, m.name AS manufacturer_name, 
                       i.price, i.quantity
                FROM inventory i
                JOIN products p ON i.product_id = p.id
                JOIN manufacturers m ON p.manufacturer_id = m.id
                WHERE i.quantity > 0
            ''')
            inventory_data = c.fetchall()

        inventory_details = {}
        for row in inventory_data:
            product_id = row[0]
            expiry_date = row[2]
            if product_id not in inventory_details:
                inventory_details[product_id] = {
                    'manufacturer_name': row[3],
                    'price': row[4],
                    'expiry_dates': [],
                    'quantities': {}
                }
            inventory_details[product_id]['expiry_dates'].append(expiry_date)
            inventory_details[product_id]['quantities'][expiry_date] = row[5]

        return render_template('export_inventory.html', products=products, inventory_details=inventory_details)

    # Handle form submission for exporting inventory
    product_id = request.form.get('product_id')
    expiry_date = request.form.get('expiry_date')
    quantity = int(request.form.get('quantity'))

    if not product_id or not expiry_date or not quantity:
        return jsonify({'error': 'All fields are required.'}), 400

    with get_db_connection() as conn:
        c = conn.cursor()

        # Retrieve product name for logging
        c.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product_name = c.fetchone()[0]

        c.execute('''
            SELECT inventory_id, quantity
            FROM inventory
            WHERE product_id = ? AND expiry_date = ?
        ''', (product_id, expiry_date))
        inventory_item = c.fetchone()

        if inventory_item and inventory_item[1] >= quantity:
            # Update inventory quantity
            c.execute('''
                UPDATE inventory
                SET quantity = quantity - ?
                WHERE inventory_id = ?
            ''', (quantity, inventory_item[0]))
            conn.commit()
            log_activity(f"exported {quantity} {product_name} (ID: {product_id}) with expiry date {expiry_date}")
            return redirect(url_for('inventory.inventory_page'))
        else:
            return jsonify({'error': 'Insufficient quantity or invalid selection.'}), 400
