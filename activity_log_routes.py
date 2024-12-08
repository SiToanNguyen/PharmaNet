from flask import Blueprint, render_template, request

activity_log_bp = Blueprint('activity_log', __name__)

@activity_log_bp.route('/activity_log')
def activity_log_page():
    search_term = request.args.get('search', '').strip()  # Capture the search term from the query parameters

    log_entries = []
    try:
        with open('activity_log.txt', 'r') as f:
            log_entries = f.readlines()
    except FileNotFoundError:
        log_entries = ["No log file found."]

    # Filter log entries based on the search term
    if search_term:
        log_entries = [entry for entry in log_entries if search_term.lower() in entry.lower()]        
    
    return render_template('activity_log.html', log_entries=log_entries)