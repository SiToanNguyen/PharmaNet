from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from utils import get_db_connection, log_activity

user_bp = Blueprint('user', __name__)

# Only "Admin" is allowed to access the User management feature
# Helper function to check if the user is "admin"
def is_admin():
    return session.get('username') == 'admin'

# Protect user-related routes
@user_bp.route('/user', methods=['GET', 'POST'])
def user_page():
    # Check if user is admin, else redirect to index page
    if not is_admin():
        return redirect(url_for('index'))

    error_message = None
    if request.method == 'POST':
        if 'username' in request.form:
            error_message = handle_add_user(request.form)  # Call the helper function
        elif 'remove_user' in request.form:
            user_id = request.form.get('user_id')
            if user_id:
                error_message = remove_user(int(user_id))

    users = get_all_users()
    return render_template('user.html', users=users, error_message=error_message)

# Route to display the "Add New User" page and handle form submission
@user_bp.route('/user/add', methods=['GET', 'POST'])
def add_user_page():
    # Check if user is admin, else redirect to index page
    if not is_admin():
        return redirect(url_for('index'))

    if request.method == 'POST':
        error_message = handle_add_user(request.form)  # Call the helper function

        # If there’s an error (like a duplicate username), render the add_user.html page with the error
        if error_message:
            return render_template('add_user.html', error_message=error_message)

        # Redirect to the user page only if no error occurs
        return redirect(url_for('user.user_page'))

    # Render the page normally for GET requests
    return render_template('add_user.html')

# Helper function to handle adding a user
def handle_add_user(form_data):
    # Check if user is admin, else redirect to index page
    if not is_admin():
        return redirect(url_for('index'))

    username = form_data.get('username')
    password = form_data.get('password')

    # Check if the username already exists in the database
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE LOWER(username) = LOWER(?)', (username.lower(),))
        existing_user = c.fetchone()

        if existing_user:
            return "A user with this username already exists. Please choose a different username."

    # Insert user into the database if no duplicate username is found
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            user_id = c.lastrowid  # Get the newly added user's ID

        # Write log when adding a new user
        log_activity(f"added {username} (ID: {user_id})")
        return None  # Return None if there is no error
    except Exception as e:
        print("Database error:", e)
        return f"Error: {str(e)}"  # Return error message if something goes wrong

# Route to display the "Edit User" page and handle form submission
@user_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    # Check if user is admin, else redirect to index page
    if not is_admin():
        return redirect(url_for('index'))

    error_message = None  # Initialize an error message variable

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Prevent changing the username of 'admin'
        if username == 'admin' and user_id != 1:  # Assuming user ID 1 is admin
            error_message = "The 'admin' username cannot be changed."
            return render_template('edit_user.html', user=get_user_by_id(user_id), error_message=error_message)

        # Check if the new username already exists
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id))
            existing_user = c.fetchone()

            if existing_user:
                # If a user with the same username exists and it's not the same user, show an error message
                error_message = "A user with this username already exists. Please choose a different username."
                return render_template('edit_user.html', user=get_user_by_id(user_id), error_message=error_message)

            # If no duplicate username, proceed to update the user
            c.execute('UPDATE users SET username = ?, password = ? WHERE id = ?',
                      (username, password, user_id))
            conn.commit()

        # Write log when editing a user
        log_activity(f"edited {username} (ID: {user_id})")

        return redirect(url_for('user.user_page'))

    # If GET request, fetch user details to populate the edit form
    user = get_user_by_id(user_id)
    return render_template('edit_user.html', user=user, error_message=error_message)

@user_bp.route('/user/remove/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    # Check if user is admin, else redirect to index page
    if not is_admin():
        return redirect(url_for('index'))

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = c.fetchone()
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()

    # Log the removal
    if username:
        log_activity(f"removed {username[0]} (ID: {user_id})")
    return jsonify({"status": "success"}), 200

def get_all_users():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, password FROM users')
        users = c.fetchall()
        return [dict(id=row[0], username=row[1], password=row[2]) for row in users]

def get_user_by_id(user_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, username, password FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        return dict(id=row[0], username=row[1], password=row[2]) if row else None
