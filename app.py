from flask import Flask, request, redirect, url_for, render_template, session
from utils import init_db

from user_routes import user_bp
from product_routes import product_bp
from import_routes import import_bp
from export_routes import export_bp
from activity_log_routes import activity_log_bp
from login_routes import login_bp

app = Flask(__name__)

app.secret_key = 'your_generated_secret_key' 
# Replace 'your_generated_secret_key' with the real key

# Use Flask Blueprint to organize the application into modular components.
# They allow to split the application into smaller parts, making the code easier to manage, maintain, and scale.
app.register_blueprint(user_bp)
app.register_blueprint(product_bp)
app.register_blueprint(import_bp)
app.register_blueprint(export_bp)
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
