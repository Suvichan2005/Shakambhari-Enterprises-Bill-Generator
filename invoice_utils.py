import os
from datetime import datetime
from data_manager import load_data, save_data
from config import BASE_DIR

APP_STATE_JSON = os.path.join(BASE_DIR, "app_state.json")

def _financial_year_suffix(today: datetime | None = None) -> str:
    """Generates the financial year suffix (e.g., /2025-26)."""
    today = today or datetime.now()
    year = today.year
    if today.month >= 4:  # Financial year starts in April
        start = year
        end = year + 1
    else:
        start = year - 1
        end = year
    return f"/{start}-{str(end)[-2:]}"

def get_next_invoice_number() -> str:
    """
    Gets the next invoice number by incrementing a stored counter.
    Returns the full invoice number string (e.g., 001/2025-26).
    """
    state = load_data(APP_STATE_JSON)
    if not isinstance(state, dict): # Handle empty or malformed file
        state = {'last_invoice_number': 0}

    last_num = state.get("last_invoice_number", 0)
    next_num = last_num + 1

    # The saving of the new number should happen only when the invoice is *generated*,
    # not when it's just suggested. So we'll have a separate function for that.

    return f"{next_num:03d}{_financial_year_suffix()}"

def update_last_invoice_number(invoice_number_str: str):
    """
    Updates the last used invoice number from a full invoice string.
    e.g., "001/2025-26" -> saves 1.
    """
    try:
        # Extract the numeric part of the invoice number
        numeric_part = int(invoice_number_str.split('/')[0])
        state = {"last_invoice_number": numeric_part}
        save_data(APP_STATE_JSON, state)
    except (ValueError, IndexError):
        print(f"Warning: Could not parse invoice number '{invoice_number_str}' to update the counter.")
