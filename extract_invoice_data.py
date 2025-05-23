import os
import json
import openpyxl
import hashlib

INVOICES_DIRS = [ # Changed to a list of directories
    "C:\\Users\\KIIT0001\\Documents\\Bills\\Shakambhari Enterprises\\GST Invoices",
    "C:\\Users\\KIIT0001\\Documents\\Bills\\Shakambhari Enterprises\\GST Invoices\\Old GST Invoices"
]
BUYER_PROFILES_JSON = "c:\\Users\\KIIT0001\\Documents\\Bills\\Shakambhari Enterprises\\buyer_profiles.json"
TRANSPORT_MODES_JSON = "c:\\Users\\KIIT0001\\Documents\\Bills\\Shakambhari Enterprises\\transport_modes.json"

def extract_buyer_name_from_details(details_list):
    if not details_list:
        return "Unknown Buyer"
    # Check if the first line is "Buyer :" and the second line has the name
    if len(details_list) > 1 and "buyer :" in details_list[0].lower().strip():
        name = details_list[1].strip()
        return name if name else "Unknown Buyer"
    # Fallback: check if the first line contains "Buyer : Actual Name"
    if "buyer :" in details_list[0].lower():
        parts = details_list[0].split(":", 1)
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip()
    # Fallback: use the first non-empty line as a potential name, if it doesn't look like a typical address line
    for line in details_list:
        if line.strip() and not any(kw in line.lower() for kw in ["road", "nagar", "street", "state", "gstin", "code", "india", "bazar"]): # Added "bazar"
            return line.strip()
    return details_list[0].strip() if details_list and details_list[0].strip() else "Unknown Buyer"

def extract_gstin_from_details(details_list):
    for detail in details_list:
        detail_lower = detail.lower()
        if "gstin" in detail_lower:
            # Try to split by " - " or ":" and take the last part
            # Remove "GSTIN" and "STATE ... CODE" parts before splitting for cleaner extraction
            cleaned_detail = detail_lower.replace("gstin", "")
            if "state" in cleaned_detail: # Remove state part if present on same line
                 cleaned_detail = cleaned_detail.split("state")[0]
            
            parts = []
            if ":" in cleaned_detail:
                parts = cleaned_detail.split(":", 1)
            elif "-" in cleaned_detail: # Use generic hyphen
                parts = cleaned_detail.split("-", 1)
            
            if len(parts) > 1 and parts[1].strip():
                # Further clean up common prefixes/suffixes if any around the GSTIN
                gstin_val = parts[1].strip().upper()
                # A typical GSTIN is 15 characters. This is a basic check.
                if len(gstin_val) >= 15:
                     # Extract the first 15 alphanumeric characters as GSTIN can sometimes have extra text
                    import re
                    match = re.search(r'[0-9A-Z]{15}', gstin_val)
                    if match:
                        return match.group(0)
                return gstin_val # return whatever found if regex fails
            elif len(parts) == 1 and parts[0].strip(): # Case where only GSTIN value might be left after cleaning
                gstin_val = parts[0].strip().upper()
                import re
                match = re.search(r'[0-9A-Z]{15}', gstin_val)
                if match:
                    return match.group(0)
                return gstin_val


    return None

def get_profile_id(gstin, buyer_details_tuple):
    if gstin:
        return gstin
    # If no GSTIN, create a hash of the buyer details for a unique ID
    hasher = hashlib.md5()
    hasher.update(str(buyer_details_tuple).encode('utf-8'))
    return f"hash_{hasher.hexdigest()}"

