"""
CLDR-Compliant Internationalization Formatting Engine (Rule 70 & Rule 73)
Provides locale-sensitive formatting for numbers, currencies, and dates based on Unicode CLDR standards.
"""

from typing import Union, Optional, Dict, Any
import datetime
import math


# CLDR currency decimal digits (ISO 4217)
CURRENCY_DIGITS = {
    "JPY": 0, "KRW": 0, "VND": 0, "CLP": 0, "UGX": 0, "RWF": 0,
    "BHD": 3, "KWD": 3, "OMR": 3, "JOD": 3, "TND": 3, "IQD": 3, "LYD": 3,
    # Standard 2 digits for EUR, USD, GBP, INR, CAD, AUD, CHF, CNY, etc.
}

# CLDR locale formatting rules
LOCALE_SPECS = {
    "en_US": {
        "decimal": ".",
        "group": ",",
        "indian_grouping": False,
        "currency_prefix": True,
        "currency_space": False,
        "date_short": "%m/%d/%Y",
        "date_medium": "%b %d, %Y",
        "symbols": {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
    },
    "en_GB": {
        "decimal": ".",
        "group": ",",
        "indian_grouping": False,
        "currency_prefix": True,
        "currency_space": False,
        "date_short": "%d/%m/%Y",
        "date_medium": "%d %b %Y",
        "symbols": {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
    },
    "de_DE": {
        "decimal": ",",
        "group": ".",
        "indian_grouping": False,
        "currency_prefix": False,
        "currency_space": True,
        "date_short": "%d.%m.%Y",
        "date_medium": "%d. %b %Y",
        "symbols": {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
    },
    "fr_FR": {
        "decimal": ",",
        "group": "\u202f",  # narrow non-breaking space
        "indian_grouping": False,
        "currency_prefix": False,
        "currency_space": True,
        "date_short": "%d/%m/%Y",
        "date_medium": "%d %b %Y",
        "symbols": {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
    },
    "hi_IN": {
        "decimal": ".",
        "group": ",",
        "indian_grouping": True,
        "currency_prefix": True,
        "currency_space": True,
        "date_short": "%d/%m/%Y",
        "date_medium": "%d %b %Y",
        "symbols": {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
    },
    "ja_JP": {
        "decimal": ".",
        "group": ",",
        "indian_grouping": False,
        "currency_prefix": True,
        "currency_space": False,
        "date_short": "%Y/%m/%d",
        "date_medium": "%Y年%m月%d日",
        "symbols": {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "JPY": "¥"}
    },
    "ar_SA": {
        "decimal": "٫",
        "group": "٬",
        "indian_grouping": False,
        "currency_prefix": False,
        "currency_space": True,
        "date_short": "%d/%m/%Y",
        "date_medium": "%d %b %Y",
        "symbols": {"USD": "USD", "EUR": "EUR", "SAR": "ر.س", "INR": "INR"}
    },
}


class CLDREngine:
    """CLDR formatting engine for enterprise presentation layer."""

    @staticmethod
    def _normalize_locale(locale: str) -> str:
        loc = locale.replace("-", "_")
        if loc in LOCALE_SPECS:
            return loc
        prefix = loc.split("_")[0]
        for key in LOCALE_SPECS:
            if key.startswith(prefix + "_"):
                return key
        return "en_US"

    @classmethod
    def format_number(cls, value: Union[int, float], locale: str = "en_US", decimal_places: int = 2) -> str:
        """Formats a number according to the target CLDR locale."""
        norm_locale = cls._normalize_locale(locale)
        spec = LOCALE_SPECS[norm_locale]

        is_negative = value < 0
        abs_val = abs(value)

        int_part = int(math.floor(abs_val))
        dec_part = round(abs_val - int_part, decimal_places)
        dec_str = f"{dec_part:.{decimal_places}f}"[2:] if decimal_places > 0 else ""

        int_str = str(int_part)
        if spec["indian_grouping"]:
            # Indian numbering system: last 3 digits, then groups of 2
            if len(int_str) > 3:
                last_three = int_str[-3:]
                remaining = int_str[:-3]
                groups = []
                while len(remaining) > 2:
                    groups.insert(0, remaining[-2:])
                    remaining = remaining[:-2]
                if remaining:
                    groups.insert(0, remaining)
                groups.append(last_three)
                formatted_int = spec["group"].join(groups)
            else:
                formatted_int = int_str
        else:
            # Standard grouping by 3
            groups = []
            while len(int_str) > 3:
                groups.insert(0, int_str[-3:])
                int_str = int_str[:-3]
            if int_str:
                groups.insert(0, int_str)
            formatted_int = spec["group"].join(groups)

        formatted_num = formatted_int
        if decimal_places > 0 and dec_str:
            formatted_num = f"{formatted_int}{spec['decimal']}{dec_str}"

        prefix = "-" if is_negative else ""
        return f"{prefix}{formatted_num}"

    @classmethod
    def format_currency(
        cls,
        amount_minor: int,
        currency: str,
        locale: str = "en_US",
        use_symbol: bool = True
    ) -> str:
        """
        Formats integer minor units into locale-sensitive currency string.
        (e.g., 100050 minor EUR in de_DE -> '1.000,50 €')
        """
        norm_locale = cls._normalize_locale(locale)
        spec = LOCALE_SPECS[norm_locale]
        curr_upper = currency.upper()

        decimals = CURRENCY_DIGITS.get(curr_upper, 2)
        major_value = amount_minor / (10 ** decimals) if decimals > 0 else float(amount_minor)

        num_str = cls.format_number(major_value, locale=norm_locale, decimal_places=decimals)
        symbol = spec["symbols"].get(curr_upper, curr_upper) if use_symbol else curr_upper

        if spec["currency_prefix"]:
            space = " " if spec["currency_space"] else ""
            return f"{symbol}{space}{num_str}"
        else:
            space = " " if spec["currency_space"] else ""
            return f"{num_str}{space}{symbol}"

    @classmethod
    def format_date(cls, dt: Union[datetime.date, datetime.datetime, str], locale: str = "en_US", format_type: str = "short") -> str:
        """Formats a date or datetime according to locale conventions."""
        if isinstance(dt, str):
            dt = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00")).date()
        elif isinstance(dt, datetime.datetime):
            dt = dt.date()

        norm_locale = cls._normalize_locale(locale)
        spec = LOCALE_SPECS[norm_locale]
        fmt = spec["date_short"] if format_type == "short" else spec["date_medium"]
        return dt.strftime(fmt)
