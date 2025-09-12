Quickstart
===========
1) Create/activate a virtualenv, then install requirements:
   pip install -r requirements.txt

2) Make sure Tesseract OCR is installed on your system (for image receipts).
   - macOS (brew): brew install tesseract
   - Ubuntu/Debian: sudo apt-get install tesseract-ocr
   - Windows: install from https://github.com/UB-Mannheim/tesseract/wiki

3) Run the pipeline with your config:
   python merge_finances_pipeline.py --config config-root.yaml

Notes
-----
- The script recursively walks the directories you provided.
- Receipts -> THB Withdrawal
- Bangkok PDFs -> Withdrawal→THB Withdrawal, Deposit→THB Deposit
- Chase PDFs -> USD Amount
- No FX math.
- Dedupe rule: if a Bangkok PDF row matches a receipt by (Date, THB Withdrawal), the PDF row is dropped.
