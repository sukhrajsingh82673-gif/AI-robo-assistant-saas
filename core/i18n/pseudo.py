"""
Pseudo-Localization Generator for UI String Expansion Verification (Rule 70 & Rule 73)
Replaces ASCII characters with accented variants and expands string length by ~30%
to test for UI clipping, truncation, and hardcoded untranslated strings.
"""

# Glyph replacement map
PSEUDO_GLYPH_MAP = {
    'a': 'å', 'b': 'ƀ', 'c': 'ç', 'd': 'ð', 'e': 'é', 'f': 'ƒ', 'g': 'ĝ',
    'h': 'ĥ', 'i': 'î', 'j': 'ĵ', 'k': 'ķ', 'l': 'ļ', 'm': 'ɱ', 'n': 'ñ',
    'o': 'ö', 'p': 'þ', 'q': 'ǫ', 'r': 'ř', 's': 'š', 't': 'ţ', 'u': 'û',
    'v': 'ṽ', 'w': 'ŵ', 'x': 'ẋ', 'y': 'ý', 'z': 'ž',
    'A': 'Å', 'B': 'Ɓ', 'C': 'Ç', 'D': 'Ð', 'E': 'É', 'F': 'Ƒ', 'G': 'Ĝ',
    'H': 'Ĥ', 'I': 'Î', 'J': 'Ĵ', 'K': 'Ķ', 'L': 'Ļ', 'M': 'Ṁ', 'N': 'Ñ',
    'O': 'Ö', 'P': 'Þ', 'Q': 'Ǫ', 'R': 'Ř', 'S': 'Š', 'T': 'Ţ', 'U': 'Û',
    'V': 'Ṽ', 'W': 'Ŵ', 'X': 'Ẋ', 'Y': 'Ý', 'Z': 'Ž'
}


class PseudoLocalizer:
    """Transforms strings into pseudo-localized variants."""

    @classmethod
    def transform(cls, text: str, expand: bool = True) -> str:
        """
        Transforms text with pseudo-accented glyphs and expansions.
        e.g., 'Save' -> '[!!! Šåṽé ~~~ !!!]'
        """
        if not text:
            return text

        transformed_chars = [PSEUDO_GLYPH_MAP.get(c, c) for c in text]
        transformed_text = "".join(transformed_chars)

        if expand:
            # Add ~30% expansion padding
            pad_len = max(3, int(len(text) * 0.3))
            padding = " ~" * (pad_len // 2)
            return f"[!!! {transformed_text}{padding} !!!]"
        else:
            return f"[! {transformed_text} !]"
