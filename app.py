import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify # Added jsonify
from datetime import datetime
import uuid  # For generating unique IDs for new profiles without GSTIN
from num2words import num2words # For converting numbers to words
import pythoncom # Added for win32com

# Assuming copy1.py is in the same directory and has the copy_excel_with_formatting function
from copy1 import copy_excel_with_formatting 

# Attempt to import win32com.client for PDF conversion
try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False
    print("WARNING: pywin32 library not found. PDF conversion will be skipped.")

app = Flask(__name__)
app.secret_key = 'your secret key'  # Needed for flash messages

PROFILES_DIR = "c:\\\\Users\\\\KIIT0001\\\\Documents\\\\Bills\\\\Shakambhari Enterprises"
BUYER_PROFILES_JSON = os.path.join(PROFILES_DIR, "buyer_profiles.json")
TRANSPORT_MODES_JSON = os.path.join(PROFILES_DIR, "transport_modes.json")
TEMPLATE_EXCEL_FILE = "C:\\\\Users\\\\KIIT0001\\\\Documents\\\\Bills\\\\Shakambhari Enterprises\\\\GST Invoices\\\\bill 4 2025.xlsx"  # Base template
OUTPUT_DIR = os.path.join(PROFILES_DIR, "Generated_Invoices")
PDF_OUTPUT_DIR = os.path.join(PROFILES_DIR, "Generated_Invoices_PDF") # Separate directory for PDFs

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
if not os.path.exists(PDF_OUTPUT_DIR): # Create PDF output directory
    os.makedirs(PDF_OUTPUT_DIR)

def load_data(json_path):
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        flash(f"Error decoding JSON from {json_path}. Please check its format.", "error")
        return []  # Return empty list if JSON is malformed

def save_data(json_path, data):
    try:
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except IOError:
        flash(f"Error saving data to {json_path}.", "error")
        return False

def convert_excel_to_pdf(excel_filepath, pdf_filepath):
    if not WIN32COM_AVAILABLE:
        print(f"Skipping PDF conversion for {excel_filepath} as pywin32 is not available.")
        return False

    excel = None
    workbook = None
    pythoncom.CoInitialize() # Initialize COM library for the current thread
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False  # Run in background

        # Check if the file exists before trying to open it
        if not os.path.exists(excel_filepath):
            print(f"Error: Excel file not found at {excel_filepath} for PDF conversion.")
            return False

        workbook = excel.Workbooks.Open(excel_filepath)
        
        # Ensure the output directory for the PDF exists
        os.makedirs(os.path.dirname(pdf_filepath), exist_ok=True)
        
        # XPS=1, PDF=0. Using 0 for PDF.
        # Quality: 0 for Standard, 1 for Minimum.
        workbook.ExportAsFixedFormat(0, pdf_filepath, Quality=0, IncludeDocProperties=True, IgnorePrintAreas=False, OpenAfterPublish=False)
        print(f"Successfully converted {excel_filepath} to {pdf_filepath}")
        return True
    except Exception as e:
        print(f"Error converting Excel to PDF: {e}")
        # Try to capture more specific COM errors if possible
        if hasattr(e, 'com_error'):
            print(f"COM Error details: {e.com_error}")
        return False
    finally:
        if workbook:
            workbook.Close(SaveChanges=False)
        if excel:
            excel.Quit()
        pythoncom.CoUninitialize() # Uninitialize COM library

