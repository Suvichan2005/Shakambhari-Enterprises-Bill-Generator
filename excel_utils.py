import openpyxl
from num2words import num2words
from config import TAX_RATES

def generate_excel_invoice(template_path, output_path, data):
    """
    Generates an Excel invoice by filling in a template with provided data.

    Args:
        template_path (str): The path to the Excel template file.
        output_path (str): The path to save the generated Excel file.
        data (dict): A dictionary containing the invoice data.
    """
    try:
        workbook = openpyxl.load_workbook(template_path)
        sheet = workbook.active
    except FileNotFoundError:
        raise Exception(f"Excel template not found at {template_path}")

    # --- Calculations ---
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

    # --- Cell Mapping and Writing ---
    # Based on analysis of extract_invoice_data.py and educated guesses.
    # This mapping may need adjustment if the actual template is different.

    # Top-level info
    sheet['E4'] = data.get("invoice_number", "")
    sheet['E5'] = data.get("invoice_date", "")

    # Buyer details
    buyer_details_list = data.get("buyer_details", [])
    for i, detail_line in enumerate(buyer_details_list):
        cell_ref = f'A{8 + i}'
        if i < 8: # Limit to A8-A15
            sheet[cell_ref] = detail_line

    # Transport
    sheet['E10'] = data.get("mode_of_transport", "")

    # Item details (assuming positions)
    sheet['C18'] = data.get("item_details", {}).get("description", "")
    sheet['G18'] = quantity
    sheet['H18'] = rate
    sheet['I18'] = item_amount

    # Subtotal
    sheet['I28'] = subtotal

    # Taxes
    if tax_type == "IGST":
        sheet['C30'] = "I.G.S.T"
        sheet['E30'] = f"{igst_rate_val:.0%}"
        sheet['I30'] = igst_amount
        sheet['C31'] = "" # Clear other tax lines
        sheet['E31'] = ""
        sheet['I31'] = ""
        sheet['C32'] = ""
        sheet['E32'] = ""
        sheet['I32'] = ""
    elif tax_type == "CGST_SGST":
        sheet['C30'] = "" # Clear other tax lines
        sheet['E30'] = ""
        sheet['I30'] = ""
        sheet['C31'] = "C.G.S.T"
        sheet['E31'] = f"{cgst_rate_val:.0%}"
        sheet['I31'] = cgst_amount
        sheet['C32'] = "S.G.S.T"
        sheet['E32'] = f"{sgst_rate_val:.0%}"
        sheet['I32'] = sgst_amount

    # Totals
    sheet['I33'] = round_off_value
    sheet['I34'] = rounded_total
    sheet['C34'] = f"Amount in Words: {amount_in_words}"

    workbook.save(output_path)
    print(f"Successfully generated Excel invoice: {output_path}")
