from reportlab.pdfgen import canvas

# Create a new PDF with the specified filename
pdf_file = "hello_world.pdf"
c = canvas.Canvas(pdf_file)

# Draw the "Hello World" text at coordinates (100, 750)
c.drawString(100, 750, "Hello World")

# Save the PDF file
c.save()

print(f"PDF '{pdf_file}' created successfully!")
