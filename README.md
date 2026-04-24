# Shakambhari Bill Generator 🧾

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Google Cloud Run](https://img.shields.io/badge/Google_Cloud-Cloud_Run-blue?logo=googlecloud)](https://cloud.google.com/run)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A scalable deployment of an automated invoice generation platform built with Python, Flask, and Google Cloud Services. Originally developed to solve a real-world business problem automating manual Excel billing for a family business, this project evolved into a robust web application that handles complex Indian GST tax logic, dynamic Excel styling, PDF generation, and secure cloud storage.

## 🚀 Key Features

*   **Dynamic Invoice Generation:** Programmatically generates pixel-perfect `.xlsx` and `.pdf` invoices using `openpyxl`. Preserves complex formatting, typography, and borders dynamically as new rows are appended.
*   **Complex Tax Logic Engine:** Automatically computes localized taxes (CGST/SGST for intra-state vs. IGST for inter-state) with precise floating-point rounding logic down to the exact penny.

*   **Serverless Cloud Deployment:** Deployed via Google Cloud Run (`cloud/app.yaml` & `Dockerfile`) for 100% uptime and horizontal scaling. Includes secure handling of API keys using secret management.
*   **Data Management & Profiles:** Full CRUD capabilities for maintaining a persistent database of Buyer Profiles and Transport Modes, eliminating repetitive data entry.
*   **Security & Authentication:** Includes a stateless session-based authentication gate for secure public-facing deployments.
*   **Dual-Environment Support:** Seamlessly runs as a standalone local desktop app (using `pywin32` for fast offline PDF rendering) or as a containerized web application deployed to GCP.

## 🛠️ Technology Stack

*   **Backend:** Python, Flask, Gunicorn
*   **Cloud Infrastructure:** Google Cloud Platform (GCP) - Cloud Run, Cloud Storage, Google Sheets API.
*   **Document Processing:** `openpyxl` (Excel templating, dynamic style cloning), `WeasyPrint` / `pdfkit` (PDF compilation).
*   **Frontend:** HTML5, CSS3, JavaScript (Jinja2 Templates).

## 💡 Technical Challenges Overcome

1.  **Dynamic Template Styling:** `openpyxl` by default does not inherit cell formatting when inserting new rows. Engineered a custom loop to deep-copy fonts, alignments, and number formats from anchor rows to dynamically appended item rows.
2.  **Tax Rounding Anomalies:** Addressed edge-case floating-point division errors where Rs 0.03 deviations would occur in high-volume invoices by normalizing item-level computations before summing the grand total.
3.  **Scope & State Management:** Refactored taxation logic that previously caused `UnboundLocalError` crashes on conditional tax scopes during production scaling.
4.  **Secure Deployment:** Hardened the repository ensuring `.env`, `service-account.json`, and all PII/database artifacts are strictly ignored via `.gitignore`, securely passing credentials to the container runtime.

## 💻 Setup & Installation

### Local Desktop Environment
1. Clone the repository:
   ```bash
   git clone https://github.com/Suvichan2005/Shakambhari-Enterprises-Bill-Generator.git
   cd Shakambhari-Enterprises-Bill-Generator
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the local application:
   ```bash
   python app.py
   ```
   *Note: Local PDF generation utilizes Microsoft Excel via COM objects (`pywin32`) and requires Windows.*

### Cloud Run Deployment (GCP)
For deploying the cloud-native variant of the application:
1. Navigate to the cloud directory:
   ```bash
   cd cloud
   ```
2. Provide your environment variables in `.env` (Ignored by Git for security).
3. Deploy to Google Cloud Run:
   ```bash
   gcloud run deploy shakambhari-invoices --source .
   ```

## 📂 Project Structure

```
├── app.py                   # Local web server entry point
├── config.py                # Central configuration and path utilities
├── extract_invoice_data.py  # Utilities for reading past Excel sheets logically
├── cloud/                   # Cloud-native infrastructure & modified backend
│   ├── app_cloud.py         # Flask backend configured for GCP Serverless
│   ├── cloud_storage.py     # GCP Bucket interfaces
│   ├── sheets_db.py         # Google Sheets Database integration
│   ├── app.yaml             # App Engine / Run deployment definitions
│   └── Dockerfile           # Container specification
├── templates/               # Jinja2 HTML themes and frontend UI
└── requirements.txt         # Python package dependencies
```

## 🤝 Contact

Feel free to reach out if you have any questions about the repository, architectural decisions, or my experience building it!

