"""
ZONATA Sovereign Financial Ledger — ISO 4217 Currency Definitions & Minor Unit Specifications
Strict adherence to Rule 12: Integer minor units only. Zero float arithmetic.
"""

from typing import Dict, Optional, Set

# Standard ISO 4217 Currency Codes mapped to decimal places for minor units
# (e.g., 2 decimals = cents/pence/paise; 0 decimals = yen/krw; 3 decimals = dinars)
ISO_4217_CURRENCY_DECIMALS: Dict[str, int] = {
    "USD": 2,  # US Dollar (cent)
    "EUR": 2,  # Euro (cent)
    "GBP": 2,  # British Pound (penny)
    "INR": 2,  # Indian Rupee (paisa)
    "JPY": 0,  # Japanese Yen (yen has no minor unit)
    "CAD": 2,  # Canadian Dollar (cent)
    "AUD": 2,  # Australian Dollar (cent)
    "CHF": 2,  # Swiss Franc (rappen)
    "CNY": 2,  # Chinese Yuan (fen)
    "SGD": 2,  # Singapore Dollar (cent)
    "HKD": 2,  # Hong Kong Dollar (cent)
    "NZD": 2,  # New Zealand Dollar (cent)
    "SEK": 2,  # Swedish Krona (öre)
    "NOK": 2,  # Norwegian Krone (øre)
    "DKK": 2,  # Danish Krone (øre)
    "BRL": 2,  # Brazilian Real (centavo)
    "MXN": 2,  # Mexican Peso (centavo)
    "ZAR": 2,  # South African Rand (cent)
    "AED": 2,  # UAE Dirham (fils)
    "SAR": 2,  # Saudi Riyal (halala)
    "BHD": 3,  # Bahraini Dinar (fils)
    "KWD": 3,  # Kuwaiti Dinar (fils)
    "OMR": 3,  # Omani Rial (baisa)
    "QAR": 2,  # Qatari Rial (dirham)
    "KRW": 0,  # South Korean Won (jeon not in practical use)
}

SUPPORTED_CURRENCIES: Set[str] = set(ISO_4217_CURRENCY_DECIMALS.keys())


class InvalidCurrencyError(ValueError):
    """Raised when an invalid or unsupported ISO 4217 currency code is provided."""
    pass


def validate_currency(currency_code: str) -> str:
    """Validates that a currency code is a 3-character uppercase ISO 4217 code.
    
    Returns the normalized uppercase code or raises InvalidCurrencyError.
    """
    if not isinstance(currency_code, str):
        raise InvalidCurrencyError(f"Currency code must be a string, got {type(currency_code).__name__}")
    normalized = currency_code.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise InvalidCurrencyError(f"Invalid currency code format '{currency_code}': must be 3-letter ISO 4217")
    if normalized not in SUPPORTED_CURRENCIES:
        raise InvalidCurrencyError(f"Unsupported ISO 4217 currency code '{normalized}'")
    return normalized


def format_minor_units(amount_minor: int, currency_code: str) -> str:
    """Formats an integer minor unit amount into a human-readable string without float arithmetic.
    
    Examples:
        format_minor_units(1050, 'USD') -> 'USD 10.50'
        format_minor_units(-500, 'USD') -> '-USD 5.00'
        format_minor_units(500, 'JPY')  -> 'JPY 500'
    """
    code = validate_currency(currency_code)
    decimals = ISO_4217_CURRENCY_DECIMALS[code]
    is_negative = amount_minor < 0
    abs_amt = abs(amount_minor)

    if decimals == 0:
        val_str = str(abs_amt)
    else:
        s = str(abs_amt).zfill(decimals + 1)
        integer_part = s[:-decimals]
        fractional_part = s[-decimals:]
        val_str = f"{integer_part}.{fractional_part}"

    sign = "-" if is_negative else ""
    return f"{sign}{code} {val_str}"
