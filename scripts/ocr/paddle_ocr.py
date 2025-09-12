from paddleocr import PaddleOCR

_ocr_en = PaddleOCR(use_angle_cls=True, lang="en")
_ocr_th = PaddleOCR(use_angle_cls=True, lang="th")


def _to_lines(res):
    out = []
    if not res:
        return out
    for blk in res:
        for item in blk:
            text, score = item[1]
            if score >= 0.50:
                t = (text or "").strip()
                if t:
                    out.append(t)
    return out


def run_ocr(img_path: str) -> str:
    en = _ocr_en.ocr(img_path, cls=True)
    th = _ocr_th.ocr(img_path, cls=True)
    merged = _to_lines(en) + _to_lines(th)
    seen, lines = set(), []
    for ln in merged:
        if ln not in seen:
            seen.add(ln)
            lines.append(ln)
    return "\n".join(lines)
