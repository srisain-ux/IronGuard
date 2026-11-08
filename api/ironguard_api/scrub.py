"""Conservative demo scrubber. Never persists input or sends it to a model."""

import re

from .directory import load_directory

NAMES = ("Anna", "Alice", "Bob", "John", "Jane", "Sarah", "David", "Michael", "Mary")


def scrub(text: str) -> str:
    """Mask known patterns and demo names/brands; not general PII recognition."""
    brands = [
        name for entry in load_directory()["brands"] for name in [entry["brand"], *entry["aliases"]]
    ]
    patterns = [
        (r"[\w.+-]+@[\w.-]+\.[^\W\d_]{2,}", "[EMAIL]"),
        (r"(?<!\w)@[\w.-]+", "[NAME]"),
        (r"(?:https?://|www\.)[^\s<>]+|\b(?:[\w-]+\.)+[^\W\d_]{2,}(?:/[^\s<>]*)?", "[URL]"),
        (r"(?:[$€£]\s*\d[\d,.]*|\b\d[\d,.]*\s*(?:USD|dollars|EUR)\b)", "[AMOUNT]"),
        (r"(?<!\w)\+?\d[\d ().-]{5,}\d(?!\w)", "[PHONE]"),
        (r"\b(?:" + "|".join(map(re.escape, NAMES)) + r")\b", "[NAME]"),
        (
            r"(?<!\w)(?:"
            + "|".join(map(re.escape, sorted(brands, key=len, reverse=True)))
            + r")(?!\w)",
            "[BRAND]",
        ),
    ]
    for pattern, placeholder in patterns:
        text = re.sub(pattern, placeholder, text, flags=re.IGNORECASE)
    return text
