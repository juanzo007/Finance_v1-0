# -*- coding: utf-8 -*-
"""
note_extractor.py — Extract note block (Paddle text)

Strategy:
- Look for explicit "Note: ..." on the same line
- Else, capture the line after a line that contains "Note" (skipping obvious labels)
"""

import re
from typing import List, Dict

STOP_WORDS = (
    "bank reference",
    "transaction reference",
    "scan to verify",
    "fee",
    "merchant id",
    "ref no",
)
NOTE_BLOCK_RE = re.compile(r"(?i)(?:note\s*[:\-–]?\s*)([^\n]+)")


def extract_note(text: str) -> str:
    # Direct "Note: xxx"
    m = NOTE_BLOCK_RE.search(text or "")
    if m:
        return m.group(1).strip()

    # Fallback: find line after a "Note" line
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if "note" in line.lower():
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                low = next_line.lower()
                if not any(s in low for s in STOP_WORDS):
                    return next_line
    return ""


def extract(image_path: str, text: str = "", lines: List[str] = None) -> Dict[str, str]:
    return {"note": extract_note(text or "")}
