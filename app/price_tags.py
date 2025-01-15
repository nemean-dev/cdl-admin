import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

def generate_pdf(data:pd.DataFrame, pdf_filename:str):
    """Generate a PDF from given data."""
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    x_start, y_start = 40, 710

    data.columns = data.columns.str.lower()
    current_rectangle = 0
    cols, rows = 8, 23
    width, height = 64, 30
    padding = 0
    max_per_page = cols * rows

    for _, row in data.iterrows():
        sku, price, qty = row['sku'], row['precio'], row['cantidad']
        for _ in range(qty):
            x = x_start + (current_rectangle % cols) * (width + padding)
            y = y_start - (current_rectangle // cols) * (height + padding)

            c.setStrokeColorRGB(0.05, 0.05, 0.05)
            c.setLineWidth(0.1)
            c.rect(x, y, width, height)

            price_font, price_font_size = "Helvetica-Bold", 11
            sku_font, sku_font_size = "Helvetica", 10

            c.setFont(price_font, price_font_size)
            price_text = f"${int(price):,}" if price == int(price) else f"${price:,.2f}"
            price_text_width = stringWidth(price_text, price_font, price_font_size)
            c.drawString(x + (width - price_text_width) / 2, y + height // 2 + 1, price_text)

            c.setFont(sku_font, sku_font_size)
            sku_text = f"{sku}"
            sku_text_width = stringWidth(sku_text, sku_font, sku_font_size)
            c.drawString(x + (width - sku_text_width) / 2, y + height - 24, sku_text)

            current_rectangle += 1
            if current_rectangle == max_per_page:
                c.showPage()
                current_rectangle = 0

    c.save()
