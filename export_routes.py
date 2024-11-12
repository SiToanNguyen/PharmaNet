from flask import Blueprint, render_template, request, redirect, url_for
from utils import get_db_connection, log_activity

export_bp = Blueprint('export', __name__)

@export_bp.route('/export', methods=['GET', 'POST'])
def export_page():
    conn = get_db_connection()
    c = conn.cursor()
    error_message = None
    
    if request.method == 'POST':
        product_id = request.form['product']
        quantity = int(request.form['quantity'])
        
        # Check if there is enough quantity in the warehouse
        c.execute('SELECT quantity FROM warehouse WHERE id = ?', (product_id,))
        current_quantity = c.fetchone()
        
        if current_quantity and current_quantity['quantity'] >= quantity:
            new_quantity = current_quantity['quantity'] - quantity
            c.execute('UPDATE warehouse SET quantity = ? WHERE id = ?', (new_quantity, product_id))
            
            # Log the export activity
            c.execute('SELECT name FROM products WHERE id = ?', (product_id,))
            product_name = c.fetchone()['name']
            log_activity(f'export {quantity} {product_name}')
                        
            conn.commit()
            conn.close()
            return redirect(url_for('export.export_page'))
        else:
            error_message = "Not enough quantity in warehouse."
    
    # Fetch all products from the warehouse
    c.execute('''
        SELECT p.id, p.name
        FROM warehouse w
        JOIN products p ON w.id = p.id
    ''')
    products = c.fetchall()
    
    # Fetch warehouse inventory for display
    c.execute('''
        SELECT p.name, w.quantity
        FROM warehouse w
        JOIN products p ON w.id = p.id
    ''')
    warehouse_items = c.fetchall()
    
    conn.close()
    
    return render_template('export.html', products=products, warehouse_items=warehouse_items, error_message=error_message if 'error_message' in locals() else None)
