"""Central configuration and path utilities for the Shakambhari Invoice app.

All paths are derived relative to the location of this file so the entire
folder can be copied anywhere (e.g. a USB drive) and still work without
editing hard‑coded absolute paths.
"""
from __future__ import annotations

import os
from typing import Optional

# Base directory of the project (folder containing app.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data files (JSON) live alongside the code by default
BUYER_PROFILES_JSON = os.path.join(BASE_DIR, "buyer_profiles.json")
TRANSPORT_MODES_JSON = os.path.join(BASE_DIR, "transport_modes.json")

# Output folders
OUTPUT_DIR = os.path.join(BASE_DIR, "Generated_Invoices")
PDF_OUTPUT_DIR = os.path.join(BASE_DIR, "Generated_Invoices_PDF")

# Directory where invoice templates (.xlsx) are kept
TEMPLATE_DIR = os.path.join(BASE_DIR, "GST Invoices")

def _discover_template_file() -> Optional[str]:
    """Return a reasonable default Excel template path.

    Strategy:
    1. If env var TEMPLATE_FILE is set and exists -> use that.
    2. Look inside TEMPLATE_DIR for the newest *.xlsx file whose name contains
       'bill' (case‑insensitive) and is not a temporary Office file.
    3. Fallback to the first *.xlsx file if any exist.
    4. None if no template found (caller handles error message).
    """
    env_path = os.environ.get("TEMPLATE_FILE")
    if env_path and os.path.isfile(env_path):
        return env_path
    if not os.path.isdir(TEMPLATE_DIR):
        return None
    candidates = []
    for fname in os.listdir(TEMPLATE_DIR):
        if not fname.lower().endswith(".xlsx"):
            continue
        if fname.startswith("~$"):  # Skip temporary lock files
            continue
        full = os.path.join(TEMPLATE_DIR, fname)
        candidates.append(full)
    if not candidates:
        return None
    # Prefer files containing 'bill'
    bill_files = [c for c in candidates if 'bill' in os.path.basename(c).lower()]
    search_pool = bill_files or candidates
    # Pick the most recently modified
    search_pool.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return search_pool[0]

TEMPLATE_EXCEL_FILE = _discover_template_file()

def ensure_dirs():
    """Create output directories if they do not exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

__all__ = [
    "BASE_DIR",
    "BUYER_PROFILES_JSON",
    "TRANSPORT_MODES_JSON",
    "OUTPUT_DIR",
    "PDF_OUTPUT_DIR",
    "TEMPLATE_DIR",
    "TEMPLATE_EXCEL_FILE",
    "ensure_dirs",
]
