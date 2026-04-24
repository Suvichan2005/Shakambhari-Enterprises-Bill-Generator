# 🚀 Shakambhari Enterprises - Cloud Deployment Guide

## Complete Guide to Hosting on Google Cloud

This guide will walk you through deploying the Shakambhari Invoice Generator to Google Cloud, making it accessible from anywhere via a web browser.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Google Cloud Setup](#step-1-google-cloud-setup)
4. [Step 2: Google Sheets Setup](#step-2-google-sheets-setup)
5. [Step 3: Cloud Storage Setup](#step-3-cloud-storage-setup)
6. [Step 4: Migrate Local Data](#step-4-migrate-local-data)
7. [Step 5: Deploy the Application](#step-5-deploy-the-application)
8. [Step 6: Access Your Application](#step-6-access-your-application)
9. [Cost Estimation](#cost-estimation)
10. [Maintenance & Troubleshooting](#maintenance--troubleshooting)

---

## Overview

### What Changes in the Cloud Version?

| Feature | Local Version | Cloud Version |
|---------|--------------|---------------|
| **Data Storage** | JSON files | Google Sheets |
| **File Storage** | Local folders | Google Cloud Storage |
| **PDF Generation** | Windows COM (win32com) | WeasyPrint (cross-platform) |
| **Access** | Only on your PC | Any device with internet |
| **Backup** | Manual | Automatic (Google manages) |

### Architecture Diagram

```
┌─────────────────┐     ┌─────────────────────────────┐
│   Your Browser  │────▶│  Google Cloud Run / App     │
│   (Phone/PC)    │     │  Engine (Flask App)         │
└─────────────────┘     └──────────┬──────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌───────────┐  ┌───────────┐  ┌───────────┐
            │  Google   │  │  Google   │  │  Invoice  │
            │  Sheets   │  │  Cloud    │  │  Template │
            │  (Data)   │  │  Storage  │  │  (XLSX)   │
            └───────────┘  │  (Files)  │  └───────────┘
                           └───────────┘
```

---

## Prerequisites

Before starting, ensure you have:

- [ ] A Google account (Gmail)
- [ ] A credit/debit card for Google Cloud (free tier available)
- [ ] Python 3.9+ installed on your PC
- [ ] Google Cloud SDK installed ([Download](https://cloud.google.com/sdk/docs/install))
- [ ] Your current Shakambhari Enterprises folder with all data

---

## Step 1: Google Cloud Setup

### 1.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Create Project"** (or select from dropdown)
3. Enter project details:
   - **Project Name:** `shakambhari-invoices`
   - **Project ID:** `shakambhari-invoices` (note this down!)
4. Click **"Create"**

### 1.2 Enable Required APIs

Run these commands in your terminal (or enable via Console):

```powershell
# Authenticate with Google Cloud
gcloud auth login

# Set your project
gcloud config set project shakambhari-invoices

# Enable required APIs
gcloud services enable sheets.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 1.3 Create a Service Account

This allows the app to access Google services:

```powershell
# Create service account
gcloud iam service-accounts create shakambhari-app --display-name="Shakambhari Invoice App"

# Grant permissions
gcloud projects add-iam-policy-binding shakambhari-invoices `
    --member="serviceAccount:shakambhari-app@shakambhari-invoices.iam.gserviceaccount.com" `
    --role="roles/editor"

# Create and download key file
gcloud iam service-accounts keys create service-account.json `
    --iam-account=shakambhari-app@shakambhari-invoices.iam.gserviceaccount.com
```

**Important:** Save `service-account.json` in the `cloud` folder. Never commit this to Git!

---

## Step 2: Google Sheets Setup

### 2.1 Create the Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Click **"+ Blank"** to create a new spreadsheet
3. Name it: `Shakambhari Invoice Database`
4. Note the **Spreadsheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS-IS-YOUR-SPREADSHEET-ID]/edit
   ```

### 2.2 Share with Service Account

1. Click the **"Share"** button in Google Sheets
2. Add this email (from Step 1.3):
   ```
   shakambhari-app@shakambhari-invoices.iam.gserviceaccount.com
   ```
3. Give it **"Editor"** access
4. Uncheck "Notify people"
5. Click **"Share"**

### 2.3 Initial Sheet Structure

The migration script will create these sheets automatically:
- **Buyers** - Buyer profiles
- **Transport** - Transport modes
- **Invoices** - Invoice records

---

## Step 3: Cloud Storage Setup

### 3.1 Create a Storage Bucket

```powershell
# Create bucket (name must be globally unique)
gsutil mb -l asia-south1 gs://shakambhari-invoices-bucket

# Set permissions
gsutil iam ch serviceAccount:shakambhari-app@shakambhari-invoices.iam.gserviceaccount.com:objectAdmin gs://shakambhari-invoices-bucket
```

**Note:** If the bucket name is taken, try: `shakambhari-invoices-[your-initials]`

---

## Step 4: Migrate Local Data

### 4.1 Install Migration Dependencies

```powershell
cd "C:\Users\KIIT0001\Documents\Bills\Shakambhari Enterprises\cloud"

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate

# Install dependencies
pip install -r requirements.txt
```

### 4.2 Set Environment Variables

```powershell
# Set credentials path
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\KIIT0001\Documents\Bills\Shakambhari Enterprises\cloud\service-account.json"
```

### 4.3 Run Migration Script

```powershell
python migrate_data.py `
    --local-dir "C:\Users\KIIT0001\Documents\Bills\Shakambhari Enterprises" `
    --spreadsheet-id "YOUR_SPREADSHEET_ID_HERE" `
    --bucket-name "shakambhari-invoices-bucket" `
    --credentials "service-account.json"
```

### 4.4 Verify Migration

1. Open your Google Spreadsheet - you should see:
   - Buyers sheet with all your buyer profiles
   - Transport sheet with transport modes
   - Invoices sheet with invoice records

2. Check Cloud Storage:
   ```powershell
   gsutil ls gs://shakambhari-invoices-bucket/
   ```
   You should see folders: `invoices/`, `pdfs/`, `templates/`

---

## Step 5: Deploy the Application

### 5.1 Update Configuration

Edit `app.yaml` with your values:

```yaml
env_variables:
  GOOGLE_CLOUD_PROJECT: "shakambhari-invoices"
  GCS_BUCKET_NAME: "shakambhari-invoices-bucket"
  SPREADSHEET_ID: "YOUR_GOOGLE_SPREADSHEET_ID_HERE"
   FLASK_SECRET_KEY: "GENERATE_A_LONG_RANDOM_SECRET"
   APP_PASSWORD: "SET_A_STRONG_PASSWORD"
```

Security notes:
- `FLASK_SECRET_KEY` should be a long random value (at least 32 characters).
- `APP_PASSWORD` enables a simple login page for app access.
- Do not commit credentials or plaintext secrets to git. Prefer setting these via deploy-time environment variables.

### 5.2 Copy Template Files

Copy these from the original templates folder to the cloud folder:

```powershell
# Create templates folder in cloud
mkdir cloud\templates

# Copy all templates
Copy-Item "templates\*.html" "cloud\templates\"
```

### 5.3 Deploy to Cloud Run (Recommended)

Cloud Run is simpler and cheaper for low traffic:

```powershell
cd cloud

# Validate deployment inputs before release
python preflight_check.py

# Build and deploy
gcloud run deploy shakambhari-invoices `
    --source . `
    --region asia-south1 `
    --platform managed `
    --allow-unauthenticated `
   --set-env-vars="SPREADSHEET_ID=YOUR_SPREADSHEET_ID,GCS_BUCKET_NAME=shakambhari-invoices-bucket,FLASK_SECRET_KEY=YOUR_RANDOM_SECRET,APP_PASSWORD=YOUR_STRONG_PASSWORD"
```

Note: If you keep placeholders in `app.yaml`, the deploy command above will override them using explicit env vars.

### Alternative: Deploy to App Engine

```powershell
cd cloud

# Deploy
gcloud app deploy app.yaml --project shakambhari-invoices
```

---

## Step 6: Access Your Application

### 6.1 Get Your App URL

After deployment, you'll get a URL like:
- **Cloud Run:** `https://shakambhari-invoices-xxxxx-xx.a.run.app`
- **App Engine:** `https://shakambhari-invoices.appspot.com`

### 6.2 Create a Shortcut for Dad

1. **On Phone:**
   - Open Chrome → Go to the URL
   - Tap menu (⋮) → "Add to Home screen"
   - It will appear as an app icon!

2. **On Desktop:**
   - Open Chrome → Go to the URL
   - Ctrl+Shift+B to show bookmarks bar
   - Drag the URL to bookmarks bar

### 6.3 Test the Application

1. Open the URL in a browser
2. Try creating a test invoice
3. Verify PDF download works
4. Check buyer profile management

---

## Cost Estimation

### Google Cloud Free Tier (First Year)

| Service | Free Allowance | Expected Usage | Monthly Cost |
|---------|---------------|----------------|--------------|
| Cloud Run | 2M requests, 360K vCPU-sec | ~1000 requests | **$0** |
| Cloud Storage | 5 GB | ~100 MB | **$0** |
| Sheets API | Unlimited | ~500 calls/month | **$0** |

### After Free Tier

| Service | Rate | Expected Cost |
|---------|------|---------------|
| Cloud Run | $0.00002400/vCPU-sec | ~$1-2/month |
| Cloud Storage | $0.020/GB/month | ~$0.10/month |
| **Total** | | **~$2-3/month** |

---

## Where Your Files Are Stored Online

After deployment and migration, generated files are stored in your Google Cloud Storage bucket:

- Excel invoices: `gs://<your-bucket>/invoices/*.xlsx`
- PDF invoices: `gs://<your-bucket>/pdfs/*.pdf`
- Invoice template: `gs://<your-bucket>/templates/*.xlsx`

How to access them:

1. From the app dashboard (`/dashboard`):
   - Use direct XLSX/PDF download buttons per invoice.
   - Use "Open Bucket", "Open invoices/", "Open pdfs/" buttons to jump to Cloud Console.
2. From Cloud Console:
   - Open Storage Browser and navigate your bucket folders.
3. From terminal:
   - `gsutil ls gs://<your-bucket>/invoices/`
   - `gsutil ls gs://<your-bucket>/pdfs/`

Important:

- Invoice metadata (buyer, invoice number, totals, links) is stored in Google Sheets, not in local JSON.
- File bytes (actual .xlsx/.pdf documents) are stored in Cloud Storage.
- Local `Generated_Invoices` folders are no longer the source of truth after cloud cutover.

---

## Maintenance & Troubleshooting

### Common Issues

#### 1. "Permission Denied" Error
```
Solution: Make sure the service account has access to the Spreadsheet
- Open Google Sheets → Share → Add service account email
```

#### 2. "Bucket Not Found" Error
```
Solution: Check bucket name spelling in environment variables
- gsutil ls (to list your buckets)
```

#### 3. PDF Not Generating
```
Solution: WeasyPrint needs system fonts
- This is handled automatically in the Dockerfile
```

### Viewing Logs

```powershell
# Cloud Run logs
gcloud run services logs read shakambhari-invoices --region asia-south1

# App Engine logs
gcloud app logs tail
```

### Updating the Application

After making changes:

```powershell
# Redeploy
gcloud run deploy shakambhari-invoices --source . --region asia-south1
```

### Backing Up Data

Your data is automatically backed up by Google, but you can export:

```powershell
# Export Google Sheet to Excel
# (Use File → Download → Microsoft Excel in Google Sheets)

# Download all invoices
gsutil -m cp -r gs://shakambhari-invoices-bucket/invoices ./backup/
```

---

## Quick Reference Card

Print this for your dad:

```
╔═══════════════════════════════════════════════════════════╗
║          SHAKAMBHARI INVOICE GENERATOR - QUICK GUIDE       ║
╠═══════════════════════════════════════════════════════════╣
║                                                            ║
║  🌐 Website: https://shakambhari-invoices.appspot.com     ║
║                                                            ║
║  📱 On Phone: Open Chrome → Menu → Add to Home Screen     ║
║                                                            ║
║  ─────────────────────────────────────────────────────    ║
║                                                            ║
║  CREATE INVOICE:                                           ║
║  1. Select buyer from dropdown                             ║
║  2. Enter invoice number and date                          ║
║  3. Add items (description, quantity, rate)                ║
║  4. Click "Generate Invoice"                               ║
║  5. Download PDF or Excel                                  ║
║                                                            ║
║  ─────────────────────────────────────────────────────    ║
║                                                            ║
║  ADD NEW BUYER:                                            ║
║  1. Click "Manage Buyer Profiles"                          ║
║  2. Click "Add New Buyer"                                  ║
║  3. Fill details and save                                  ║
║                                                            ║
║  ─────────────────────────────────────────────────────    ║
║                                                            ║
║  LOAD OLD INVOICE:                                         ║
║  1. Click "Load Old Invoice" button                        ║
║  2. Search or scroll to find invoice                       ║
║  3. Click "Load & Edit" or "Create Duplicate"              ║
║                                                            ║
╚═══════════════════════════════════════════════════════════╝
```

---

## Need Help?

If you encounter issues:

1. Check the logs (see Maintenance section)
2. Verify environment variables are set correctly
3. Ensure service account has proper permissions
4. Check that the Spreadsheet ID is correct

For technical support, refer to:
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

**Last Updated:** December 2024
