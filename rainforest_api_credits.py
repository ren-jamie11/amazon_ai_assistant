from datetime import datetime
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

MONTHLY_RAINFOREST_API_LIMIT = 100
WORKSHEET_NAME = "credits"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _current_period() -> str:
    """Returns current period as 'YYYY-MM'."""
    return datetime.now().strftime("%Y-%m")


@st.cache_resource
def _get_worksheet():
    """Returns the 'credits' worksheet. Cached across reruns for the session."""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open(st.secrets["sheet"]["name"])

    # Get-or-create the credits worksheet
    try:
        ws = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=WORKSHEET_NAME, rows=100, cols=3)
        ws.update("A1:C1", [["username", "credits_remaining", "period"]])
    return ws


def _find_row_index(username: str):
    """Returns the 1-indexed row number for the user, or None if not found."""
    ws = _get_worksheet()
    try:
        cell = ws.find(username, in_column=1)
        return cell.row if cell else None
    except gspread.exceptions.CellNotFound:
        return None


def get_credits(username: str) -> int:
    """
    Returns credits remaining for the user. If the stored period is stale
    (different month), resets to MONTHLY_RAINFOREST_API_LIMIT and persists.
    If the user is missing from the sheet, adds them with full credits.
    """
    ws = _get_worksheet()
    current = _current_period()
    row_idx = _find_row_index(username)

    if row_idx is None:
        # User missing — append a row with full credits
        ws.append_row([username, MONTHLY_RAINFOREST_API_LIMIT, current])
        return MONTHLY_RAINFOREST_API_LIMIT

    # Read this user's row (columns B and C)
    row_values = ws.row_values(row_idx)
    try:
        stored_credits = int(row_values[1])
    except (IndexError, ValueError):
        stored_credits = 0
    stored_period = row_values[2] if len(row_values) > 2 else ""

    if stored_period != current:
        # New month — reset
        ws.update(f"B{row_idx}:C{row_idx}", [[MONTHLY_RAINFOREST_API_LIMIT, current]])
        return MONTHLY_RAINFOREST_API_LIMIT

    return stored_credits


def deduct_credits(username: str, amount: int) -> int:
    """
    Deduct `amount` credits from user. Returns new balance.
    Does not enforce non-negative — caller should check first via get_credits().
    """
    ws = _get_worksheet()
    current = _current_period()
    row_idx = _find_row_index(username)

    if row_idx is None:
        # Shouldn't happen if get_credits was called first, but handle defensively
        new_balance = max(0, MONTHLY_RAINFOREST_API_LIMIT - amount)
        ws.append_row([username, new_balance, current])
        return new_balance

    row_values = ws.row_values(row_idx)
    try:
        stored_credits = int(row_values[1])
    except (IndexError, ValueError):
        stored_credits = 0
    stored_period = row_values[2] if len(row_values) > 2 else ""

    # Handle period rollover defensively in case the month changed between calls
    if stored_period != current:
        stored_credits = MONTHLY_RAINFOREST_API_LIMIT

    new_balance = stored_credits - amount
    ws.update(f"B{row_idx}:C{row_idx}", [[new_balance, current]])
    return new_balance