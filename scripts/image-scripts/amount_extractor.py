# -*- coding: utf-8 -*-
"""
Simple brute-force amount_extractor.py - No fancy regex, just string operations
"""

import re
from typing import Dict, List, Optional
from decimal import Decimal, InvalidOperation


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


def extract_numbers_from_text(text: str) -> List[str]:
    """Extract all number-like patterns from text using simple approach"""
    if not text:
        return []

    # Find all potential number patterns (much simpler approach)
    # Look for digits followed by optional comma/digits and decimal
    simple_pattern = r"\d+(?:,\d{3})*(?:\.\d{2})?"
    matches = re.findall(simple_pattern, text)

    results = []
    for match in matches:
        # Skip if it looks like a reference number (too many digits without decimals)
        if "." not in match and len(match.replace(",", "")) > 6:
            continue
        # Skip if it doesn't look like money (no decimal or wrong decimal places)
        if "." in match:
            decimal_part = match.split(".")[-1]
            if len(decimal_part) != 2:
                continue

        results.append(match)

    return results


def find_amount_near_amount_label(lines: List[str]) -> Optional[str]:
    """Look for amount near 'Amount' label using simple string operations"""
    print(f"[AMOUNT DEBUG] find_amount_near_amount_label - checking {len(lines)} lines")

    if not lines:
        return None

    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        print(f"[AMOUNT DEBUG] Line {i}: '{line}' (lower: '{line_lower}')")

        # Simple check for "amount" in the line
        if "amount" in line_lower:
            print(f"[AMOUNT DEBUG] Found 'amount' in line {i}")

            # Check this line and next few lines
            search_lines = lines[i : min(i + 4, len(lines))]

            for j, search_line in enumerate(search_lines):
                print(f"[AMOUNT DEBUG] Searching line {i+j}: '{search_line}'")

                # Simple approach: look for patterns like "123.45" in the line
                numbers = extract_numbers_from_text(search_line)
                print(f"[AMOUNT DEBUG] Found numbers: {numbers}")

                for num in numbers:
                    # Special handling for numbers attached to THB
                    if search_line.endswith("THB") and not num.endswith("THB"):
                        # Check if this number appears right before THB
                        if f"{num}THB" in search_line:
                            print(f"[AMOUNT DEBUG] Found {num} attached to THB")
                            cleaned = clean_amount(num)
                            if cleaned:
                                print(f"[AMOUNT DEBUG] SUCCESS! Returning: {cleaned}")
                                return cleaned

                    # Regular number processing
                    cleaned = clean_amount(num)
                    print(f"[AMOUNT DEBUG] Number '{num}' cleaned to '{cleaned}'")
                    if cleaned:
                        print(f"[AMOUNT DEBUG] SUCCESS! Returning: {cleaned}")
                        return cleaned

    print("[AMOUNT DEBUG] find_amount_near_amount_label - no amount found")
    return None


def find_largest_reasonable_amount(text: str, lines: List[str]) -> Optional[str]:
    """Find the largest reasonable amount using simple approach"""
    print(f"[AMOUNT DEBUG] find_largest_reasonable_amount")

    if not text and not lines:
        return None

    # Combine all text
    all_text = text + " " + " ".join(lines or [])
    numbers = extract_numbers_from_text(all_text)

    print(f"[AMOUNT DEBUG] All numbers found: {numbers}")

    best_amount = None
    best_decimal = Decimal("0")

    for num in numbers:
        cleaned = clean_amount(num)
        print(f"[AMOUNT DEBUG] Number '{num}' cleaned to '{cleaned}'")
        if cleaned:
            try:
                decimal_val = Decimal(cleaned.replace(",", ""))
                if decimal_val > best_decimal:
                    best_decimal = decimal_val
                    best_amount = cleaned
                    print(f"[AMOUNT DEBUG] New best: {best_amount}")
            except InvalidOperation:
                continue

    print(f"[AMOUNT DEBUG] find_largest_reasonable_amount returning: {best_amount}")
    return best_amount


def extract(image_path: str, text: str = "", lines: List[str] = None) -> Dict[str, str]:
    """
    Extract withdrawal amount using simple string operations instead of complex regex.
    """
    print(f"\n[AMOUNT DEBUG] ===== EXTRACTING FROM {image_path} =====")
    print(f"[AMOUNT DEBUG] Text length: {len(text) if text else 0}")
    print(f"[AMOUNT DEBUG] Lines count: {len(lines) if lines else 0}")

    if lines:
        print("[AMOUNT DEBUG] Lines:")
        for i, line in enumerate(lines):
            print(f"  [{i:02d}] '{line}'")

    if not lines:
        lines = []
    if not text:
        text = ""

    # Strategy 1: Look near "Amount" labels
    print("\n[AMOUNT DEBUG] === STRATEGY 1: Amount labels ===")
    amount = find_amount_near_amount_label(lines)

    # Strategy 2: Find largest reasonable amount as fallback
    if not amount:
        print("\n[AMOUNT DEBUG] === STRATEGY 2: Largest reasonable amount ===")
        amount = find_largest_reasonable_amount(text, lines)

    # Return with both keys for compatibility
    result = {"withdrawal": amount or "", "thb_withdrawal": amount or ""}

    print(f"\n[AMOUNT DEBUG] ===== FINAL RESULT: {result} =====\n")
    return result


# Test function for debugging
def test_extraction():
    """Test with the problematic case"""
    test_lines = [
        "Bangkok Bank",
        "Transaction successful",
        "23 Feb 25,17:50",
        "Amount",
        "759.00THB",
        "From",
        "MR JOHN HARRIS",
    ]

    result = extract("test", "\n".join(test_lines), test_lines)
    print(f"Test result: {result}")
    return result


if __name__ == "__main__":
    test_extraction()
