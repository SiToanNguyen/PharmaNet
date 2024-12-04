from flask import Blueprint, render_template, request
from utils import get_db_connection, log_activity
from datetime import datetime

report_bp = Blueprint('report', __name__)

@report_bp.route('/report')
def report_page():
    return render_template('report.html')

@report_bp.route('/report', methods=['POST'])
def generate_report_page():
    try:
        # Get the date range from the form
        from_date_str = request.form['from_date']
        to_date_str = request.form['to_date']

        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

        # Connect to the database
        connection = get_db_connection()
        cursor = connection.cursor()

        # Fetch purchase transactions within the date range
        purchase_query = """
            SELECT purchase_transaction_id, transaction_date, total_price
            FROM purchase_transactions
            WHERE transaction_date BETWEEN ? AND ?
        """
        cursor.execute(purchase_query, (from_date, to_date))
        filtered_purchases = [
            {
                "id": row[0],
                "transaction_date": row[1],
                "total_price": row[2]
            }
            for row in cursor.fetchall()
        ]
        total_purchase_value = sum(t["total_price"] for t in filtered_purchases)

        # Fetch sale transactions within the date range
        sale_query = """
            SELECT sale_transaction_id, transaction_date, total_price
            FROM sale_transactions
            WHERE transaction_date BETWEEN ? AND ?
        """
        cursor.execute(sale_query, (from_date, to_date))
        filtered_sales = [
            {
                "id": row[0],
                "transaction_date": row[1],
                "total_price": row[2]
            }
            for row in cursor.fetchall()
        ]
        total_sale_value = sum(t["total_price"] for t in filtered_sales)

        # Calculate the final sum
        net_value = total_sale_value - total_purchase_value

        # Close the database connection
        connection.close()

        # Log the activity (if necessary)
        log_activity(f"generated report for {from_date} to {to_date}")

        # Prepare the report data
        report_data = {
            "purchases": filtered_purchases,
            "sales": filtered_sales,
            "total_purchase_value": total_purchase_value,
            "total_sale_value": total_sale_value,
            "net_value": net_value,
        }

        return render_template('report.html', report_data=report_data)

    except Exception as e:
        return f"An error occurred: {e}", 400
