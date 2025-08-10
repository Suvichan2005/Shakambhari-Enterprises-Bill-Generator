import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify # Added jsonify
from datetime import datetime
import uuid  # For generating unique IDs for new profiles without GSTIN
from num2words import num2words # For converting numbers to words
from typing import Any, List
from excel_utils import generate_excel_invoice
from pdf_utils import generate_pdf_invoice
from data_manager import load_data, save_data
from invoice_utils import get_next_invoice_number, update_last_invoice_number
from config import (BUYER_PROFILES_JSON, TRANSPORT_MODES_JSON, OUTPUT_DIR, PDF_OUTPUT_DIR, TEMPLATE_EXCEL_FILE, ensure_dirs, BASE_DIR, TAX_RATES)


app = Flask(__name__)
app.secret_key = 'shakambhari-secret'  # Needed for flash messages (simplified)
ensure_dirs()  # make sure output dirs exist


TRANSPORT_PREFIX_VARIANTS = [
    'mode of transport:', 'mode of transports:', 'mode of transport', 'mode of transports'
]

def normalize_transport_mode(raw: str | None) -> str:
    if not raw:
        return ''
    val = raw.strip()
    low = val.lower()
    for prefix in TRANSPORT_PREFIX_VARIANTS:
        if low.startswith(prefix):
            # remove the matched prefix length from original string to preserve original case after prefix
            val = val[len(prefix):].strip(' -:')
            break
    if not val:
        return ''
    return f"Mode of Transport: {val}"  # canonical form

