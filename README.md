# Shakambhari Bill Generator

This is a personal project built to help automate and simplify the invoice and bill generation process for my dad's business. The application provides a user-friendly web interface to generate GST-compliant invoices in both Excel (XLSX) and PDF formats, with features tailored for Indian business needs.

## Features

- **Buyer Profile Management:** Add, edit, and manage buyer profiles with GSTIN and address details.
- **Transport Modes:** Save and reuse common transport modes for invoices.
- **Live Invoice Preview:** See a real-time preview of the invoice as you fill out the form.
- **Tax Calculation:** Supports IGST and CGST/SGST calculations as per Indian GST rules.
- **Invoice Generation:** Generates invoices in Excel format using a template, and automatically converts them to PDF (requires Windows and MS Excel).
- **Download Links:** Download generated invoices in both XLSX and PDF formats.
- **Relative Paths:** All file operations use paths relative to the project directory for easy portability.

## Why I Built This

My dad runs a business and used to spend a lot of time manually creating invoices in Excel. This project was created to make his work easier, reduce errors, and save time by automating repetitive billing tasks. It is designed to be simple enough for non-technical users to operate locally on a Windows PC.

## Requirements

- **Windows OS** (for PDF generation via Excel automation)
- **Python 3.8+**
- **Microsoft Excel** (for PDF export)
- **pip** (Python package manager)

## Setup Instructions

1. **Clone the repository:**
   ```sh
   git clone <your-repo-url>
   cd Shakambhari-Bill-Generator
   ```

2. **Create a virtual environment (optional but recommended):**
   ```sh
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Check the Excel template:**
   - Place your invoice template in the `GST Invoices/` folder and update the template filename in `app.py` if needed.

5. **Run the application:**
   - You can use the batch file for convenience:
     ```sh
     Shakambhari Bill Gen.bat
     ```
   - Or run manually:
     ```sh
     python app.py
     ```

6. **Open your browser and go to:**
   - [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## Notes

- **PDF Generation:**
  - PDF export requires Windows, Microsoft Excel, and the `pywin32` Python package.
  - On Linux or Mac, only Excel (XLSX) export will work unless you adapt the code to use a cross-platform PDF library.
- **Data Storage:**
  - Buyer profiles and transport modes are stored as JSON files in the project directory.
- **Customization:**
  - You can modify the Excel template and the HTML files in `templates/` to suit your needs.
