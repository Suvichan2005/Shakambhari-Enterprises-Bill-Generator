"""Pre-deployment checks for the cloud invoice app.

Run from repo root or cloud folder:
    python cloud/preflight_check.py
"""

from __future__ import annotations

import os
import re
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = [
    ROOT / "app_cloud.py",
    ROOT / "app.yaml",
    ROOT / "requirements.txt",
    ROOT / "templates" / "index.html",
    ROOT / "templates" / "success.html",
    ROOT / "templates" / "login.html",
    ROOT / "templates" / "error.html",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_files() -> list[str]:
    issues = []
    for file_path in REQUIRED_FILES:
        if not file_path.exists():
            issues.append(f"Missing required file: {file_path}")
    return issues


def check_app_yaml(strict_placeholders: bool) -> tuple[list[str], list[str]]:
    issues = []
    warnings = []
    app_yaml = ROOT / "app.yaml"
    if not app_yaml.exists():
        return ["cloud/app.yaml not found"], warnings

    content = read_text(app_yaml)
    required_keys = [
        "GOOGLE_CLOUD_PROJECT",
        "GCS_BUCKET_NAME",
        "SPREADSHEET_ID",
        "FLASK_SECRET_KEY",
        "APP_PASSWORD",
    ]
    for key in required_keys:
        if key not in content:
            issues.append(f"app.yaml missing env key: {key}")

    placeholder_patterns = [
        r"CHANGE_ME_TO_A_LONG_RANDOM_SECRET",
        r"CHANGE_ME_TO_A_STRONG_PASSWORD",
        r"YOUR_GOOGLE_SPREADSHEET_ID_HERE",
    ]
    for pat in placeholder_patterns:
        if re.search(pat, content):
            msg = f"app.yaml still has placeholder value matching: {pat}"
            if strict_placeholders:
                issues.append(msg)
            else:
                warnings.append(msg)

    return issues, warnings


def check_ignore_rules() -> list[str]:
    issues = []
    gitignore = ROOT.parent / ".gitignore"
    if not gitignore.exists():
        return ["Root .gitignore not found"]

    content = read_text(gitignore)
    required_lines = [
        "cloud/service-account.json",
        "logs/",
        "_backups/",
        ".env",
    ]
    for line in required_lines:
        if line not in content:
            issues.append(f".gitignore missing rule: {line}")

    return issues


def check_gcs_template() -> list[str]:
    issues = []
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket_name = 'shakambhari-invoices-bucket'
        
        if not bucket_name or bucket_name == 'YOUR_BUCKET_NAME_HERE':
            return ["Could not determine GCS_BUCKET_NAME or it is a placeholder. Skipping template verification."]
            
        bucket = client.bucket(bucket_name)
        blob = bucket.blob("templates/invoice_template_2026_27.xlsx")
        
        if not blob.exists():
            issues.append(f"CRITICAL: Missing canonical template in GCS at gs://{bucket_name}/templates/invoice_template_2026_27.xlsx")
            issues.append("Please upload cloud/invoice_template_2026_27.xlsx to GCS before deploying.")
    except ImportError:
        return ["google-cloud-storage not installed, skipping GCS template verification."]
    except Exception as e:
        return [f"Failed to check GCS for template: {e}"]
        
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cloud pre-deployment checks")
    parser.add_argument(
        "--strict-placeholders",
        action="store_true",
        help="Fail if app.yaml still contains placeholder values",
    )
    args = parser.parse_args()

    all_issues: list[str] = []
    all_warnings: list[str] = []
    all_issues.extend(check_files())
    app_yaml_issues, app_yaml_warnings = check_app_yaml(strict_placeholders=args.strict_placeholders)
    all_issues.extend(app_yaml_issues)
    all_warnings.extend(app_yaml_warnings)
    all_issues.extend(check_ignore_rules())
    all_issues.extend(check_gcs_template())

    if all_issues:
        print("Preflight FAILED with the following issues:\n")
        for idx, issue in enumerate(all_issues, start=1):
            print(f"{idx}. {issue}")
        print("\nFix these and rerun: python cloud/preflight_check.py")
        return 1

    if all_warnings:
        print("Preflight PASSED with warnings:\n")
        for idx, warning in enumerate(all_warnings, start=1):
            print(f"{idx}. {warning}")
        print("\nYou can still deploy if you pass real env vars in the deploy command.")
        return 0

    print("Preflight PASSED. Cloud deployment checks look good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
