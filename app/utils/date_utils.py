from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Tuple, Union


def parse_date_string(date_str: Union[str, date]) -> Tuple[Optional[date], Optional[str]]:
    """
    Parses a date string supporting both 'DD/MM/YYYY' and 'DD.MM.YYYY' notation.
    Validates calendar accuracy (e.g. rejects 31/11/2001 or leap year invalidity)
    and checks that the date is not in the future.

    Returns:
        (date_object, None) on success.
        (None, error_message) on failure.
    """
    if isinstance(date_str, date):
        if date_str > date.today():
            return None, "Date of birth cannot be in the future."
        return date_str, None

    if not date_str or not isinstance(date_str, str):
        return None, "Date of birth is required."

    cleaned = date_str.strip()
    if not cleaned:
        return None, "Date of birth cannot be empty."

    # Normalize dot separator to slash
    normalized = cleaned.replace(".", "/")
    parts = normalized.split("/")

    if len(parts) != 3:
        return None, "Date of birth must be in DD/MM/YYYY or DD.MM.YYYY format."

    day_s, month_s, year_s = parts

    if not (day_s.isdigit() and month_s.isdigit() and year_s.isdigit()):
        return None, "Date of birth must contain only numeric day, month, and year values."

    day = int(day_s)
    month = int(month_s)
    year = int(year_s)

    if year < 1900:
        return None, "Year of birth must be 1900 or later."

    try:
        parsed_date = datetime.strptime(f"{day:02d}/{month:02d}/{year:04d}", "%d/%m/%Y").date()
    except ValueError:
        # Specific friendly message for calendar impossibility
        return None, f"Invalid calendar date '{cleaned}'. Please check the day, month, or leap year."

    if parsed_date > date.today():
        return None, f"Date of birth cannot be in the future (supplied date: {format_date_display(parsed_date)})."

    return parsed_date, None


def format_date_display(d: Optional[Union[date, datetime, str]]) -> str:
    """Formats a date object or ISO string to standard DD/MM/YYYY display format."""
    if d is None:
        return ""
    if isinstance(d, str):
        # If it's already an ISO string like YYYY-MM-DD
        try:
            d_obj = datetime.strptime(d[:10], "%Y-%m-%d").date()
            return d_obj.strftime("%d/%m/%Y")
        except ValueError:
            return d
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    return str(d)