def main():
    buyer_profiles_dict = {}
    transport_modes_set = set()

    for invoices_dir in INVOICES_DIRS: # Iterate through each directory
        print(f"Scanning directory: {invoices_dir}")
        if not os.path.exists(invoices_dir):
            print(f"Warning: Directory not found - {invoices_dir}")
            continue

        for filename in os.listdir(invoices_dir):
            if filename.endswith(".xlsx") and not filename.startswith("~"):
                filepath = os.path.join(invoices_dir, filename)
                print(f"Processing file: {filepath}")
                try:
                    workbook = openpyxl.load_workbook(filepath, data_only=True)
                    sheet = workbook.active

                    current_buyer_details = []
                    for i in range(8, 16):  # A8 to A15
                        cell_value = sheet[f'A{i}'].value
                        current_buyer_details.append(str(cell_value).strip() if cell_value is not None else "")
                    # Filter out trailing empty strings from buyer_details for cleaner storage
                    while current_buyer_details and not current_buyer_details[-1]:
                        current_buyer_details.pop()

                    current_mode_of_transport = str(sheet['E10'].value).strip() if sheet['E10'].value is not None else ""
                    if current_mode_of_transport:
                        transport_modes_set.add(current_mode_of_transport)

                    current_tax_type = "UNKNOWN"
                    igst_val_cell = sheet['I30'].value
                    cgst_val_cell = sheet['I31'].value
                    
                    # Check numeric values first
                    igst_amount = float(igst_val_cell) if isinstance(igst_val_cell, (int, float)) else 0.0
                    cgst_amount = float(cgst_val_cell) if isinstance(cgst_val_cell, (int, float)) else 0.0

                    # Check percentage labels in column E
                    e30_val = str(sheet['E30'].value or "").strip()
                    e31_val = str(sheet['E31'].value or "").strip()

                    if igst_amount > 0 and e30_val not in ["0.00%", "0%"]:
                        current_tax_type = "IGST"
                    elif cgst_amount > 0 and e31_val not in ["0.00%", "0%"]:
                        current_tax_type = "CGST_SGST"
                    else: # Fallback to labels in C if amounts are zero or percentages are ambiguous
                        c30_label = str(sheet['C30'].value or "").upper()
                        c31_label = str(sheet['C31'].value or "").upper()
                        if "I.G.S.T" in c30_label and e30_val not in ["0.00%", "0%"]:
                            current_tax_type = "IGST"
                        elif "C.G.S.T" in c31_label and e31_val not in ["0.00%", "0%"]:
                            current_tax_type = "CGST_SGST"
                    
                    extracted_gstin = extract_gstin_from_details(current_buyer_details)
                    extracted_buyer_name = extract_buyer_name_from_details(current_buyer_details)

                    profile_id = get_profile_id(extracted_gstin, tuple(current_buyer_details))

                    # Add or update buyer profile
                    # If profile exists, current data (especially tax type) from this file will overwrite
                    # This ensures the latest file processed for a given GSTIN sets its default_tax_type
                    buyer_profiles_dict[profile_id] = {
                        "profile_id": profile_id, # Store the ID used (GSTIN or hash)
                        "buyer_name": extracted_buyer_name,
                        "buyer_details": current_buyer_details,
                        "gstin": extracted_gstin if extracted_gstin else "",
                        "default_tax_type": current_tax_type
                    }
                    print(f"  Processed profile for: {extracted_buyer_name} (ID: {profile_id}, Tax: {current_tax_type})")

                except Exception as e:
                    print(f"Error processing file {filepath}: {e}")

    # Convert dictionary to list for JSON output
    final_buyer_profiles = sorted(list(buyer_profiles_dict.values()), key=lambda p: p['buyer_name'])
    final_transport_modes = sorted(list(transport_modes_set))
    # Filter out empty transport modes
    final_transport_modes = [mode for mode in final_transport_modes if mode]


    with open(BUYER_PROFILES_JSON, 'w') as f:
        json.dump(final_buyer_profiles, f, indent=4)
    print(f"\\nSuccessfully extracted {len(final_buyer_profiles)} buyer profiles to {BUYER_PROFILES_JSON}")

    with open(TRANSPORT_MODES_JSON, 'w') as f:
        json.dump(final_transport_modes, f, indent=4)
    print(f"Successfully extracted {len(final_transport_modes)} unique transport modes to {TRANSPORT_MODES_JSON}")

if __name__ == "__main__":
    main()
