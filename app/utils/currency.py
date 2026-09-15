from flask import current_app


def format_currency(value):
    """Format a number as CFA currency, e.g. 1234567 -> '1,234,567 CFA'."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0
    symbol = current_app.config.get("CURRENCY_SYMBOL", "CFA")
    return f"{value:,.0f} {symbol}"
