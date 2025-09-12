# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Dict, List, Optional

# Simple Thai detection (Unicode block U+0E00..U+0E7F)
_TH_RE = re.compile(r"[\u0E00-\u0E7F]")

# Some labels that appear below the recipient, where we should stop
_LABELS = {
    "fee",
    "bank reference no.",
    "transaction reference",
    "transaction id",
    "biller id",
    "merchant id",
    "service code",
    "reference no.",
    "refernce no.",
    "promptpay",
    "scan to verify",
    "e-wallet number",
    "e-wallet number.",
    "k plus wallet",
    "g-wallet",
    "k+ shop",
}

# Looks like an account / id number line we should ignore as a name
_IDISH = re.compile(r"[\d\-xX]{4,}")


def _is_thai(s: str) -> bool:
    return bool(_TH_RE.search(s))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _is_labelish(s: str) -> bool:
    low = s.lower()
    return any(lbl in low for lbl in _LABELS)


def _good_name_line(s: str) -> bool:
    """Accept lines that look like names; reject obvious ids/labels."""
    s = _norm(s)
    if not s:
        return False
    if _is_labelish(s):
        return False
    if _IDISH.search(s):
        # Likely account / biller / wallet number line, skip as name
        return False
    return True


def _pick_description_after_to(lines: List[str]) -> str:
    """
    Find 'To' and return next 1 (and possibly 2) lines:
      - If next line(s) look Thai -> return 'Thai'
      - Otherwise join 1-2 'name-like' lines by a space
    """
    for i, raw in enumerate(lines):
        if _norm(raw).lower() == "to":
            # Candidates are the next 1 and maybe 2 lines
            cand1 = _norm(lines[i + 1]) if i + 1 < len(lines) else ""
            cand2 = _norm(lines[i + 2]) if i + 2 < len(lines) else ""

            # Thai override
            if cand1 and _is_thai(cand1):
                return "Thai"
            if cand2 and _is_thai(cand2):
                return "Thai"

            parts: List[str] = []
            if cand1 and _good_name_line(cand1):
                parts.append(cand1)
            if cand2 and _good_name_line(cand2):
                parts.append(cand2)

            return " ".join(parts).strip()
    return ""


def extract(image_path: str, text: str = "", lines: List[str] = None) -> Dict[str, str]:
    """
    Return {'description': <value>} using the 'To' anchor rule:
      - Find the line 'To'
      - Description = the next 1 and possibly 2 lines (filtered)
      - If those look Thai -> 'Thai'
    """
    if lines is None or not isinstance(lines, list):
        lines = (text or "").splitlines()

    desc = _pick_description_after_to(lines)

    # Final tidy: if empty, return empty string; never None
    return {"description": desc or ""}
