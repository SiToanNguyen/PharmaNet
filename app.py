from flask import Flask, request, redirect, url_for, render_template, session, send_from_directory
from utils import init_db, get_db_connection

from user_routes import user_bp
from manufacturer_routes import manufacturer_bp
from product_routes import product_bp
from inventory_routes import inventory_bp
from purchase_transaction_routes import purchase_transaction_bp
from activity_log_routes import activity_log_bp
from login_routes import login_bp

app = Flask(__name__)

app.secret_key = 'your_generated_secret_key' 
# Replace 'your_generated_secret_key' with the real key

# Use Flask Blueprint to organize the application into modular components.
# They allow to split the application into smaller parts, making the code easier to manage, maintain, and scale.
app.register_blueprint(user_bp)
app.register_blueprint(manufacturer_bp)
app.register_blueprint(product_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(purchase_transaction_bp)
app.register_blueprint(activity_log_bp)
app.register_blueprint(login_bp)

# Redirect users to the login page if they are not logged in when trying to access any page
@app.before_request
def check_login():
    # When requesting the CSS without logging in, it also redirects to the login page, thus does not load the CSS.
    if request.endpoint == 'static':
        return  # Bypass login check for static files and the login page, allow static file requests to proceed
    if 'username' not in session and request.endpoint not in ['login.login']:
        return redirect(url_for('login.login'))

# Context processor to make username available to all pages
@app.context_processor
def inject_user():
    return dict(username=session.get('username'))

@app.route('/')
def index():
    username = session.get('username')
    return render_template('index.html', username=username)

# For the CSS in "static" to reach the image in "images"
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('images', filename)

# Only for testing the price_history feature
@app.route('/price_history')
def view_price_history():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM price_history ORDER BY change_date DESC')
        price_history = c.fetchall()
    return render_template('price_history.html', price_history=price_history)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
