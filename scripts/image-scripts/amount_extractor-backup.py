# -*- coding: utf-8 -*-
"""
Debug version of amount_extractor.py - Extra logging to find the 759.00 issue
"""

import re
from typing import Dict, List, Optional
from decimal import Decimal, InvalidOperation

# More comprehensive money patterns for Thai banking (order matters!)
MONEY_PATTERNS = [
    # Standard format with commas: 150,000.00 or 2,500.00
    r"\b\d{1,3}(?:,\d{3})*\.\d{2}\b",
    # Simple numbers with decimals: 759.00, 300.00, etc
    r"\b\d{1,4}\.\d{2}\b",
    # Large numbers without commas: 150000.00
    r"\b\d{5,}\.\d{2}\b",
    # Numbers with commas but no decimals: 150,000 or 2,500
    r"\b\d{1,3}(?:,\d{3})+\b",
]

# Compile pattern that captures the full match
MONEY_RE = re.compile("|".join(MONEY_PATTERNS))

# Amount indicators (English and Thai)
AMOUNT_INDICATORS = [
    "amount",
    "ยอดเงิน",
    "จำนวนเงิน",
    "จำนวน",
    "total",
    "รวม",
    "THB",
    "บาท",
]

# Section separators to help identify amount region
SECTION_SEPARATORS = ["from", "to", "จาก", "ถึง", "fee", "ค่าธรรมเนียม"]


def clean_amount(amount_str: str) -> Optional[str]:
    """Clean and validate amount string, return formatted version or None"""
    if not amount_str:
        return None

    try:
        # Remove commas and convert to decimal
        clean_num = amount_str.replace(",", "")
        decimal_val = Decimal(clean_num)

        # Must be positive and reasonable (between 0.01 and 10,000,000)
        if decimal_val <= 0 or decimal_val > Decimal("10000000"):
            return None

        # Format back with commas and 2 decimal places
        return f"{decimal_val:,.2f}"

    except (InvalidOperation, ValueError):
        return None


def find_amount_near_label(lines: List[str]) -> Optional[str]:
    """Look for amount near 'Amount' or similar labels"""
    print(f"[DEBUG] find_amount_near_label - checking {len(lines)} lines")

    if not lines:
        return None

    for i, line in enumerate(lines):
        line_lower = line.lower()
        print(f"[DEBUG] Line {i}: '{line}' (lower: '{line_lower}')")

        # Check if this line contains an amount indicator
        indicators_found = [ind for ind in AMOUNT_INDICATORS if ind in line_lower]
        if indicators_found:
            print(f"[DEBUG] Found indicators {indicators_found} in line {i}")

            # Search this line and next few lines for amounts
            search_lines = lines[i : min(i + 4, len(lines))]
            print(f"[DEBUG] Searching lines {i} to {min(i+4, len(lines))-1}")

            for j, search_line in enumerate(search_lines):
                print(f"[DEBUG] Searching line {i+j}: '{search_line}'")
                amounts = MONEY_RE.findall(search_line)
                print(f"[DEBUG] Found amounts: {amounts}")

                for amount in amounts:
                    print(f"[DEBUG] Testing amount: '{amount}'")
                    cleaned = clean_amount(amount)
                    print(f"[DEBUG] Cleaned to: '{cleaned}'")
                    if cleaned:
                        print(f"[DEBUG] SUCCESS! Returning: {cleaned}")
                        return cleaned

    print("[DEBUG] find_amount_near_label - no amount found")
    return None