@app.route('/')
def index():
    buyer_profiles = load_data(BUYER_PROFILES_JSON)
    transport_modes = load_data(TRANSPORT_MODES_JSON)
    today_date = datetime.now().strftime('%Y-%m-%d')  # html date input format
    valid_buyer_profiles = [p for p in buyer_profiles if p.get('profile_id') and p.get('buyer_name')]
    suggestion = get_next_invoice_number()
    return render_template('index.html', buyer_profiles=valid_buyer_profiles, transport_modes=transport_modes, today_date=today_date, suggested_invoice_number=suggestion)

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    try:
        # Core form fields
        buyer_profile_id = request.form['buyer_profile_id']
        raw_invoice_number_form = request.form['invoice_number']
        invoice_date_from_form_str = request.form['invoice_date']

        # Parse date
        try:
            dt_object = datetime.strptime(invoice_date_from_form_str, '%Y-%m-%d')
        except ValueError:
            flash("Invalid date format received. Please use YYYY-MM-DD.", "error")
            return redirect(url_for('index'))
    # Use DD/MM/YYYY format for display per new requirement
        formatted_invoice_date_for_excel = dt_object.strftime('%d/%m/%Y')

        # Invoice number display & date display for template
        invoice_number_for_filename = raw_invoice_number_form.strip()
        excel_invoice_number_display = f"INVOICE No. {invoice_number_for_filename}" if invoice_number_for_filename else ""
        excel_invoice_date_display = f"Date : {formatted_invoice_date_for_excel}" if formatted_invoice_date_for_excel else ""

        # Transport (UI provides raw without forced prefix)
        transport_mode_raw = request.form.get('transport_mode')
        transport_mode = normalize_transport_mode(transport_mode_raw)

        # Item
        item_description_bags = request.form.get('item_description_bags')
        excel_item_base_description = request.form.get('item_base_description') or '1. Aluminium Utensils'
        item_description = excel_item_base_description
        if item_description_bags:
            item_description += f" ({item_description_bags} Bags)"
        quantity = float(request.form.get('quantity', 0) or 0)
        rate = float(request.form.get('rate', 0) or 0)

        # Buyer profile lookup
        buyer_profiles = load_data(BUYER_PROFILES_JSON)
        selected_profile = next((p for p in buyer_profiles if p.get('profile_id') == buyer_profile_id), None)
        if not selected_profile:
            flash("Selected buyer profile not found.", "error")
            return redirect(url_for('index'))

        # Tax resolution
        tax_type_override = request.form.get('tax_type_override')
        if tax_type_override and tax_type_override != "PROFILE_DEFAULT":
            final_tax_type = tax_type_override
        else:
            final_tax_type = selected_profile.get('default_tax_type', 'IGST')

        config_data = {
            "buyer_details": selected_profile.get('buyer_details', []),
            "mode_of_transport": transport_mode,
            "item_details": {"description": item_description, "quantity": quantity, "rate": rate},
            "tax_type": final_tax_type,
            "invoice_number": excel_invoice_number_display,
            "invoice_date": excel_invoice_date_display
        }

        # Safe filenames
        safe_invoice_number_for_file = ''.join(c if c.isalnum() else '_' for c in invoice_number_for_filename)
        safe_buyer_name = ''.join(c if c.isalnum() else '_' for c in selected_profile.get('buyer_name', 'UnknownBuyer'))
        excel_filename_base = f"Invoice_{safe_invoice_number_for_file}_{safe_buyer_name}" if safe_invoice_number_for_file else f"Invoice_{safe_buyer_name}"
        excel_output_filename = f"{excel_filename_base}.xlsx"
        excel_destination_filepath = os.path.join(OUTPUT_DIR, excel_output_filename)

        if not TEMPLATE_EXCEL_FILE:
            flash("No Excel template found. Place a template .xlsx inside the 'GST Invoices' folder.", "error")
            return redirect(url_for('index'))

        # Generate Excel
        try:
            generate_excel_invoice(TEMPLATE_EXCEL_FILE, excel_destination_filepath, config_data)
        except Exception as e:
            flash(f"Error generating Excel file: {e}", "error")
            return redirect(url_for('index'))

        # PDF Generation
        pdf_output_filename = f"{excel_filename_base}.pdf"
        pdf_destination_filepath = os.path.join(PDF_OUTPUT_DIR, pdf_output_filename)
        try:
            generate_pdf_invoice(config_data, pdf_destination_filepath)
            update_last_invoice_number(invoice_number_for_filename) # Update counter
            flash(f"Invoice {excel_output_filename} and PDF {pdf_output_filename} created successfully!", "success")
            # Redirect to a page that offers both downloads, or just the PDF
            return redirect(url_for('success_pdf', filename=pdf_output_filename, excel_filename=excel_output_filename))
        except Exception as e:
            print(f"Error generating PDF: {e}")
            flash(f"Invoice {excel_output_filename} generated, but PDF creation failed: {e}", "warning")
            return redirect(url_for('success', filename=excel_output_filename))

    except Exception as e:
        flash(f"Error generating invoice: {e}", "error")
        print(f"Exception in generate_invoice: {e}")
        import traceback; traceback.print_exc()
        buyer_profiles_data = load_data(BUYER_PROFILES_JSON)
        transport_modes_data = load_data(TRANSPORT_MODES_JSON)
        return render_template('index.html', error=str(e), buyer_profiles=buyer_profiles_data, transport_modes=transport_modes_data, today_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/calculate_preview', methods=['POST'])
def calculate_preview_route():
    data = request.json
    try:
        quantity = float(data.get('quantity', 0))
        rate = float(data.get('rate', 0))
        tax_type = data.get('tax_type', 'IGST')
        item_amount = quantity * rate
        subtotal = float(item_amount)
        igst_amount = 0; cgst_amount = 0; sgst_amount = 0
        if tax_type == "IGST":
            igst_amount = subtotal * TAX_RATES['IGST']
        elif tax_type == "CGST_SGST":
            cgst_amount = subtotal * TAX_RATES['CGST']
            sgst_amount = subtotal * TAX_RATES['SGST']
        total_before_round_off = float(subtotal) + float(igst_amount) + float(cgst_amount) + float(sgst_amount)
        rounded_total = round(total_before_round_off)
        round_off_value = rounded_total - total_before_round_off
        amount_in_words_str = "Zero"
        if rounded_total > 0:
            amount_in_words_str = num2words(int(rounded_total), lang='en_IN').replace('-', ' ').replace(',', '').title()
        amount_in_words = amount_in_words_str + " Only"
        return jsonify({
            "item_amount": f"{item_amount:.2f}",
            "subtotal": f"{subtotal:.2f}",
            "igst_amount": f"{igst_amount:.2f}",
            "cgst_amount": f"{cgst_amount:.2f}",
            "sgst_amount": f"{sgst_amount:.2f}",
            "total_before_round_off": f"{total_before_round_off:.2f}",
            "round_off_value": f"{round_off_value:.2f}",
            "rounded_total": f"{rounded_total:.2f}",
            "amount_in_words": amount_in_words
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/list_profiles')
def list_profiles():
    buyer_profiles = load_data(BUYER_PROFILES_JSON)
    valid_profiles = [p for p in buyer_profiles if p.get('profile_id') and p.get('buyer_name')]
    return render_template('list_profiles.html', profiles=valid_profiles)

@app.route('/manage_profile', methods=['GET', 'POST'])
@app.route('/manage_profile/<profile_id>', methods=['GET', 'POST'])
def manage_profile(profile_id=None):
    buyer_profiles = load_data(BUYER_PROFILES_JSON)
    profile_to_edit = None
    is_new_profile = False
    if profile_id:
        profile_to_edit = next((p for p in buyer_profiles if p.get('profile_id') == profile_id), None)
        if not profile_to_edit:
            flash(f"Profile with ID {profile_id} not found.", "error")
            return redirect(url_for('index'))
    else:
        is_new_profile = True
        profile_to_edit = {"buyer_name": "", "buyer_details": ["", "", "", "", "", ""], "gstin": "", "default_tax_type": "IGST", "profile_id": ""}
    if request.method == 'POST':
        buyer_name = request.form.get('buyer_name', '').strip()
        buyer_details_str = request.form.get('buyer_details_textarea', '')
        buyer_details = [line.strip() for line in buyer_details_str.split('\n') if line.strip()]
        gstin = request.form.get('gstin', '').strip().upper()
        default_tax_type = request.form.get('default_tax_type', 'IGST')
        if not buyer_name:
            flash("Buyer Name is required.", "error")
            return render_template('profile_form.html', profile=request.form, is_new_profile=is_new_profile, profile_id=profile_id)
        if is_new_profile:
            if gstin:
                new_profile_id = f"{buyer_name.replace(' ', '_')}_{gstin}"
            else:
                new_profile_id = f"{buyer_name.replace(' ', '_')}_{uuid.uuid4().hex[:6]}"
            if any(p.get('profile_id') == new_profile_id for p in buyer_profiles):
                flash(f"A profile with ID {new_profile_id} (derived from name/GSTIN) already exists. Please use a unique name or GSTIN.", "error")
                current_data = {"buyer_name": buyer_name, "buyer_details_textarea": buyer_details_str, "gstin": gstin, "default_tax_type": default_tax_type, "profile_id": ""}
                return render_template('profile_form.html', profile=current_data, is_new_profile=True, profile_id=None)
            new_profile = {"profile_id": new_profile_id, "buyer_name": buyer_name, "buyer_details": buyer_details, "gstin": gstin, "default_tax_type": default_tax_type}
            buyer_profiles.append(new_profile)
            flash(f"Profile for {buyer_name} added successfully!", "success")
        else:
            profile_to_update = next((p for p in buyer_profiles if p.get('profile_id') == profile_id), None)
            if profile_to_update:
                profile_to_update['buyer_name'] = buyer_name
                profile_to_update['buyer_details'] = buyer_details
                profile_to_update['gstin'] = gstin
                profile_to_update['default_tax_type'] = default_tax_type
                flash(f"Profile {buyer_name} updated successfully!", "success")
            else:
                flash(f"Error: Profile with ID {profile_id} not found for update.", "error")
                return redirect(url_for('index'))
        if save_data(BUYER_PROFILES_JSON, buyer_profiles):
            return redirect(url_for('index'))
        else:
            current_data = {"buyer_name": buyer_name, "buyer_details_textarea": buyer_details_str, "gstin": gstin, "default_tax_type": default_tax_type, "profile_id": profile_id if not is_new_profile else ""}
            return render_template('profile_form.html', profile=current_data, is_new_profile=is_new_profile, profile_id=profile_id)
    if profile_to_edit and isinstance(profile_to_edit.get('buyer_details'), list):
        profile_to_edit['buyer_details_textarea'] = '\n'.join(profile_to_edit['buyer_details'])
    elif profile_to_edit:
        profile_to_edit['buyer_details_textarea'] = ''
    return render_template('profile_form.html', profile=profile_to_edit, is_new_profile=is_new_profile, profile_id=profile_id)

@app.route('/success')
def success():
    filename = request.args.get('filename')
    return render_template('success.html', filename=filename, download_path=f'/generated_invoices/{filename}', is_pdf=False)

@app.route('/success_pdf')
def success_pdf():
    pdf_filename = request.args.get('filename')
    excel_filename = request.args.get('excel_filename')
    return render_template('success.html',
                           pdf_filename=pdf_filename,
                           excel_filename=excel_filename,
                           is_pdf=True)

@app.route('/generated_invoices/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

@app.route('/generated_invoices_pdf/<filename>')
def download_pdf_file(filename):
    return send_from_directory(PDF_OUTPUT_DIR, filename, as_attachment=True)

@app.route('/api/next_invoice_number')
def api_next_invoice_number():
    return jsonify({"next_invoice_number": get_next_invoice_number()})

if __name__ == '__main__':
    if not TEMPLATE_EXCEL_FILE:
        print("ERROR: No template Excel file found. Place one inside 'GST Invoices'.")
    app.run(debug=True)
