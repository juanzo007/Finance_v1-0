# -*- coding: utf-8 -*-
"""
amount_extractor.py — Extract THB amount using full-text regex (MiniCPM-friendly)
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List

# Match patterns like "123,456.78" or "123456.78"
AMOUNT_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b|\b\d+(?:\.\d{2})\b")


def extract_amount(text: str) -> Optional[float]:
    if not text:
        return None
    matches = AMOUNT_RE.findall(text)
    amounts = []
    for raw in matches:
        clean = raw.replace(",", "")
        try:
            amt = Decimal(clean).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if amt > 0:
                amounts.append(amt)
        except:
            continue
    if not amounts:
        return None
    return float(max(amounts))  # assume largest is withdrawal


def extract(
    image_path: str, text: str = "", lines: List[str] = None
) -> Dict[str, float]:
    val = extract_amount(text or "")
    return {"thb_withdrawal": val if val is not None else ""}