def find_amount_in_header(lines: List[str]) -> Optional[str]:
    """Find amount in header section (before From/To section)"""
    print(f"[DEBUG] find_amount_in_header - checking {len(lines)} lines")

    if not lines:
        return None

    # Find where the From/To section starts
    header_end = len(lines)
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        separators_found = [sep for sep in SECTION_SEPARATORS if sep in line_lower]
        if separators_found:
            header_end = i
            print(
                f"[DEBUG] Found separator '{separators_found}' at line {i}, header ends there"
            )
            break

    print(f"[DEBUG] Header section: lines 0 to {header_end-1}")

    # Look for amounts in header section
    candidates = []
    for i in range(min(header_end, len(lines))):
        line = lines[i]
        print(f"[DEBUG] Header line {i}: '{line}'")
        amounts = MONEY_RE.findall(line)
        print(f"[DEBUG] Found amounts: {amounts}")

        for amount in amounts:
            cleaned = clean_amount(amount)
            print(f"[DEBUG] Amount '{amount}' cleaned to '{cleaned}'")
            if cleaned:
                candidates.append((cleaned, i))

    print(f"[DEBUG] Header candidates: {candidates}")

    # Return the first valid amount found in header
    if candidates:
        result = candidates[0][0]
        print(f"[DEBUG] find_amount_in_header returning: {result}")
        return result

    print("[DEBUG] find_amount_in_header - no amount found")
    return None


def find_largest_amount(text: str) -> Optional[str]:
    """Fallback: find the largest reasonable amount in entire text"""
    print(f"[DEBUG] find_largest_amount - full text: '{text[:100]}...'")

    if not text:
        return None

    amounts = MONEY_RE.findall(text)
    print(f"[DEBUG] All amounts found in text: {amounts}")

    best_amount = None
    best_decimal = Decimal("0")

    for amount in amounts:
        cleaned = clean_amount(amount)
        print(f"[DEBUG] Amount '{amount}' cleaned to '{cleaned}'")
        if cleaned:
            try:
                decimal_val = Decimal(cleaned.replace(",", ""))
                print(f"[DEBUG] Decimal value: {decimal_val}")
                if decimal_val > best_decimal:
                    best_decimal = decimal_val
                    best_amount = cleaned
                    print(f"[DEBUG] New best: {best_amount}")
            except InvalidOperation:
                continue

    print(f"[DEBUG] find_largest_amount returning: {best_amount}")
    return best_amount


def extract(image_path: str, text: str = "", lines: List[str] = None) -> Dict[str, str]:
    """
    Extract withdrawal amount from OCR text/lines.
    Returns dict with consistent key naming for pipeline.
    """
    print(f"\n[DEBUG] ===== EXTRACTING FROM {image_path} =====")
    print(f"[DEBUG] Text length: {len(text) if text else 0}")
    print(f"[DEBUG] Lines count: {len(lines) if lines else 0}")

    if lines:
        print("[DEBUG] Lines:")
        for i, line in enumerate(lines):
            print(f"  [{i:02d}] '{line}'")

    if not lines:
        lines = []
    if not text:
        text = ""

    # Strategy 1: Look near "Amount" labels
    print("\n[DEBUG] === STRATEGY 1: Amount labels ===")
    amount = find_amount_near_label(lines)

    # Strategy 2: Look in header section
    if not amount:
        print("\n[DEBUG] === STRATEGY 2: Header section ===")
        amount = find_amount_in_header(lines)

    # Strategy 3: Find largest amount as fallback
    if not amount:
        print("\n[DEBUG] === STRATEGY 3: Largest amount fallback ===")
        amount = find_largest_amount(text)

    # Return with both keys for compatibility
    result = {
        "withdrawal": amount or "",
        "thb_withdrawal": amount or "",  # Pipeline expects this key
    }

    print(f"\n[DEBUG] ===== FINAL RESULT: {result} =====\n")
    return result


# Test function for debugging
def test_extraction():
    """Test with sample Bangkok Bank data"""
    # Test case 1: Regular amount
    test_lines1 = [
        "Bangkok Bank",
        "Transaction successful",
        "06 Sep 25, 13:22",
        "Amount",
        "2,500.00 THB",
        "From",
        "MR JOHN HARRIS",
    ]

    # Test case 2: The problematic 759.00 case
    test_lines2 = [
        "Bangkok Bank",
        "Transaction successful",
        "23 Feb 25, 17:50",
        "Amount",
        "759.00 THB",
        "From",
        "MR JOHN HARRIS",
    ]

    result1 = extract("test1", "\n".join(test_lines1), test_lines1)
    result2 = extract("test2", "\n".join(test_lines2), test_lines2)

    print(f"Test 1 (2,500.00): {result1}")
    print(f"Test 2 (759.00): {result2}")

    return result1, result2


if __name__ == "__main__":
    test_extraction()
