import os
import json
from datetime import datetime
from flask import flash
from config import BASE_DIR

BACKUP_DIR = os.path.join(BASE_DIR, "_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_json(path: str):
    """Creates a timestamped backup of a JSON file."""
    if not os.path.isfile(path):
        return
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"{os.path.basename(path)}.{stamp}.bak")
        with open(path, 'rb') as src, open(backup_file, 'wb') as dst:
            dst.write(src.read())
    except Exception as e:
        print(f"WARNING: Backup failed for {path}: {e}")

def load_data(json_path):
    """Loads data from a JSON file."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        flash(f"Error decoding JSON from {json_path}. Please check its format.", "error")
        return []

def save_data(json_path, data):
    """Saves data to a JSON file after creating a backup."""
    try:
        backup_json(json_path)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except IOError as e:
        flash(f"Error saving data to {json_path}: {e}", "error")
        return False
