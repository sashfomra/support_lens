"""
PII Masking — Two-layer approach:
  Layer 1: Regex (emails, phones, credit cards, order IDs, IPs)
  Layer 2: spaCy NER (names, organisations, locations)
"""
import re
from typing import Tuple, Dict

# Try spaCy, fall back gracefully
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except Exception:
    _nlp = None
    SPACY_AVAILABLE = False


# ── Regex patterns ────────────────────────────────────────────────────────────
_PATTERNS: Dict[str, Tuple[str, str]] = {
    "EMAIL":    (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
    "PHONE":    (r"(\+?\d[\d\s\-().]{7,}\d)", "[PHONE]"),
    "CARD":     (r"\b(?:\d[ \-]?){13,16}\b", "[CARD_NUMBER]"),
    "ORDER_ID": (r"\b(?:ORD|INV|TKT|REF)[-\s]?\d{4,12}\b", "[ORDER_ID]"),
    "IP":       (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_ADDRESS]"),
    "SSN":      (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
}


def _regex_mask(text: str) -> Tuple[str, list]:
    """Apply regex PII rules. Returns masked text + list of found PII types."""
    found = []
    for pii_type, (pattern, replacement) in _PATTERNS.items():
        new_text, count = re.subn(pattern, replacement, text, flags=re.IGNORECASE)
        if count > 0:
            found.append(pii_type)
            text = new_text
    return text, found


def _spacy_mask(text: str) -> Tuple[str, list]:
    """Apply spaCy NER to mask names, orgs, locations."""
    if not SPACY_AVAILABLE or _nlp is None:
        return text, []

    found = []
    doc = _nlp(text)
    replacements = []

    for ent in reversed(doc.ents):  # reversed to not shift indices
        if ent.label_ in ("PERSON",):
            replacements.append((ent.start_char, ent.end_char, "[CUSTOMER_NAME]"))
            found.append("PERSON")
        elif ent.label_ in ("ORG",):
            replacements.append((ent.start_char, ent.end_char, "[ORGANIZATION]"))
            found.append("ORG")
        elif ent.label_ in ("GPE", "LOC"):
            replacements.append((ent.start_char, ent.end_char, "[LOCATION]"))
            found.append("LOCATION")

    result = text
    for start, end, repl in sorted(replacements, key=lambda x: x[0], reverse=True):
        result = result[:start] + repl + result[end:]

    return result, list(set(found))


def mask_pii(text: str) -> Tuple[str, list]:
    """
    Full two-layer PII masking.
    Returns (masked_text, list_of_pii_types_found)
    """
    text, regex_found = _regex_mask(text)
    text, ner_found = _spacy_mask(text)
    return text, list(set(regex_found + ner_found))


def extract_customer_info(text: str) -> Dict[str, str]:
    """
    Extract PII for storage (separate from the masked version sent to SLM).
    Returns dict with any found PII.
    """
    info = {}
    email_match = re.search(_PATTERNS["EMAIL"][0], text, re.IGNORECASE)
    if email_match:
        info["email"] = email_match.group(0)
    phone_match = re.search(_PATTERNS["PHONE"][0], text)
    if phone_match:
        info["phone"] = phone_match.group(0)
    order_match = re.search(_PATTERNS["ORDER_ID"][0], text, re.IGNORECASE)
    if order_match:
        info["order_id"] = order_match.group(0)
    return info
