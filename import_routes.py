from flask import Blueprint, render_template, request, redirect, url_for
from utils import get_db_connection, log_activity

import_bp = Blueprint('import', __name__)

@import_bp.route('/import', methods=['GET', 'POST'])
def import_page():
    conn = get_db_connection()
    c = conn.cursor()
    error_message = None
    
    if request.method == 'POST':
        id = request.form['product']
        quantity = int(request.form['quantity'])
        
        # Check if the product is already in the warehouse
        c.execute('SELECT quantity FROM warehouse WHERE id = ?', (id,))
        existing_product = c.fetchone()
        
        if existing_product:
            new_quantity = existing_product['quantity'] + quantity
            c.execute('UPDATE warehouse SET quantity = ? WHERE id = ?', (new_quantity, id))
        else:
            c.execute('INSERT INTO warehouse (id, quantity) VALUES (?, ?)', (id, quantity))
        
        # Log the activity
        c.execute('SELECT name FROM products WHERE id = ?', (id,))
        product_name = c.fetchone()['name']        
        log_activity(f'import {quantity} {product_name}')
        
        conn.commit()
        return redirect(url_for('import.import_page'))

    c.execute('SELECT id, name FROM products WHERE removed = 0')
    products = c.fetchall()
    
    c.execute('SELECT p.name, w.quantity FROM warehouse w JOIN products p ON w.id = p.id')
    warehouse_items = c.fetchall()
    
    conn.close()
    return render_template('import.html', products=products, warehouse_items=warehouse_items, error_message=error_message)
