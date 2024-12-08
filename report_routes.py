from flask import Blueprint, render_template, request, send_file
from utils import get_db_connection, log_activity
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER  # Import for center alignment

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

        # Format the dates as strings in 'YYYY-MM-DD' format
        formatted_from_date = from_date.strftime('%Y-%m-%d')
        formatted_to_date = to_date.strftime('%Y-%m-%d')

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

        # Format the money values to 2 decimal places
        formatted_total_purchase_value = "{:.2f}".format(total_purchase_value)
        formatted_total_sale_value = "{:.2f}".format(total_sale_value)
        formatted_net_value = "{:.2f}".format(net_value)

        # Close the database connection
        connection.close()

        # Prepare the report data
        report_data = {
            "from_date": formatted_from_date,  # Pass formatted date as string
            "to_date": formatted_to_date,      # Pass formatted date as string
            "purchases": filtered_purchases,
            "sales": filtered_sales,
            "total_purchase_value": total_purchase_value,
            "total_sale_value": total_sale_value,
            "net_value": net_value,
        }

        return render_template('report.html', report_data=report_data)

    except Exception as e:
        return f"An error occurred: {e}", 400

@report_bp.route('/export_pdf', methods=['POST'])
def export_report_pdf():
    try:
        # Get the date range from the form
        from_date_str = request.form['from_date']
        to_date_str = request.form['to_date']

        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()

        # Connect to the database and fetch data (same as before)
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

        # Format the money values to 2 decimal places
        formatted_total_purchase_value = "{:.2f}".format(total_purchase_value)
        formatted_total_sale_value = "{:.2f}".format(total_sale_value)
        formatted_net_value = "{:.2f}".format(net_value)

        # Close the database connection
        connection.close()

        # Create a PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Get the default styles
        styles = getSampleStyleSheet()

        # Create a custom style for centered titles
        centered_title_style = styles['Heading1']
        centered_title_style.fontSize = 18  # Customize the font size if needed
        centered_title_style.fontName = 'Helvetica-Bold'
        centered_title_style.alignment = TA_CENTER  # Center align

        # Title: "PharmaNet" - Centered
        title = "PharmaNet"
        title_paragraph = Paragraph(title, style=centered_title_style)
        elements.append(title_paragraph)

        # Add a line break for spacing between title and content
        elements.append(Paragraph("<br />", styles['Normal']))

        # Subtitle: "Report from {from_date} to {to_date}" - Centered
        centered_subtitle_style = styles['Heading2']
        centered_subtitle_style.fontSize = 14
        centered_subtitle_style.alignment = TA_CENTER  # Center align

        subtitle = f"Report from {from_date} to {to_date}"
        subtitle_paragraph = Paragraph(subtitle, style=centered_subtitle_style)
        elements.append(subtitle_paragraph)

        # Set the total document width (for letter size, it's 612 points)
        page_width = letter[0]  # 612 points

        # Define column widths relative to the page width
        margin = 36  # Left and right margin (about 1 inch)
        available_width = page_width - 2 * margin  # Subtract left and right margins
        col_widths = [available_width * 0.2, available_width * 0.4, available_width * 0.4]  # 20% - 40% - 40%

        # Section 1: "Purchase Transactions"
        section_title = "Purchase Transactions"
        section_title_style = styles['Heading3']
        section_title_style.fontSize = 12
        section_title_style.fontName = 'Helvetica-Bold'
        elements.append(Paragraph(section_title, style=section_title_style))

        # Purchase Transactions Table
        purchase_data = [['ID', 'Transaction Date', 'Total Price (€)']]  # Table headers
        for purchase in filtered_purchases:
            purchase_data.append([str(purchase['id']), str(purchase['transaction_date']), f"{purchase['total_price']:.2f}"])

        purchase_table = Table(purchase_data, colWidths=col_widths)  # Set column widths to spread across page
        purchase_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),  # Add padding to left side
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),  # Add padding to right side
        ]))
        elements.append(purchase_table)

        # Section 2: "Sale Transactions"
        section_title = "Sale Transactions"
        elements.append(Paragraph(section_title, style=section_title_style))

        # Sale Transactions Table
        sale_data = [['ID', 'Transaction Date', 'Total Price (€)']]  # Table headers
        for sale in filtered_sales:
            sale_data.append([str(sale['id']), str(sale['transaction_date']), f"{sale['total_price']:.2f}"])

        sale_table = Table(sale_data, colWidths=col_widths)  # Set column widths to spread across page
        sale_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(sale_table)

        # Section 3: "Total" and Totals Data
        elements.append(Paragraph("Total", style=section_title_style))  # Add the "Total" heading

        # Totals Data
        totals_data = [
            ["Total Purchase Value", formatted_total_purchase_value],
            ["Total Sale Value", formatted_total_sale_value],
            ["Net Value", formatted_net_value]
        ]

        # Define column widths for the totals table
        totals_col_widths = [available_width * 0.6, available_width * 0.4]  # Adjust proportions as needed

        # Create the Totals Table
        totals_table = Table(totals_data, colWidths=totals_col_widths)  # Use the defined column widths
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 0), (-1, -1), colors.beige),  # Set default background
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),  # Ensure "Total Purchase Value" is normal
            ('BACKGROUND', (0, 2), (-1, 2), colors.lightblue),  # Highlight "Net Value" row
        ]))
        elements.append(totals_table)


        # Build the PDF
        doc.build(elements)

        # Move buffer position to the beginning
        buffer.seek(0)

        # Send the PDF to the user as a download
        return send_file(buffer, as_attachment=True, download_name="report.pdf", mimetype="application/pdf")

    except Exception as e:
        return f"An error occurred while generating the PDF: {e}", 400