from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from utils import get_db_connection, log_activity

manufacturer_bp = Blueprint('manufacturer', __name__)

@manufacturer_bp.route('/manufacturer', methods=['GET', 'POST'])
def manufacturer_page():
    error_message = None
    
    if request.method == 'POST':
        if 'manufacturer_name' in request.form:
            error_message = handle_add_manufacturer(request.form)  # Call the helper function
        elif 'remove_manufacturer' in request.form:
            manufacturer_id = request.form.get('manufacturer_id')
            if manufacturer_id:
                error_message = remove_manufacturer(int(manufacturer_id))
    
    manufacturers = get_all_manufacturers()
    return render_template('manufacturer.html', manufacturers=manufacturers, error_message=error_message)

# Route to display the "Add New Manufacturer" page and handle form submission
@manufacturer_bp.route('/manufacturer/add', methods=['GET', 'POST'])
def add_manufacturer_page():
    if request.method == 'POST':
        error_message = handle_add_manufacturer(request.form)  # Call the helper function
        
        # If there’s an error (like a duplicate name), render the add_manufacturer.html page with the error
        if error_message:
            return render_template('add_manufacturer.html', error_message=error_message)

        # Redirect to the manufacturer page only if no error occurs
        return redirect(url_for('manufacturer.manufacturer_page'))
    
    # Render the page normally for GET requests
    return render_template('add_manufacturer.html')

# Helper function to handle adding a manufacturer
def handle_add_manufacturer(form_data):
    manufacturer_name = form_data.get('manufacturer_name')
    description = form_data.get('description', '')  # Handle empty description field

    # Check if the manufacturer name is empty
    if not manufacturer_name.strip():
        return "Manufacturer name cannot be empty."

    # Check if the manufacturer name already exists in the database
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, removed FROM manufacturers WHERE LOWER(name) = LOWER(?)', (manufacturer_name.lower(),))
        existing_manufacturer = c.fetchone()

        if existing_manufacturer:
            manufacturer_id, removed_status = existing_manufacturer
            if removed_status:  # If the manufacturer is marked as removed
                # Reactivate the manufacturer
                c.execute(''' 
                    UPDATE manufacturers 
                    SET description = ?, removed = 0 
                    WHERE id = ?
                ''', (description, manufacturer_id))
                conn.commit()

                # Write log when reactivating a manufacturer
                log_activity(f"reactivated the manufacturer {manufacturer_name} (ID: {manufacturer_id})")
                return None  # No error
            else:
                print(f"Existing manufacturer check for {manufacturer_name}: Found duplicate")
                # If a manufacturer with the same name already exists, return an error message
                return "A manufacturer with this name already exists. Please choose a different name."
        else:
            print(f"Existing manufacturer check for {manufacturer_name}: No duplicate found")

    # Insert manufacturer into the database if no duplicate name is found
    try:
        c.execute('INSERT INTO manufacturers (name, description) VALUES (?, ?)', (manufacturer_name, description))
        conn.commit()
        manufacturer_id = c.lastrowid  # Get the newly added manufacturer's ID

        # Write log when adding a new manufacturer
        log_activity(f"added the manufacturer {manufacturer_name} (ID: {manufacturer_id})")
        return None  # Return None if there is no error
    except Exception as e:
        print("Database error:", e)
        return f"Error: {str(e)}"  # Return error message if something goes wrong

# Route to display the "Edit Manufacturer" page and handle form submission
@manufacturer_bp.route('/manufacturer/edit/<int:manufacturer_id>', methods=['GET', 'POST'])
def edit_manufacturer(manufacturer_id):
    error_message = None  # Initialize an error message variable
    
    if request.method == 'POST':
        manufacturer_name = request.form.get('manufacturer_name')
        description = request.form.get('description')

        # Check if the manufacturer name is empty
        if not manufacturer_name.strip():
            error_message = "Manufacturer name cannot be empty."
            return render_template('edit_manufacturer.html', manufacturer=get_manufacturer_by_id(manufacturer_id), error_message=error_message)
        
        # Check if the new manufacturer name already exists
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM manufacturers WHERE name = ? AND id != ?', (manufacturer_name, manufacturer_id))
            existing_manufacturer = c.fetchone()

            if existing_manufacturer:
                # If a manufacturer with the same name exists and it's not the same manufacturer, show an error message
                error_message = "A manufacturer with this name already exists. Please choose a different name."
                return render_template('edit_manufacturer.html', manufacturer=get_manufacturer_by_id(manufacturer_id), error_message=error_message)
            
            # If no duplicate name, proceed to update the manufacturer
            c.execute('UPDATE manufacturers SET name = ?, description = ? WHERE id = ?',
                      (manufacturer_name, description, manufacturer_id))
            conn.commit()

        # Write log when editing a manufacturer
        log_activity(f"edited the manufacturer {manufacturer_name} (ID: {manufacturer_id})")
        
        return redirect(url_for('manufacturer.manufacturer_page'))

    # If GET request, fetch manufacturer details to populate the edit form
    manufacturer = get_manufacturer_by_id(manufacturer_id)
    return render_template('edit_manufacturer.html', manufacturer=manufacturer, error_message=error_message)

@manufacturer_bp.route('/manufacturer/remove/<int:manufacturer_id>', methods=['POST'])
def remove_manufacturer(manufacturer_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT name FROM manufacturers WHERE id = ?', (manufacturer_id,))
        manufacturer_name = c.fetchone()
        c.execute('UPDATE manufacturers SET removed = 1 WHERE id = ?', (manufacturer_id,))
        conn.commit()

    # Log the removal
    if manufacturer_name:
        log_activity(f"removed the manufacturer {manufacturer_name[0]} (ID: {manufacturer_id})")
    return jsonify({"status": "success"}), 200

def get_all_manufacturers():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, description FROM manufacturers WHERE removed = 0')
        manufacturers = c.fetchall()
        return [dict(id=row[0], name=row[1], description=row[2]) for row in manufacturers]

def get_manufacturer_by_id(manufacturer_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, description FROM manufacturers WHERE id = ?', (manufacturer_id,))
        row = c.fetchone()
        return dict(id=row[0], name=row[1], description=row[2]) if row else None
