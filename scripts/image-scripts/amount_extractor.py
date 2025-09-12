# -*- coding: utf-8 -*-
"""
amount_extractor.py — pick the withdrawal amount from OCR text/lines *provided by the pipeline*.
No OCR happens here (mirrors note_extractor style).

Heuristics (run in order):
1) Prefer the number on the same line as 'Amount' or the next few lines.
2) If 'Amount' label is missed, search the header region before the 'From' section.
3) Fallback to the largest money-looking number anywhere in the text.

Returns: {"withdrawal": "<amount-string or ''>"}
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

# money like 155,000.00 or 520.00
MONEY_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b|\b\d+(?:\.\d{2})\b")

# Labels and section anchors we’ve seen
AMOUNT_LABELS = ("amount", "ยอดเงิน", "จำนวนเงิน")
FROM_LABELS = ("from", "จาก")


def _to_decimal(tok: str) -> Optional[Decimal]:
    try:
        v = Decimal(tok.replace(",", "")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return v if v > 0 else None
    except Exception:
        return None


def _fmt(v: Decimal) -> str:
    # 1234.50 -> "1,234.50"
    q = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{q:.2f}"
    whole, dot, frac = s.partition(".")
    whole_commas = "{:,}".format(int(whole))
    return whole_commas + dot + frac


def _window_after_amount(lines: List[str]) -> Optional[str]:
    """Find 'Amount' line, then look same line and next few lines for money tokens."""
    if not lines:
        return None
    low = [ln.lower() for ln in lines]
    for i, ln in enumerate(low):
        if any(lbl in ln for lbl in AMOUNT_LABELS):
            # same line first
            for tok in MONEY_RE.findall(lines[i]):
                v = _to_decimal(tok)
                if v is not None:
                    return _fmt(v)
            # then next 1..4 lines (layout varies)
            for j in range(i + 1, min(i + 5, len(lines))):
                for tok in MONEY_RE.findall(lines[j]):
                    v = _to_decimal(tok)
                    if v is not None:
                        return _fmt(v)
            break
    return None


def _header_before_from(lines: List[str]) -> Optional[str]:
    """Heuristic: search money tokens above the 'From'/'จาก' section."""
    if not lines:
        return None
    low = [ln.lower() for ln in lines]
    end = len(lines)
    for i, ln in enumerate(low):
        if any(lbl == ln.strip() or ln.strip().startswith(lbl) for lbl in FROM_LABELS):
            end = i
            break
    # Scan top→end for first plausible amount (topmost bold area usually has it)
    for i in range(0, end):
        for tok in MONEY_RE.findall(lines[i]):
            v = _to_decimal(tok)
            if v is not None:
                return _fmt(v)
    return None


def _largest_anywhere(text: str) -> Optional[str]:
    if not text:
        return None
    best: Optional[Decimal] = None
    for tok in MONEY_RE.findall(text):
        v = _to_decimal(tok)
        if v is None:
            continue
        if best is None or v > best:
            best = v
    return _fmt(best) if best is not None else None


def extract(image_path: str, text: str = "", lines: List[str] = None) -> Dict[str, str]:
    """
    Called by the pipeline. Uses OCR output supplied by the pipeline (PaddleOCR).
    """
    # 1) ‘Amount’ window
    amt = _window_after_amount(lines or [])
    if not amt:
        # 2) header region (before 'From')
        amt = _header_before_from(lines or [])
    if not amt:
        # 3) largest number anywhere
        amt = _largest_anywhere(text or "")
    return {"withdrawal": amt or ""}
