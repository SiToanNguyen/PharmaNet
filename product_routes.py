from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils import get_db_connection, log_activity
import sqlite3

product_bp = Blueprint('product', __name__)

@product_bp.route('/product', methods=['GET', 'POST'])
def product_page():
    error_message = None

    # Get search parameters from the request
    product_name = request.args.get('product_name', '').strip()
    manufacturer_name = request.args.get('manufacturer_name', '').strip()

    # Base query
    query = '''
        SELECT 
            p.id AS product_id, 
            p.name AS product_name, 
            m.name AS manufacturer_name, 
            p.purchase_price AS product_purchase_price,
            p.price AS product_price,
            m.id AS manufacturer_id
        FROM products p
        JOIN manufacturers m ON p.manufacturer_id = m.id
        WHERE 1=1
    '''
    params = []

    # Add filters dynamically based on user input
    if product_name:
        query += " AND p.name LIKE ?"
        params.append(f"%{product_name}%")
    if manufacturer_name:
        query += " AND m.name LIKE ?"
        params.append(f"%{manufacturer_name}%")

    # Execute the query
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            products = cursor.fetchall()

            # Format products to have a 'manufacturer' key as a dictionary
            products = [
                {
                    'id': row['product_id'],
                    'name': row['product_name'],
                    'purchase_price': row['product_purchase_price'],
                    'price': row['product_price'],
                    'manufacturer': {'id': row['manufacturer_id'], 'name': row['manufacturer_name']}
                }
                for row in products
            ]
    except sqlite3.OperationalError as e:
        return f"SQL error: {e}", 500
    
    if request.method == 'POST':
        if 'product_name' in request.form:
            error_message = handle_add_product(request.form)  # Call the helper function
        elif 'remove_product' in request.form:
            product_id = request.form.get('product_id')
            if product_id:
                error_message = remove_product(int(product_id))
    
    return render_template('product.html', products=products, error_message=error_message)

# Get all manufacturers, who are not removed
def get_all_manufacturers():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name FROM manufacturers WHERE removed = 0')
        return c.fetchall()

# Route to display the "Add New Product" page and handle form submission
@product_bp.route('/product/add', methods=['GET', 'POST'])
def add_product_page():
    if request.method == 'POST':
        error_message = handle_add_product(request.form)  # Call the helper function
        
        # If there’s an error (like a duplicate name), render the add_product.html page with the error
        if error_message:
            manufacturers = get_all_manufacturers()  # Pass manufacturers even if there's an error
            return render_template('add_product.html', error_message=error_message)

        # Redirect to the product page only if no error occurs
        return redirect(url_for('product.product_page'))
    
    manufacturers = get_all_manufacturers()

    # Render the page normally for GET requests
    return render_template('add_product.html', manufacturers=manufacturers)

# Helper function to handle adding a product
def handle_add_product(form_data):
    product_name = form_data.get('product_name')
    manufacturer_id = form_data.get('manufacturer_id') 
    purchase_price = form_data.get('purchase_price')
    price = form_data.get('price')
    description = form_data.get('description', '')  # Handle empty description field

    if not product_name or not manufacturer_id or not purchase_price or not price:
        return "Product name, manufacturer, purchase price, and price cannot be empty."

    # Check if the product name already exists in the database
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, removed FROM products WHERE LOWER(name) = LOWER(?)', (product_name.lower(),))
        existing_product = c.fetchone()

        if existing_product:
            product_id, removed_status = existing_product
            if removed_status:  # If the product is marked as removed
                # Reactivate the product
                c.execute(''' 
                    UPDATE products 
                    SET manufacturer_id = ?, purchase_price = ?, price = ?, description = ?, removed = 0
                    WHERE id = ? 
                ''', (manufacturer_id, purchase_price, price, description, product_id))
                
                # Log price history for reactivated product
                c.execute(
                    'INSERT INTO price_history (product_id, old_price, new_price) VALUES (?, NULL, ?)',
                    (product_id, price)
                )
                
                conn.commit()

                # Write log when reactivating a product
                log_activity(f"reactivated the product {product_name} (ID: {product_id})")
                return None  # No error
            else:
                print(f"Existing product check for {product_name}: Found duplicate")
                # If a product with the same name already exists, return an error message
                return "A product with this name already exists. Please choose a different name."
        else:
            print(f"Existing product check for {product_name}: No duplicate found")

    # Insert product into the database if no duplicate name is found
    try:
        c.execute('INSERT INTO products (name, manufacturer_id, purchase_price, price, description) VALUES (?, ?, ?, ?)',
                  (product_name, manufacturer_id, purchase_price, price, description))
        
        product_id = c.lastrowid  # Get the newly added product's ID
        
        # Log initial price in price history
        c.execute(
            'INSERT INTO price_history (product_id, old_price, new_price) VALUES (?, NULL, ?)',
            (product_id, price)
        )
        
        conn.commit()

        # Log adding a new product
        log_activity(f"added the product {product_name} (ID: {product_id})")
        return None  # Return None if there is no error
    except Exception as e:
        print("Database error:", e)
        return f"Error: {str(e)}"  # Return error message if something goes wrong

