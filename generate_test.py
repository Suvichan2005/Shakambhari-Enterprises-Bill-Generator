import sys
import os
from pathlib import Path
ROOT = Path(__file__).parent
# Ensure we can import modules from the cloud folder
sys.path.insert(0, str(ROOT / 'cloud'))
import app_cloud as ac

TEMPLATE = ROOT / '_cloud_template_Annapurna.xlsx'
OUT_DIR = ROOT / 'Generated_Invoices'
OUT_DIR.mkdir(parents=True, exist_ok=True)

class DummyStorage:
    def __init__(self, template_path: Path):
        self._bytes = template_path.read_bytes()
        self._name = template_path.name
    def download_template(self):
        return (self._bytes, self._name)
    def download_file(self, candidate):
        return None
    def upload_invoice_xlsx(self, data, filename):
        p = OUT_DIR / filename
        p.write_bytes(data)
        return f'file://{p}'
    def upload_invoice_pdf(self, data, filename):
        p = OUT_DIR / filename
        p.write_bytes(data)
        return f'file://{p}'
    def list_invoices(self, limit=100):
        return []

if not TEMPLATE.exists():
    print('Template not found:', TEMPLATE)
    sys.exit(1)

# Patch storage
ac.get_cloud_storage = lambda: DummyStorage(TEMPLATE)

# Build sample invoice data
items = [
    {'description': 'Sample Item A', 'quantity': 10, 'rate': 123.45, 'hsn': '7201'},
    {'description': 'Sample Item B', 'quantity': 5, 'rate': 200.00, 'hsn': '7202'},
]

invoice_data = {
    'invoice_number': '999',
    'invoice_date': '2026-08-04',
    'invoice_date_display': '04/08/2026',
    'buyer_name': 'Test Buyer',
    'buyer_gstin': '19ACZPN5725A1Z8',
    'buyer_details': ['Buyer:', 'Test Buyer', '1 Test Road', 'GSTIN - 19ACZPN5725A1Z8'],
    'ewaybill_number': 'EW1234567890',
    'ewaybill_date': '2026-08-04',
    'ewaybill_date_display': '04/08/2026',
    'ship_from_details': ['Shakambhari Enterprises', 'Om Bhawan, 144/145 J.N Mukherjee Road'],
    'ship_to_enabled': True,
    'ship_to_details': ['Customer Location', 'Somewhere, India'],
    'digitally_signed': True,
    'items': items,
    'transport_mode': 'Mode of Transport: Road',
    'delivery_charge': 50.0,
    'tax_type': 'IGST',
    'display_tax_type': 'IGST',
    'tax_rate_igst': 5.0,
    'tax_rate_cgst': 0.0,
    'tax_rate_sgst': 0.0,
    'subtotal': sum(i['quantity']*i['rate'] for i in items),
    'igst_rate': 5.0,
    'igst_amount': 0.0,
    'cgst_rate': 0.0,
    'cgst_amount': 0.0,
    'sgst_rate': 0.0,
    'sgst_amount': 0.0,
    'round_off_value': 0.0,
    'rounded_total': 0,
    'amount_in_words': ''
}

print('Generating XLSX...')
try:
    xlsx = ac.generate_invoice_excel(invoice_data)
    out_xlsx = OUT_DIR / f'Invoice_test_{invoice_data["invoice_number"]}.xlsx'
    out_xlsx.write_bytes(xlsx)
    print('Wrote', out_xlsx)
except Exception as e:
    print('Failed to generate XLSX:', e)

print('Attempting PDF (WeasyPrint) generation...')
try:
    pdf = ac.generate_invoice_pdf(invoice_data)
    if pdf:
        out_pdf = OUT_DIR / f'Invoice_test_{invoice_data["invoice_number"]}.pdf'
        out_pdf.write_bytes(pdf)
        print('Wrote', out_pdf)
    else:
        print('PDF generation not available or failed (WeasyPrint missing).')
except Exception as e:
    print('PDF generation error:', e)

print('Done')
