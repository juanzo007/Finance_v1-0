# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import Dict, List, Tuple

# Example lines we see:
# "07 Jan 25,14:24"
# "10 Jan 25, 00:39"
# "23 Feb 25,19:O1"   (OCR uses letter 'O' instead of zero)
# "06 Apr 25,16:56"
# Fallback source: "Transaction reference" like 202503291855... (yyyymmddHHMM...)

_MONTH = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

DATE_RE = re.compile(r"\b(?P<d>\d{1,2})\s+(?P<m>[A-Za-z]{3})\s+(?P<y>\d{2})\b")
TIME_RE = re.compile(r"\b(?P<h>[0-2OIl]\d)[:\.](?P<min>[0-5OIl]\d)\b")

# First 12 digits of the transaction reference look like yyyymmddHHMM
REF_TS_RE = re.compile(r"\b(20\d{12})\d*\b")


def _fix_ocr_digits(s: str) -> str:
    # Common OCR substitutions: O/I/l -> 0/1/1
    return s.replace("O", "0").replace("o", "0").replace("I", "1").replace("l", "1")


def _fmt_date(d: int, m: int, y2: int) -> str:
    y4 = 2000 + y2
    return f"{m:02d}/{d:02d}/{y4:d}"


def _fmt_time(h: int, m: int) -> str:
    h = max(0, min(h, 23))
    m = max(0, min(m, 59))
    return f"{h:02d}:{m:02d}"


def _parse_date_time_from_line(line: str) -> Tuple[str, str]:
    """
    Try to get date+time from a single header line like:
      '07 Jan 25,14:24' or '10 Jan 25, 00:39'
    """
    s = _fix_ocr_digits(line.strip())
    date_m = DATE_RE.search(s)
    if not date_m:
        return "", ""

    d = int(date_m.group("d"))
    mname = date_m.group("m").lower()
    if mname not in _MONTH:
        return "", ""
    m = _MONTH[mname]
    y2 = int(date_m.group("y"))

    # Prefer a time on the same line, if present
    time_m = TIME_RE.search(s)
    date_str = _fmt_date(d, m, y2)
    if time_m:
        h = int(_fix_ocr_digits(time_m.group("h")))
        mi = int(_fix_ocr_digits(time_m.group("min")))
        return date_str, _fmt_time(h, mi)
    else:
        return date_str, ""


def _parse_from_reference(lines: List[str]) -> Tuple[str, str]:
    """
    Fallback: derive from 'Transaction reference' lines that begin with
    yyyymmddHHMM..., e.g. 202503291855...
    """
    for ln in lines:
        m = REF_TS_RE.search(ln)
        if not m:
            continue
        ts = m.group(1)  # 14 digits yyyymmddHHMM?? (we only need first 12)
        y = int(ts[0:4])
        mo = int(ts[4:6])
        d = int(ts[6:8])
        hh = int(ts[8:10])
        mi = int(ts[10:12])
        return f"{mo:02d}/{d:02d}/{y:d}", _fmt_time(hh, mi)
    return "", ""


def extract(image_path: str, text: str = "", lines: List[str] = None) -> Dict[str, str]:
    """
    Return {'date': 'MM/DD/YYYY', 'time': 'HH:MM'} if found ('' if not).
    Strategy:
      1) Scan lines; the first one matching '<D> <Mon> <YY>' wins.
         - If a time is on that line, use it.
      2) If time still blank, try to find a time anywhere on the date line.
      3) Fallback to the transaction reference (yyyymmddHHMM...) if needed.
    """
    if lines is None or not isinstance(lines, list):
        lines = (text or "").splitlines()

    date_str, time_str = "", ""

    # Pass 1: look for a header date line (e.g., "07 Jan 25,14:24")
    for ln in lines:
        ds, ts = _parse_date_time_from_line(ln)
        if ds:
            date_str = ds
            time_str = time_str or ts  # keep if we got one
            break

    # Fallback: transaction reference timestamp
    if not date_str or not time_str:
        ds2, ts2 = _parse_from_reference(lines)
        if not date_str and ds2:
            date_str = ds2
        if not time_str and ts2:
            time_str = ts2

    return {
        "date": date_str or "",
        "time": time_str or "",
    }
