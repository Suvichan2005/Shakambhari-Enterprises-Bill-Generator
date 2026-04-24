"""
Google Sheets Integration for Shakambhari Invoice Generator
============================================================
This module handles all Google Sheets operations for:
- Buyer Profiles (stored in 'Buyers' sheet)
- Transport Modes (stored in 'Transport' sheet)
- Invoice Records (stored in 'Invoices' sheet)
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsDB:
    """
    A database-like interface for Google Sheets.
    Handles buyer profiles, transport modes, and invoice records.
    """
    
    def __init__(self, spreadsheet_id: str = None, credentials_path: str = None):
        """
        Initialize the Google Sheets connection.
        
        Args:
            spreadsheet_id: The ID of the Google Spreadsheet (from URL)
            credentials_path: Path to service account JSON file
        """
        self.spreadsheet_id = spreadsheet_id or os.environ.get('SPREADSHEET_ID')
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        self.client = None
        self.spreadsheet = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Google Sheets."""
        try:
            if self.credentials_path and os.path.exists(self.credentials_path):
                # Use service account file
                creds = Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES
                )
            else:
                # Use default credentials (for Cloud Run/App Engine)
                from google.auth import default
                creds, _ = default(scopes=SCOPES)
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print(f"✓ Connected to Google Sheets: {self.spreadsheet.title}")
        except Exception as e:
            print(f"✗ Failed to connect to Google Sheets: {e}")
            raise
    
    def _get_or_create_sheet(self, sheet_name: str, headers: List[str]) -> gspread.Worksheet:
        """Get a worksheet or create it if it doesn't exist."""
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            worksheet.append_row(headers)
            print(f"✓ Created new sheet: {sheet_name}")
        return worksheet
    
    # ===================== BUYER PROFILES =====================
    
    BUYER_HEADERS = ['profile_id', 'buyer_name', 'buyer_details', 'gstin', 'default_tax_type', 'created_at', 'updated_at']
    
    def get_all_buyers(self) -> List[Dict]:
        """Get all buyer profiles."""
        sheet = self._get_or_create_sheet('Buyers', self.BUYER_HEADERS)
        records = sheet.get_all_records()
        
        # Parse buyer_details from JSON string
        for record in records:
            if record.get('buyer_details'):
                try:
                    record['buyer_details'] = json.loads(record['buyer_details'])
                except json.JSONDecodeError:
                    record['buyer_details'] = record['buyer_details'].split('\n')
            else:
                record['buyer_details'] = []
        
        return records
    
    def get_buyer(self, profile_id: str) -> Optional[Dict]:
        """Get a specific buyer profile."""
        buyers = self.get_all_buyers()
        return next((b for b in buyers if b.get('profile_id') == profile_id), None)
    
    def save_buyer(self, buyer: Dict) -> bool:
        """Save or update a buyer profile."""
        sheet = self._get_or_create_sheet('Buyers', self.BUYER_HEADERS)
        
        # Prepare data
        buyer_details_str = json.dumps(buyer.get('buyer_details', []))
        now = datetime.now().isoformat()
        
        # Check if exists
        try:
            cell = sheet.find(buyer['profile_id'], in_column=1)
            # Update existing
            row_num = cell.row
            sheet.update(f'A{row_num}:G{row_num}', [[
                buyer['profile_id'],
                buyer['buyer_name'],
                buyer_details_str,
                buyer.get('gstin', ''),
                buyer.get('default_tax_type', 'IGST'),
                sheet.cell(row_num, 6).value,  # Keep original created_at
                now
            ]])
        except Exception:
            # Insert new
            sheet.append_row([
                buyer['profile_id'],
                buyer['buyer_name'],
                buyer_details_str,
                buyer.get('gstin', ''),
                buyer.get('default_tax_type', 'IGST'),
                now,
                now
            ])
        
        return True
    
    def delete_buyer(self, profile_id: str) -> bool:
        """Delete a buyer profile."""
        sheet = self._get_or_create_sheet('Buyers', self.BUYER_HEADERS)
        try:
            cell = sheet.find(profile_id, in_column=1)
            sheet.delete_rows(cell.row)
            return True
        except Exception:
            return False
    
    # ===================== TRANSPORT MODES =====================
    
    TRANSPORT_HEADERS = ['mode', 'created_at']
    
    def get_all_transport_modes(self) -> List[str]:
        """Get all transport modes."""
        sheet = self._get_or_create_sheet('Transport', self.TRANSPORT_HEADERS)
        records = sheet.get_all_records()
        return [r['mode'] for r in records if r.get('mode')]
    
    def add_transport_mode(self, mode: str) -> bool:
        """Add a new transport mode if it doesn't exist."""
        sheet = self._get_or_create_sheet('Transport', self.TRANSPORT_HEADERS)
        modes = self.get_all_transport_modes()
        
        # Check if exists (case-insensitive)
        if mode.lower() not in [m.lower() for m in modes]:
            sheet.append_row([mode, datetime.now().isoformat()])
            return True
        return False
    
    # ===================== INVOICE RECORDS =====================
    
    INVOICE_HEADERS = [
        'invoice_number', 'invoice_date', 'buyer_name', 'buyer_gstin', 
        'items_json', 'subtotal', 'tax_type', 'tax_amount', 'total_amount',
        'transport_mode', 'file_url', 'pdf_url', 'created_at'
    ]
    
    def get_all_invoices(self, limit: Optional[int] = 100) -> List[Dict]:
        """Get recent invoices."""
        sheet = self._get_or_create_sheet('Invoices', self.INVOICE_HEADERS)
        records = sheet.get_all_records()
        
        # Parse items JSON
        for record in records:
            if record.get('items_json'):
                try:
                    record['items'] = json.loads(record['items_json'])
                except json.JSONDecodeError:
                    record['items'] = []
        
        # Sort by date descending and limit
        records.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        if limit is None or limit <= 0:
            return records
        return records[:limit]
    
    def save_invoice(self, invoice: Dict) -> bool:
        """Save an invoice record."""
        sheet = self._get_or_create_sheet('Invoices', self.INVOICE_HEADERS)
        
        items_json = json.dumps(invoice.get('items', []))
        now = datetime.now().isoformat()
        
        sheet.append_row([
            invoice.get('invoice_number', ''),
            invoice.get('invoice_date', ''),
            invoice.get('buyer_name', ''),
            invoice.get('buyer_gstin', ''),
            items_json,
            invoice.get('subtotal', 0),
            invoice.get('tax_type', 'IGST'),
            invoice.get('tax_amount', 0),
            invoice.get('total_amount', 0),
            invoice.get('transport_mode', ''),
            invoice.get('file_url', ''),
            invoice.get('pdf_url', ''),
            now
        ])
        return True
    
    def get_invoice(self, invoice_number: str) -> Optional[Dict]:
        """Get a specific invoice by number."""
        target = (invoice_number or '').strip()
        if not target:
            return None

        # Search across full history and return newest match.
        invoices = self.get_all_invoices(limit=None)
        return next((i for i in invoices if (i.get('invoice_number') or '').strip() == target), None)
    
    def get_last_invoice_number(self) -> Optional[str]:
        """Get the most recent invoice number for auto-suggestion."""
        invoices = self.get_all_invoices(limit=10)
        if invoices:
            return invoices[0].get('invoice_number')
        return None


# ===================== HELPER FUNCTIONS =====================

def init_sheets_db() -> GoogleSheetsDB:
    """Initialize and return the Google Sheets database connection."""
    spreadsheet_id = os.environ.get('SPREADSHEET_ID')
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_ID environment variable is not set")
    
    return GoogleSheetsDB(spreadsheet_id=spreadsheet_id)


# For testing locally
if __name__ == '__main__':
    import os
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'service-account.json'
    os.environ['SPREADSHEET_ID'] = 'YOUR_SPREADSHEET_ID'
    
    db = init_sheets_db()
    print("Buyers:", db.get_all_buyers())
    print("Transport:", db.get_all_transport_modes())
    print("Invoices:", db.get_all_invoices(limit=5))
