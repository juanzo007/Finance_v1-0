# -*- coding: utf-8 -*-
"""
finances_pipeline.py — schema-preserving pipeline with per-extractor DEBUG logs.
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import importlib.util

import pandas as pd
from paddleocr import PaddleOCR

# --- Paths ---
ROOT = Path(__file__).resolve().parent
IMG_DIR = ROOT / "data" / "test-images"
OUT_XLSX = ROOT / "Finances.xlsx"

# Make sure our helpers are preferred over site-packages collisions (e.g., PaddleOCR's utils)
TOOLS_DIR = str(ROOT / "scripts" / "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

SCRIPTS_DIR = ROOT / "scripts" / "image-scripts"
EXTRACTORS = {
    "date": SCRIPTS_DIR / "date_extractor.py",
    "amount": SCRIPTS_DIR / "amount_extractor.py",
    "description": SCRIPTS_DIR / "description_extractor.py",
    "note": SCRIPTS_DIR / "note_extractor.py",  # may be missing; handled gracefully
}

DEBUG = os.environ.get("PIPE_DEBUG", "0") == "1"


# --- Logging helpers ---
def _log(msg: str) -> None:
    print(msg, flush=True)


def _load_optional(name: str, path: Path):
    """Load a module if the file exists; else return None (skip that extractor).
    Temporarily prepend the extractor directory to sys.path so relative-like
    imports such as `from utils import ...` resolve to the local file instead
    of site-packages (e.g., PaddleOCR's utils).
    """
    import sys

    _log(f"[LOAD] {name} -> {path}")
    if not path.exists():
        _log(f"[WARN] Extractor missing: {path.name} (skipping)")
        return None

    # Temporarily put the extractor's folder at the front of sys.path
    added = False
    try:
        folder = str(path.parent)
        if folder not in sys.path:
            sys.path.insert(0, folder)
            added = True

        spec = importlib.util.spec_from_file_location(name, str(path))
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load {name} from {path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        # Restore sys.path to avoid leaking state across loads
        if added and sys.path and sys.path[0] == folder:
            sys.path.pop(0)


# --- OCR engine (use supported language key) ---
_OCR = PaddleOCR(lang="en", use_angle_cls=True, show_log=False)


def _ocr_image(p: Path) -> Tuple[str, List[str]]:
    """Return (full_text, ordered_lines) from PaddleOCR."""
    result = _OCR.ocr(str(p), cls=True)
    lines: List[str] = []
    if result and isinstance(result, list):
        for page in result or []:
            if not page:
                continue
            for _, (txt, _score) in page:
                if not txt:
                    continue
                s = re.sub(r"\s+", " ", txt.strip())
                if s:
                    lines.append(s)
    text = "\n".join(lines)
    if DEBUG:
        _log(f"[DEBUG] OCR lines for {p.name}:")
        for i, ln in enumerate(lines):
            _log(f"   [{i:02d}] {ln}")
    return text, lines


def _coerce_amount(val: Any) -> Any:
    """Return float if safely coercible; else blank ('')."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str) and val.strip():
        try:
            return float(val.replace(",", ""))
        except Exception:
            return ""
    return ""


def main():
    # Load current workbook schema (preserve headers/order exactly).
    if OUT_XLSX.exists():
        try:
            df = pd.read_excel(OUT_XLSX)
            headers = list(df.columns)
            _log(f"[INFO] Loaded {OUT_XLSX} with {len(headers)} column(s).")
        except Exception as e:
            _log(f"[ERROR] Could not read {OUT_XLSX}: {e}")
            return
    else:
        df = pd.DataFrame()
        headers = []
        _log(
            f"[WARN] {OUT_XLSX} not found. No headers to map; will not create new schema."
        )

    # Load extractors (optionally skip missing ones)
    date_mod = _load_optional("date_extractor", EXTRACTORS["date"])
    amt_mod = _load_optional("amount_extractor", EXTRACTORS["amount"])
    desc_mod = _load_optional("description_extractor", EXTRACTORS["description"])
    note_mod = _load_optional("note_extractor", EXTRACTORS["note"])

    # Collect images
    images: List[Path] = []
    for pat in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        images.extend(sorted(IMG_DIR.glob(pat)))

    _log(f"[INFO] Found {len(images)} image(s) in {IMG_DIR}")

    has_image_col = "Image" in headers

    for img in images:
        try:
            text, lines = _ocr_image(img)
            _log(f"[OCR] {img.name}: {len(lines)} line(s) recognized.")

            # --- Date/Time ---
            try:
                d = (
                    date_mod.extract(image_path=str(img), text=text, lines=lines)
                    if date_mod
                    else {}
                )
            except Exception as e:
                _log(
                    f"[EXTRACT-ERROR] {img.name} :: date_extractor: {type(e).__name__}: {e}"
                )
                d = {}
            _log(f"[DEBUG] {img.name} :: date_extractor -> {d}")

            # --- Amount ---
            try:
                a = (
                    amt_mod.extract(image_path=str(img), text=text, lines=lines)
                    if amt_mod
                    else {}
                )
            except Exception as e:
                _log(
                    f"[EXTRACT-ERROR] {img.name} :: amount_extractor: {type(e).__name__}: {e}"
                )
                a = {}
            _log(f"[DEBUG] {img.name} :: amount_extractor -> {a}")

            # --- Description ---
            try:
                de = (
                    desc_mod.extract(image_path=str(img), text=text, lines=lines)
                    if desc_mod
                    else {}
                )
            except Exception as e:
                _log(
                    f"[EXTRACT-ERROR] {img.name} :: description_extractor: {type(e).__name__}: {e}"
                )
                de = {}
            _log(f"[DEBUG] {img.name} :: description_extractor -> {de}")

            # --- Note ---
            try:
                n = (
                    note_mod.extract(image_path=str(img), text=text, lines=lines)
                    if note_mod
                    else {}
                )
            except Exception as e:
                _log(
                    f"[EXTRACT-ERROR] {img.name} :: note_extractor: {type(e).__name__}: {e}"
                )
                n = {}
            _log(f"[DEBUG] {img.name} :: note_extractor -> {n}")

            # --- Build updates ONLY for existing headers ---
            updates: Dict[str, Any] = {}

            # Date / Time
            if isinstance(d, dict):
                if "Date" in headers and "date" in d:
                    updates["Date"] = d.get("date", "")
                if "Time" in headers and "time" in d:
                    updates["Time"] = d.get("time", "")

            # Amount -> Withdrawal THB (accept both keys from extractor)
            if "Withdrawal THB" in headers and isinstance(a, dict):
                amt_key = (
                    "thb_withdrawal"
                    if "thb_withdrawal" in a
                    else ("withdrawal" if "withdrawal" in a else None)
                )
                if amt_key:
                    updates["Withdrawal THB"] = _coerce_amount(a.get(amt_key, ""))

            # Description -> Description/Descrition (whichever exists)
            if isinstance(de, dict) and "description" in de:
                desc_header = None
                if "Descrition" in headers:
                    desc_header = "Descrition"
                elif "Description" in headers:
                    desc_header = "Description"
                if desc_header:
                    updates[desc_header] = de.get("description", "")

            # Note
            if "Note" in headers and isinstance(n, dict) and "note" in n:
                updates["Note"] = n.get("note", "")

            # Nothing to update and no Image anchor? Skip.
            if not updates and not has_image_col:
                _log(f"[SKIP] {img.name}: no matching headers to update.")
                continue

            if has_image_col:
                # Upsert by 'Image'
                if len(df) and (df["Image"].astype(str) == img.name).any():
                    idx = df.index[df["Image"].astype(str) == img.name][0]
                    for k, v in updates.items():
                        if k in headers:
                            df.at[idx, k] = v
                else:
                    if headers:
                        blank = {h: "" for h in headers}
                        blank["Image"] = img.name
                        for k, v in updates.items():
                            if k in headers:
                                blank[k] = v
                        df = pd.concat([df, pd.DataFrame([blank])], ignore_index=True)
                    else:
                        _log(
                            f"[SKIP] {img.name}: workbook has no headers; not creating new schema."
                        )
                        continue
            else:
                # No 'Image' column: append a row using only existing headers
                if headers:
                    row = {h: "" for h in headers}
                    for k, v in updates.items():
                        if k in headers:
                            row[k] = v
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                else:
                    _log(
                        f"[SKIP] {img.name}: workbook has no headers; not creating new schema."
                    )
                    continue

            _log(
                f"[OK] {img.name}: "
                + (
                    ", ".join(f"{k}={updates[k]!r}" for k in updates)
                    if updates
                    else "(no updates)"
                )
            )

        except KeyboardInterrupt:
            _log("[ABORTED] KeyboardInterrupt")
            raise
        except Exception as e:
            _log(f"[ERROR] {img.name}: {e}")

    # Write back with original header order (unchanged)
    if headers:
        df = df[headers]
        df.to_excel(OUT_XLSX, index=False)
        _log(f"[DONE] Updated: {OUT_XLSX}")
    else:
        _log(f"[DONE] No headers found in {OUT_XLSX}; nothing written.")


if __name__ == "__main__":
    main()
