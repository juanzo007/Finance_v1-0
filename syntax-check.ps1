# RunPipeline.ps1
# 1) Activate venv
# 2) Install requirements
# 3) Compile-check pipeline + extractors (abort on error)
# 4) Run pipeline

$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot

Write-Host "=== Activating virtual environment ==="
& "$here\.venv\Scripts\Activate.ps1"

Write-Host "=== Upgrading pip (just in case) ==="
python -m pip install --upgrade pip | Out-Null

Write-Host "=== Installing requirements.txt ==="
pip install -r "$here\requirements.txt"

# ------- Compile check (HARD GATE) -------
Write-Host "=== Syntax check: pipeline + extractors ==="

# Build file list safely (PowerShell expands the glob reliably here)
$files = @(
    "$here\finances_pipeline.py"
) + (Get-ChildItem "$here\scripts\image-scripts\*.py" -File | ForEach-Object { $_.FullName })

# Run compiler
python -m py_compile @files

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Syntax errors detected. Fix the file(s) above and re-run." -ForegroundColor Red
    exit 1
}

Write-Host "✅ All scripts compiled cleanly" -ForegroundColor Green
# -----------------------------------------

Write-Host "=== Running finances_pipeline.py ==="
try {
    python "$here\finances_pipeline.py"
    Write-Host "=== Done! Output written to Finances.xlsx ==="
}
catch {
    Write-Host "❌ Pipeline crashed. See error above." -ForegroundColor Red
    exit 1
}