@app.route('/')
def index():
    buyer_profiles = load_data(BUYER_PROFILES_JSON)
    transport_modes = load_data(TRANSPORT_MODES_JSON)
    today_date = datetime.now().strftime('%Y-%m-%d')
    valid_buyer_profiles = [p for p in buyer_profiles if p.get('profile_id') and p.get('buyer_name')]
    return render_template('index.html', 
                           buyer_profiles=valid_buyer_profiles, 
                           transport_modes=transport_modes, 
                           today_date=today_date)

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    try:
        buyer_profile_id = request.form['buyer_profile_id']
        raw_invoice_number_form = request.form['invoice_number'] # Raw number from form
        raw_invoice_date_str_form = request.form['invoice_date'] # Raw date from form
        
        # Keep the raw values for filenames and internal logic
        invoice_number_for_filename = raw_invoice_number_form.strip()
        
        # For display/Excel content, add prefixes
        excel_invoice_number_display = "INVOICE No. " + invoice_number_for_filename if invoice_number_for_filename else ""
        excel_invoice_date_display = "Date : " + raw_invoice_date_str_form.strip() if raw_invoice_date_str_form else ""


        selected_transport_mode = request.form.get('transport_mode')
        new_transport_mode = request.form.get('new_transport_mode', '').strip()
        transport_mode = new_transport_mode if new_transport_mode else selected_transport_mode

        item_description_bags = request.form.get('item_description_bags')
        excel_item_base_description = request.form.get('item_base_description') or '1. Aluminium Utensils' 
        
        item_description = f"{excel_item_base_description}"
        if item_description_bags:
            item_description += f" ({item_description_bags} Bags)"
        
        quantity = float(request.form.get('quantity', 0))
        rate = float(request.form.get('rate', 0))

        buyer_profiles = load_data(BUYER_PROFILES_JSON)
        selected_profile = next((p for p in buyer_profiles if p['profile_id'] == buyer_profile_id), None)

        if not selected_profile:
            flash("Selected buyer profile not found.", "error")
            return redirect(url_for('index'))


        tax_type_override = request.form.get('tax_type_override')
        # Determine final tax type based on override or profile default
        if tax_type_override and tax_type_override != "PROFILE_DEFAULT": # PROFILE_DEFAULT is disabled, so this check is more direct
            final_tax_type = tax_type_override
        else: # If no override or "PROFILE_DEFAULT" (though disabled, good to be robust)
            final_tax_type = selected_profile.get('default_tax_type', 'IGST')


        config = {
            "buyer_details": selected_profile['buyer_details'],
            "mode_of_transport": transport_mode,
            "item_details": {
                "description": item_description,
                "quantity": quantity,
                "rate": rate
            },
            "tax_type": final_tax_type,
            "invoice_number": excel_invoice_number_display, # Use prefixed for Excel content
            "invoice_date": excel_invoice_date_display    # Use prefixed for Excel content
        }
        
        safe_invoice_number_for_file = "".join(c if c.isalnum() else '_' for c in invoice_number_for_filename)
        safe_buyer_name = "".join(c if c.isalnum() else '_' for c in selected_profile.get('buyer_name', 'UnknownBuyer'))
        
        # Excel file generation
        excel_filename_base = f"Invoice_{safe_invoice_number_for_file}_{safe_buyer_name}"
        excel_output_filename = f"{excel_filename_base}.xlsx"
        excel_destination_filepath = os.path.join(OUTPUT_DIR, excel_output_filename)

        copy_excel_with_formatting(TEMPLATE_EXCEL_FILE, excel_destination_filepath, config)

        # PDF Conversion
        pdf_output_filename = f"{excel_filename_base}.pdf"
        pdf_destination_filepath = os.path.join(PDF_OUTPUT_DIR, pdf_output_filename)
        
        pdf_generated_successfully = False
        if WIN32COM_AVAILABLE:
            if convert_excel_to_pdf(excel_destination_filepath, pdf_destination_filepath):
                pdf_generated_successfully = True
                flash(f"Invoice {excel_output_filename} generated and PDF {pdf_output_filename} created successfully!", "success")
                # Redirect to download the PDF
                return redirect(url_for('success_pdf', filename=pdf_output_filename)) 
            else:
                flash(f"Invoice {excel_output_filename} generated, but PDF conversion failed. You can download the Excel file.", "warning")
                # Fallback to Excel download if PDF fails
                return redirect(url_for('success', filename=excel_output_filename))
        else:
            flash(f"Invoice {excel_output_filename} generated. PDF conversion skipped (pywin32 not available).", "info")
            return redirect(url_for('success', filename=excel_output_filename))


    except Exception as e:
        flash(f"Error generating invoice: {str(e)}", "error")
        # Log the full exception for debugging
        print(f"Exception in generate_invoice: {e}")
        import traceback
        traceback.print_exc()
        buyer_profiles_data = load_data(BUYER_PROFILES_JSON)
        transport_modes_data = load_data(TRANSPORT_MODES_JSON)
        return render_template('index.html', 
                               error=str(e), 
                               buyer_profiles=buyer_profiles_data, 
                               transport_modes=transport_modes_data,
                               today_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/calculate_preview', methods=['POST'])
def calculate_preview_route():
    data = request.json
    try:
        quantity = float(data.get('quantity', 0))
        rate = float(data.get('rate', 0))
        tax_type = data.get('tax_type', 'IGST') # Default to IGST if not provided

        item_amount = quantity * rate
        subtotal = float(item_amount)  # Assuming one item for now

        igst_amount = 0
        cgst_amount = 0
        sgst_amount = 0
        
        # Standard tax rates (as in copy1.py)
        igst_rate_val = 0.12 
        cgst_rate_val = 0.06
        sgst_rate_val = 0.06

        if tax_type == "IGST":
            igst_amount = subtotal * igst_rate_val
        elif tax_type == "CGST_SGST":
            cgst_amount = subtotal * cgst_rate_val
            sgst_amount = subtotal * sgst_rate_val

        total_before_round_off = float(subtotal) + float(igst_amount) + float(cgst_amount) + float(sgst_amount)
        rounded_total = round(total_before_round_off)
        round_off_value = rounded_total - total_before_round_off

        amount_in_words_str = "Zero"
        if rounded_total > 0:
            amount_in_words_str = num2words(int(rounded_total), lang='en_IN')
            amount_in_words_str = amount_in_words_str.replace('-', ' ').replace(',', '').title()
        
        amount_in_words = str(amount_in_words_str) + " Only"

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
    # Ensure profiles are somewhat valid for listing, e.g., have a name and ID
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
                current_data = {
                    "buyer_name": buyer_name,
                    "buyer_details_textarea": buyer_details_str,
                    "gstin": gstin,
                    "default_tax_type": default_tax_type,
                    "profile_id": ""
                }
                return render_template('profile_form.html', profile=current_data, is_new_profile=True, profile_id=None)

            new_profile = {
                "profile_id": new_profile_id,
                "buyer_name": buyer_name,
                "buyer_details": buyer_details,
                "gstin": gstin,
                "default_tax_type": default_tax_type
            }
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
            current_data = {
                "buyer_name": buyer_name,
                "buyer_details_textarea": buyer_details_str,
                "gstin": gstin,
                "default_tax_type": default_tax_type,
                "profile_id": profile_id if not is_new_profile else ""
            }
            return render_template('profile_form.html', profile=current_data, is_new_profile=is_new_profile, profile_id=profile_id)

    if profile_to_edit and isinstance(profile_to_edit.get('buyer_details'), list):
        profile_to_edit['buyer_details_textarea'] = '\n'.join(profile_to_edit['buyer_details'])
    elif profile_to_edit:
        profile_to_edit['buyer_details_textarea'] = ''

    return render_template('profile_form.html', profile=profile_to_edit, is_new_profile=is_new_profile, profile_id=profile_id)

@app.route('/success')
def success():
    filename = request.args.get('filename')
    # This route now primarily serves as a fallback or if PDF generation is skipped/failed
    return render_template('success.html', filename=filename, download_path=f'/generated_invoices/{filename}', is_pdf=False)

@app.route('/success_pdf') # New route for PDF success page
def success_pdf():
    filename = request.args.get('filename')
    return render_template('success.html', filename=filename, download_path=f'/generated_invoices_pdf/{filename}', is_pdf=True)


@app.route('/generated_invoices/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

@app.route('/generated_invoices_pdf/<filename>') # New route to download PDFs
def download_pdf_file(filename):
    return send_from_directory(PDF_OUTPUT_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists(TEMPLATE_EXCEL_FILE):
        print(f"ERROR: Template Excel file not found at {TEMPLATE_EXCEL_FILE}")
        print("Please ensure the template file exists and the path is correct in app.py")
    else:
        app.run(debug=True)
