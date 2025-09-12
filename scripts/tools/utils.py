"""
Utility functions for OCR and text processing
"""

import re
from PIL import Image
from typing import List, Optional


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from image using OCR

    Args:
        image_path: Path to the image file

    Returns:
        str: Extracted text from the image
    """
    try:
        # Open and preprocess image for better OCR
        img = Image.open(image_path)

        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Extract text using pytesseract
        text = pytesseract.image_to_string(img, lang="eng")
        return text
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""


def clean_text_line(line: str) -> str:
    """
    Clean a single line of OCR text

    Args:
        line: Raw OCR text line

    Returns:
        str: Cleaned text line
    """
    # Remove extra whitespace
    cleaned = re.sub(r"\s+", " ", line.strip())
    return cleaned


def find_anchor_line(
    lines: List[str], anchor_text: str, case_sensitive: bool = False
) -> Optional[int]:
    """
    Find the line index containing the anchor text

    Args:
        lines: List of text lines to search
        anchor_text: Text to search for
        case_sensitive: Whether to match case exactly

    Returns:
        int: Index of the line containing anchor text, or None if not found
    """
    search_text = anchor_text if case_sensitive else anchor_text.lower()

    for i, line in enumerate(lines):
        line_text = line if case_sensitive else line.lower()
        if search_text in line_text:
            return i

    return None


def is_capitalized_name_line(line: str) -> bool:
    """
    Check if a line contains capitalized names (likely recipient info)

    Args:
        line: Text line to check

    Returns:
        bool: True if line contains capitalized names or potential business names
    """
    line = line.strip()

    # Skip empty lines
    if not line:
        return False

    # Skip lines that are just numbers, account numbers, or codes
    number_only_pattern = r"^[\d\-\s]+$"
    if re.match(number_only_pattern, line):
        return False

    account_pattern = r"^\d{3}-.*-\d{3,4}$"
    if re.match(account_pattern, line):
        return False

    # Check for capitalized words (names)
    capitalized_words = re.findall(r"\b[A-Z][A-Z]+\b", line)

    # Also check for potential business names (even if lowercase)
    business_patterns = [
        r"\b\w+\s+station\b",  # "lap station", "gas station", etc.
        r"\b\w+\s+center\b",  # "service center", etc.
        r"\b\w+\s+shop\b",  # "coffee shop", etc.
        r"\b\w+\s+store\b",  # "convenience store", etc.
    ]

    has_business_pattern = any(
        re.search(pattern, line, re.IGNORECASE) for pattern in business_patterns
    )

    # Must have either capitalized words or business patterns
    if not capitalized_words and not has_business_pattern:
        return False

    # Filter out common non-name capitalized words
    excluded_words = {
        "THB",
        "USD",
        "EUR",
        "GBP",
        "ID",
        "NO",
        "REF",
        "CODE",
        "PROMPTPAY",
        "SERVICE",
        "MERCHANT",
        "BANK",
        "FEE",
        "NOTE",
    }

    valid_name_words = [
        word for word in capitalized_words if word not in excluded_words
    ]

    return len(valid_name_words) > 0 or has_business_pattern


def extract_capitalized_names(line: str, include_mr_ms: bool = True) -> str:
    """
    Extract capitalized names from a line

    Args:
        line: Text line to extract names from
        include_mr_ms: Whether to include MR/MS prefixes

    Returns:
        str: Extracted and cleaned name
    """
    line = line.strip()

    if include_mr_ms:
        # Keep MR/MS but clean up the rest
        name = re.sub(r"[^\w\s\.]", " ", line)  # Remove special chars except periods
    else:
        # Remove MR/MS prefixes
        name = re.sub(r"^(MR\.?\s+|MS\.?\s+|DR\.?\s+)", "", line, flags=re.IGNORECASE)
        name = re.sub(r"[^\w\s]", " ", name)  # Remove special chars

    # Clean up extra spaces
    name = re.sub(r"\s+", " ", name).strip()

    return name


def is_section_marker(line: str) -> bool:
    """
    Check if a line indicates the start of a new section (stop parsing names)

    Args:
        line: Text line to check

    Returns:
        bool: True if this line marks a section boundary
    """
    line_lower = line.lower().strip()

    section_markers = [
        "service code",
        "merchant id",
        "fee",
        "note",
        "bank reference",
        "promptpay",
        "prompt pay",
        "biller id",
        "ref no",
        "reference",
        "top up",
        "g-wallet",
        "k plus wallet",
        "e-wallet",
        "transaction reference",
    ]

    return any(marker in line_lower for marker in section_markers)


def apply_name_replacements(name: str) -> str:
    """
    Apply known name/entity replacements using the mapping file

    Args:
        name: Raw extracted name

    Returns:
        str: Name after applying replacements
    """
    from .recipient_mappings import apply_recipient_mappings

    return apply_recipient_mappings(name)
