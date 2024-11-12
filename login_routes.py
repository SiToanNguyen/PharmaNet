from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
from utils import get_db_connection, log_activity

login_bp = Blueprint('login', __name__)

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials in the database
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username  # Store username in the session

            # Log successful login
            log_activity(f'{username} logged in.')

            return redirect(url_for('index'))
        else:
            error_message = "Wrong Username or Password!"

    return render_template('login.html', error_message=error_message)

@login_bp.route('/logout')
def logout():
    username = session.pop('username', None)  # Remove username from session

    # Log successful logout
    if username:
        log_activity(f'{username} logged out.')

    return redirect(url_for('login.login'))
