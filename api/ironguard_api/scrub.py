"""Conservative demo scrubber. Never persists input or sends it to a model."""

import re

NAMES = ("Anna", "Alice", "Bob", "John", "Jane", "Sarah", "David", "Michael", "Mary")
BRANDS = ("PNC", "T-Mobile", "Chase", "Wells Fargo", "Bank of America", "UTD")


def scrub(text: str) -> str:
    patterns = [
        (r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]"),
        (r"(?:https?://|www\.)[^\s<>]+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s<>]*)?", "[URL]"),
        (r"(?:[$€£]\s*\d[\d,.]*|\b\d[\d,.]*\s*(?:USD|dollars|EUR)\b)", "[AMOUNT]"),
        (r"(?<!\w)\+?\d[\d ().-]{5,}\d(?!\w)", "[PHONE]"),
        (r"(?<!\w)@[\w.]+", "[NAME]"),
        (r"\b(?:" + "|".join(map(re.escape, NAMES)) + r")\b", "[NAME]"),
        (r"\b(?:" + "|".join(map(re.escape, BRANDS)) + r")\b", "[BRAND]"),
    ]
    for pattern, placeholder in patterns:
        text = re.sub(pattern, placeholder, text, flags=re.IGNORECASE)
    return text
