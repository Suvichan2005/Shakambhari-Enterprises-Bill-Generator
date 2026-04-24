"""
Migration Script: Local Data to Google Cloud
=============================================
This script migrates your existing local data to Google Cloud:
1. Buyer profiles (JSON → Google Sheets)
2. Transport modes (JSON → Google Sheets)
3. Existing invoices (Excel files → Cloud Storage + Sheets)
4. Invoice template (Excel → Cloud Storage)

Prerequisites:
- Set up Google Cloud project
- Create service account and download JSON key
- Set environment variables
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from sheets_db import GoogleSheetsDB
    from cloud_storage import CloudStorage
    import openpyxl
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install gspread google-auth google-cloud-storage openpyxl")
    sys.exit(1)


class DataMigrator:
    """Handles migration from local files to Google Cloud."""
    
    def __init__(self, local_data_dir: str, spreadsheet_id: str, bucket_name: str):
        """
        Initialize the migrator.
        
        Args:
            local_data_dir: Path to the local Shakambhari Enterprises folder
            spreadsheet_id: Google Spreadsheet ID for data storage
            bucket_name: Google Cloud Storage bucket name
        """
        self.local_dir = Path(local_data_dir)
        self.spreadsheet_id = spreadsheet_id
        self.bucket_name = bucket_name
        
        self.sheets_db = None
        self.cloud_storage = None
        
        self.stats = {
            'buyers_migrated': 0,
            'transport_modes_migrated': 0,
            'invoices_migrated': 0,
            'templates_uploaded': 0,
            'errors': []
        }
    
    def connect(self):
        """Establish connections to Google services."""
        print("Connecting to Google services...")
        
        try:
            self.sheets_db = GoogleSheetsDB(spreadsheet_id=self.spreadsheet_id)
            print("✓ Connected to Google Sheets")
        except Exception as e:
            print(f"✗ Failed to connect to Google Sheets: {e}")
            raise
        
        try:
            self.cloud_storage = CloudStorage(bucket_name=self.bucket_name)
            print("✓ Connected to Cloud Storage")
        except Exception as e:
            print(f"✗ Failed to connect to Cloud Storage: {e}")
            raise
    
    def migrate_buyers(self):
        """Migrate buyer profiles from JSON to Google Sheets."""
        print("\n--- Migrating Buyer Profiles ---")
        
        json_path = self.local_dir / 'buyer_profiles.json'
        if not json_path.exists():
            print(f"✗ File not found: {json_path}")
            return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                buyers = json.load(f)
            
            print(f"Found {len(buyers)} buyer profiles")
            
            for buyer in buyers:
                try:
                    # Ensure required fields
                    if not buyer.get('profile_id') or not buyer.get('buyer_name'):
                        print(f"  ⚠ Skipping invalid profile: {buyer}")
                        continue
                    
                    self.sheets_db.save_buyer(buyer)
                    self.stats['buyers_migrated'] += 1
                    print(f"  ✓ Migrated: {buyer['buyer_name']}")
                    
                except Exception as e:
                    error_msg = f"Failed to migrate buyer {buyer.get('buyer_name', 'unknown')}: {e}"
                    print(f"  ✗ {error_msg}")
                    self.stats['errors'].append(error_msg)
            
            print(f"✓ Migrated {self.stats['buyers_migrated']} buyer profiles")
            
        except Exception as e:
            print(f"✗ Error reading buyers JSON: {e}")
            self.stats['errors'].append(str(e))
    
    def migrate_transport_modes(self):
        """Migrate transport modes from JSON to Google Sheets."""
        print("\n--- Migrating Transport Modes ---")
        
        json_path = self.local_dir / 'transport_modes.json'
        if not json_path.exists():
            print(f"✗ File not found: {json_path}")
            return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                modes = json.load(f)
            
            print(f"Found {len(modes)} transport modes")
            
            for mode in modes:
                try:
                    if mode and isinstance(mode, str):
                        self.sheets_db.add_transport_mode(mode)
                        self.stats['transport_modes_migrated'] += 1
                        print(f"  ✓ Added: {mode}")
                except Exception as e:
                    print(f"  ✗ Failed to add mode '{mode}': {e}")
            
            print(f"✓ Migrated {self.stats['transport_modes_migrated']} transport modes")
            
        except Exception as e:
            print(f"✗ Error reading transport modes JSON: {e}")
            self.stats['errors'].append(str(e))
    
    def migrate_invoices(self, invoices_dir: str = 'Generated_Invoices'):
        """Migrate generated invoices to Cloud Storage and record in Sheets."""
        print("\n--- Migrating Generated Invoices ---")
        
        invoices_path = self.local_dir / invoices_dir
        if not invoices_path.exists():
            print(f"✗ Directory not found: {invoices_path}")
            return
        
        xlsx_files = list(invoices_path.glob('*.xlsx'))
        print(f"Found {len(xlsx_files)} Excel invoice files")
        
        for xlsx_file in xlsx_files:
            try:
                print(f"  Processing: {xlsx_file.name}")
                
                # Upload Excel file
                with open(xlsx_file, 'rb') as f:
                    file_data = f.read()
                
                xlsx_url = self.cloud_storage.upload_invoice_xlsx(file_data, xlsx_file.name)
                
                # Try to extract invoice data from Excel
                invoice_data = self._extract_invoice_data(xlsx_file)
                
                if invoice_data:
                    invoice_data['file_url'] = xlsx_url
                    
                    # Check for corresponding PDF
                    pdf_path = self.local_dir / 'Generated_Invoices_PDF' / xlsx_file.name.replace('.xlsx', '.pdf')
                    if pdf_path.exists():
                        with open(pdf_path, 'rb') as f:
                            pdf_data = f.read()
                        pdf_url = self.cloud_storage.upload_invoice_pdf(pdf_data, pdf_path.name)
                        invoice_data['pdf_url'] = pdf_url
                    
                    # Save to Sheets
                    self.sheets_db.save_invoice(invoice_data)
                
                self.stats['invoices_migrated'] += 1
                print(f"    ✓ Uploaded: {xlsx_file.name}")
                
            except Exception as e:
                error_msg = f"Failed to migrate invoice {xlsx_file.name}: {e}"
                print(f"    ✗ {error_msg}")
                self.stats['errors'].append(error_msg)
        
        print(f"✓ Migrated {self.stats['invoices_migrated']} invoices")
    
    def _extract_invoice_data(self, xlsx_path: Path) -> dict:
        """Extract invoice data from an Excel file."""
        try:
            wb = openpyxl.load_workbook(xlsx_path, data_only=True)
            sheet = wb.active
            
            # Extract invoice number
            invoice_num_raw = sheet['E2'].value or ''
            invoice_number = str(invoice_num_raw).replace('INVOICE No.', '').replace('Invoice No.', '').strip()
            
            # Extract date
            date_raw = sheet['H2'].value or ''
            date_str = str(date_raw).replace('Date :', '').replace('Date:', '').strip()
            
            # Try to parse date
            invoice_date = ''
            try:
                dt = datetime.strptime(date_str, '%d/%m/%Y')
                invoice_date = dt.strftime('%Y-%m-%d')
            except:
                pass
            
            # Extract buyer name
            buyer_name = str(sheet['A9'].value or '').strip()
            
            # Extract GSTIN
            gstin = ''
            for row in range(9, 16):
                cell_val = str(sheet[f'A{row}'].value or '')
                gstin_match = re.search(r'GSTIN\s*[-:]\s*([A-Z0-9]{15})', cell_val, re.IGNORECASE)
                if gstin_match:
                    gstin = gstin_match.group(1)
                    break
            
            # Extract items
            items = []
            for row in range(18, 28):
                desc = sheet[f'A{row}'].value
                qty = sheet[f'F{row}'].value
                rate = sheet[f'G{row}'].value
                
                if desc or (qty and rate):
                    items.append({
                        'description': str(desc or '').strip(),
                        'quantity': float(qty) if qty else 0,
                        'rate': float(rate) if rate else 0
                    })
            
            # Extract totals
            subtotal = sheet['I29'].value or 0
            total = sheet['I33'].value or 0
            
            # Determine tax type
            tax_type = 'IGST'
            if sheet['I31'].value and float(sheet['I31'].value or 0) > 0:
                tax_type = 'CGST_SGST'
            
            wb.close()
            
            return {
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'buyer_name': buyer_name,
                'buyer_gstin': gstin,
                'items': items,
                'subtotal': float(subtotal) if subtotal else 0,
                'tax_type': tax_type,
                'tax_amount': (float(subtotal) * 0.05) if subtotal else 0,
                'total_amount': float(total) if total else 0,
                'transport_mode': str(sheet['E10'].value or '').replace('Mode of Transport :', '').strip()
            }
            
        except Exception as e:
            print(f"    ⚠ Could not extract data: {e}")
            return {}
    
    def upload_template(self, template_dir: str = 'GST Invoices'):
        """Upload the invoice template to Cloud Storage."""
        print("\n--- Uploading Invoice Template ---")
        
        template_path = self.local_dir / template_dir
        if not template_path.exists():
            print(f"✗ Directory not found: {template_path}")
            return
        
        xlsx_files = list(template_path.glob('*.xlsx'))
        if not xlsx_files:
            print(f"✗ No Excel template found in {template_path}")
            return
        
        # Use the first xlsx file as template
        template_file = xlsx_files[0]
        print(f"Uploading template: {template_file.name}")
        
        try:
            with open(template_file, 'rb') as f:
                file_data = f.read()
            
            url = self.cloud_storage.upload_template(file_data, template_file.name)
            self.stats['templates_uploaded'] += 1
            print(f"✓ Uploaded template: {url}")
            
        except Exception as e:
            error_msg = f"Failed to upload template: {e}"
            print(f"✗ {error_msg}")
            self.stats['errors'].append(error_msg)
    
    def run_full_migration(self):
        """Run the complete migration process."""
        print("=" * 60)
        print("SHAKAMBHARI ENTERPRISES - DATA MIGRATION")
        print("=" * 60)
        print(f"Local directory: {self.local_dir}")
        print(f"Spreadsheet ID: {self.spreadsheet_id}")
        print(f"Bucket name: {self.bucket_name}")
        print("=" * 60)
        
        self.connect()
        
        self.upload_template()
        self.migrate_buyers()
        self.migrate_transport_modes()
        self.migrate_invoices()
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"Buyers migrated: {self.stats['buyers_migrated']}")
        print(f"Transport modes migrated: {self.stats['transport_modes_migrated']}")
        print(f"Invoices migrated: {self.stats['invoices_migrated']}")
        print(f"Templates uploaded: {self.stats['templates_uploaded']}")
        
        if self.stats['errors']:
            print(f"\n⚠ {len(self.stats['errors'])} errors occurred:")
            for error in self.stats['errors'][:10]:
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
        else:
            print("\n✓ No errors!")
        
        print("=" * 60)


def main():
    """Main entry point for migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate Shakambhari data to Google Cloud')
    parser.add_argument('--local-dir', required=True, help='Path to local Shakambhari Enterprises folder')
    parser.add_argument('--spreadsheet-id', required=True, help='Google Spreadsheet ID')
    parser.add_argument('--bucket-name', required=True, help='Google Cloud Storage bucket name')
    parser.add_argument('--credentials', help='Path to service account JSON file')
    
    args = parser.parse_args()
    
    if args.credentials:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = args.credentials
    
    migrator = DataMigrator(
        local_data_dir=args.local_dir,
        spreadsheet_id=args.spreadsheet_id,
        bucket_name=args.bucket_name
    )
    
    migrator.run_full_migration()


if __name__ == '__main__':
    main()
