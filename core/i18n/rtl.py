"""
Right-to-Left (RTL) Layout and Bi-directional Text Support (Rule 70 & Rule 73)
Supports Arabic, Hebrew, Persian, Urdu, and Yiddish text directions and layout metadata.
"""

from typing import Dict, Any

RTL_LANGUAGES = {"ar", "he", "fa", "ur", "yi", "ps", "ug", "sd"}

# Unicode Bidirectional Controls
LRM = "\u200e"  # Left-to-Right Mark
RLM = "\u200f"  # Right-to-Left Mark
LRE = "\u202a"  # Left-to-Right Embedding
RLE = "\u202b"  # Right-to-Left Embedding
PDF = "\u202c"  # Pop Directional Formatting
LRO = "\u202d"  # Left-to-Right Override
RLO = "\u202e"  # Right-to-Left Override


class RTLEngine:
    """RTL detection and layout direction coordinator."""

    @staticmethod
    def is_rtl(locale_or_lang: str) -> bool:
        """Determines if the given locale or ISO-639 language code requires RTL layout."""
        if not locale_or_lang:
            return False
        clean = locale_or_lang.lower().replace("-", "_")
        lang = clean.split("_")[0]
        return lang in RTL_LANGUAGES

    @classmethod
    def get_layout_metadata(cls, locale_or_lang: str) -> Dict[str, Any]:
        """Returns layout direction, alignment, and mirroring properties for UI components."""
        rtl = cls.is_rtl(locale_or_lang)
        return {
            "direction": "rtl" if rtl else "ltr",
            "start_align": "right" if rtl else "left",
            "end_align": "left" if rtl else "right",
            "mirror_icons": rtl,
            "html_dir": "rtl" if rtl else "ltr",
        }

    @classmethod
    def wrap_bidi(cls, text: str, is_rtl: bool) -> str:
        """Wraps text in explicit directional marks to prevent layout corruption."""
        mark = RLM if is_rtl else LRM
        return f"{mark}{text}{mark}"