# Route to display the "Edit Product" page and handle form submission
@product_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    error_message = None  # Initialize an error message variable
        
    # Get the list of manufacturers to pass to the dropdown list
    manufacturers = get_all_manufacturers()

    if request.method == 'POST':
        product_name = request.form.get('product_name')
        manufacturer_id = request.form.get('manufacturer_id')
        purchase_price = request.form.get('purchase_price')
        price = request.form.get('price')
        description = request.form.get('description')

        if not product_name or not manufacturer_id or not purchase_price or not price:
            error_message = "Product name, manufacturer, and price cannot be empty."
            return render_template('edit_product.html', product=get_product_by_id(product_id), error_message=error_message)

        # Check if the new product name already exists
        with get_db_connection() as conn:
            c = conn.cursor()

            # Get the current price for comparison
            c.execute('SELECT price FROM products WHERE id = ?', (product_id,))
            current_price = c.fetchone()[0]

            c.execute('SELECT id FROM products WHERE name = ? AND id != ?', (product_name, product_id))
            existing_product = c.fetchone()

            if existing_product:
                # If a product with the same name exists and it's not the same product, show an error message
                error_message = "A product with this name already exists. Please choose a different name."
                return render_template('edit_product.html', product=get_product_by_id(product_id), error_message=error_message)
            
            # If no duplicate name, proceed to update the product
            c.execute('UPDATE products SET name = ?, manufacturer_id = ?, price = ?, purchase_price = ?, description = ? WHERE id = ?',
                      (product_name, manufacturer_id, price, purchase_price, description, product_id))          
                        
            # Log price change if it differs
            if price != current_price:
                c.execute(
                    'INSERT INTO price_history (product_id, old_price, new_price) VALUES (?, ?, ?)',
                    (product_id, current_price, price)
                )

            conn.commit()

        # Log editing a product
        log_activity(f"edited the product {product_name} (ID: {product_id})")
        
        return redirect(url_for('product.product_page'))

    # If GET request, fetch product details to populate the edit form
    product = get_product_by_id(product_id)
    return render_template('edit_product.html', product=product, manufacturers=manufacturers, error_message=error_message)

@product_bp.route('/product/remove/<int:product_id>', methods=['POST'])
def remove_product(product_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product_name = c.fetchone()
        c.execute('UPDATE products SET removed = 1 WHERE id = ?', (product_id,))
        conn.commit()

    # Log removing a product
    if product_name:
        log_activity(f"removed the product {product_name[0]} (ID: {product_id})")
    return jsonify({"status": "success"}), 200

def get_all_products():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(''' 
            SELECT p.id, p.name, p.manufacturer_id, p.purchase_price, p.price, m.name AS manufacturer_name, m.id AS manufacturer_id
            FROM products p
            JOIN manufacturers m ON p.manufacturer_id = m.id
            WHERE p.removed = 0
        ''')
        products = c.fetchall()
        return [dict(id=row[0], name=row[1], manufacturer={'id': row[6], 'name': row[5]}, purchase_price=row[3], price=row[4]) for row in products]

def get_product_by_id(product_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, manufacturer_id, purchase_price, price, description FROM products WHERE id = ?', (product_id,))
        row = c.fetchone()
        return dict(id=row[0], name=row[1], manufacturer_id=row[2], purchase_price=row[3], price=row[4], description=row[5]) if row else None
