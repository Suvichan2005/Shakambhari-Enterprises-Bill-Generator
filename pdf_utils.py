import os
from flask import render_template_string
from weasyprint import HTML
from num2words import num2words
from config import TAX_RATES

def generate_pdf_invoice(data, output_path):
    """
    Generates a PDF invoice from data using an HTML template.

    Args:
        data (dict): A dictionary containing the invoice data.
        output_path (str): The path to save the generated PDF file.
    """
    # --- Calculations (similar to excel_utils) ---
    quantity = data.get("item_details", {}).get("quantity", 0)
    rate = data.get("item_details", {}).get("rate", 0)
    tax_type = data.get("tax_type", "IGST")

    item_amount = quantity * rate
    subtotal = item_amount
    igst_amount = 0
    cgst_amount = 0
    sgst_amount = 0

    igst_rate_val = TAX_RATES['IGST']
    cgst_rate_val = TAX_RATES['CGST']
    sgst_rate_val = TAX_RATES['SGST']

    if tax_type == "IGST":
        igst_amount = subtotal * igst_rate_val
    elif tax_type == "CGST_SGST":
        cgst_amount = subtotal * cgst_rate_val
        sgst_amount = subtotal * sgst_rate_val

    total_before_round_off = subtotal + igst_amount + cgst_amount + sgst_amount
    rounded_total = round(total_before_round_off)
    round_off_value = rounded_total - total_before_round_off

    amount_in_words_str = "Zero"
    if rounded_total > 0:
        amount_in_words_str = num2words(int(rounded_total), lang='en_IN').replace('-', ' ').replace(',', '').title()
    amount_in_words = amount_in_words_str + " Only"

    # --- Prepare context for template ---
    # The template has slightly different variable names, so we adapt.
    template_context = {
        "invoice_number_display": data.get("invoice_number", ""),
        "invoice_date_display": data.get("invoice_date", ""),
        "buyer_name": data.get("buyer_details", [])[0] if data.get("buyer_details") else "",
        "buyer_details_list": data.get("buyer_details", [])[1:] if data.get("buyer_details") and len(data.get("buyer_details")) > 1 else data.get("buyer_details", []),
        "buyer_gstin": next((line.split(":")[-1].strip() for line in data.get("buyer_details", []) if "GSTIN" in line.upper()), ""),
        "buyer_state_code": "", # This was not in the original data, can be added later.
        "mode_of_transport": data.get("mode_of_transport", ""),
        "item_description": data.get("item_details", {}).get("description", ""),
        "quantity": quantity,
        "rate": rate,
        "item_amount": item_amount,
        "subtotal": subtotal,
        "tax_type": tax_type,
        "igst_amount": igst_amount,
        "cgst_amount": cgst_amount,
        "sgst_amount": sgst_amount,
        "round_off_value": round_off_value,
        "rounded_total": rounded_total,
        "amount_in_words": amount_in_words
    }

    # --- Load Template and Render ---
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'invoice_pdf_template.html')
    try:
        with open(template_path, 'r') as f:
            template_html = f.read()
    except FileNotFoundError:
        raise Exception(f"PDF template not found at {template_path}")

    # We need a Flask app context to use render_template_string
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        rendered_html = render_template_string(template_html, **template_context)

    # --- Generate PDF ---
    HTML(string=rendered_html).write_pdf(output_path)
    print(f"Successfully generated PDF invoice: {output_path}")
