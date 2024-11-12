from flask import Blueprint, render_template

activity_log_bp = Blueprint('activity_log', __name__)

@activity_log_bp.route('/activity_log')
def activity_log_page():
    log_entries = []
    try:
        with open('activity_log.txt', 'r') as f:
            log_entries = f.readlines()
    except FileNotFoundError:
        log_entries = ["No log file found."]
    
    return render_template('activity_log.html', log_entries=log_entries)