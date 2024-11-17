from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils import get_db_connection, log_activity

product_bp = Blueprint('product', __name__)

@product_bp.route('/product', methods=['GET', 'POST'])
def product_page():
    error_message = None
    
    if request.method == 'POST':
        if 'product_name' in request.form:
            error_message = handle_add_product(request.form)  # Call the helper function
        elif 'remove_product' in request.form:
            product_id = request.form.get('product_id')
            if product_id:
                error_message = remove_product(int(product_id))
    
    products = get_all_products()
    return render_template('product.html', products=products, error_message=error_message)

# Route to display the "Add New Product" page and handle form submission
@product_bp.route('/product/add', methods=['GET', 'POST'])
def add_product_page():
    if request.method == 'POST':
        error_message = handle_add_product(request.form)  # Call the helper function
        
        # If there’s an error (like a duplicate name), render the add_product.html page with the error
        if error_message:
            return render_template('add_product.html', error_message=error_message)

        # Redirect to the product page only if no error occurs
        return redirect(url_for('product.product_page'))
    
    # Render the page normally for GET requests
    return render_template('add_product.html')

# Helper function to handle adding a product
def handle_add_product(form_data):
    product_name = form_data.get('product_name')
    manufacturer = form_data.get('manufacturer')
    price = form_data.get('price')
    description = form_data.get('description', '')  # Handle empty description field

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
                    SET manufacturer = ?, price = ?, description = ?, removed = 0
                    WHERE id = ?
                ''', (manufacturer, price, description, product_id))
                conn.commit()

                # Write log when reactivating a product
                log_activity(f"reactivated {product_name} (ID: {product_id})")
                return None  # No error
            else:
                print(f"Existing product check for {product_name}: Found duplicate")
                # If a product with the same name already exists, return an error message
                return "A product with this name already exists. Please choose a different name."
        else:
            print(f"Existing product check for {product_name}: No duplicate found")

    # Insert product into the database if no duplicate name is found
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT INTO products (name, manufacturer, price, description) VALUES (?, ?, ?, ?)',
                      (product_name, manufacturer, price, description))
            conn.commit()
            product_id = c.lastrowid  # Get the newly added product's ID

        # Write log when adding a new product
        log_activity(f"added {product_name} (ID: {product_id})")
        return None  # Return None if there is no error
    except Exception as e:
        print("Database error:", e)
        return f"Error: {str(e)}"  # Return error message if something goes wrong

# Route to display the "Edit Product" page and handle form submission
@product_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    error_message = None  # Initialize an error message variable
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        manufacturer = request.form.get('manufacturer')
        price = request.form.get('price')
        description = request.form.get('description')

        # Check if the new product name already exists
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM products WHERE name = ? AND id != ?', (product_name, product_id))
            existing_product = c.fetchone()

            if existing_product:
                # If a product with the same name exists and it's not the same product, show an error message
                error_message = "A product with this name already exists. Please choose a different name."
                return render_template('edit_product.html', product=get_product_by_id(product_id), error_message=error_message)
            
            # If no duplicate name, proceed to update the product
            c.execute('UPDATE products SET name = ?, manufacturer = ?, price = ?, description = ? WHERE id = ?',
                      (product_name, manufacturer, price, description, product_id))
            conn.commit()

        # Write log when editing a product
        log_activity(f"edited {product_name} (ID: {product_id})")
        
        return redirect(url_for('product.product_page'))

    # If GET request, fetch product details to populate the edit form
    product = get_product_by_id(product_id)
    return render_template('edit_product.html', product=product, error_message=error_message)

@product_bp.route('/product/remove/<int:product_id>', methods=['POST'])
def remove_product(product_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product_name = c.fetchone()
        c.execute('UPDATE products SET removed = 1 WHERE id = ?', (product_id,))
        conn.commit()

    # Log the removal
    if product_name:
        log_activity(f"removed {product_name[0]} (ID: {product_id})")
    return jsonify({"status": "success"}), 200

def get_all_products():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, manufacturer, price FROM products WHERE removed = 0')
        products = c.fetchall()
        return [dict(id=row[0], name=row[1], manufacturer=row[2], price=row[3]) for row in products]

def get_product_by_id(product_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, manufacturer, price, description FROM products WHERE id = ?', (product_id,))
        row = c.fetchone()
        return dict(id=row[0], name=row[1], manufacturer=row[2], price=row[3], description=row[4]) if row else None
