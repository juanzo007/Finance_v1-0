# RunPipeline.ps1 — strict, loud, and boringly reliable

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

# --- Resolve paths ---
$here = $PSScriptRoot
$venvAct = Join-Path $here ".venv\Scripts\Activate.ps1"
$pipeline = Join-Path $here "finances_pipeline.py"
$extractorDir = Join-Path $here "scripts\image-scripts"
$outXlsx = Join-Path $here "Finances.xlsx"

Write-Host "=== Working dir  : $here"
Write-Host "=== Pipeline     : $pipeline"
Write-Host "=== Extractors   : $extractorDir"
Write-Host "=== Output XLSX  : $outXlsx"
Write-Host ""

# --- Sanity: required files/folders ---
if (!(Test-Path $venvAct)) { Write-Host "❌ Missing venv: $venvAct" -ForegroundColor Red; exit 1 }
if (!(Test-Path $pipeline)) { Write-Host "❌ Missing pipeline: $pipeline" -ForegroundColor Red; exit 1 }
if (!(Test-Path $extractorDir)) { Write-Host "❌ Missing extractor folder: $extractorDir" -ForegroundColor Red; exit 1 }

# --- Show extractor files ---
$extractors = Get-ChildItem "$extractorDir\*.py" -File
if ($extractors.Count -eq 0) {
    Write-Host "❌ No extractor scripts found in $extractorDir" -ForegroundColor Red
    exit 1
}
Write-Host "=== Extractor scripts detected ==="
$extractors | ForEach-Object { Write-Host (" - " + $_.FullName) }
Write-Host ""

# --- Check if output file is locked by Excel ---
try {
    if (Test-Path $outXlsx) {
        $fs = [System.IO.File]::Open($outXlsx, 'Open', 'ReadWrite', 'None')
        $fs.Close()
    }
}
catch {
    Write-Host "❌ $outXlsx appears to be open/locked (close Excel and retry)." -ForegroundColor Red
    exit 1
}

# --- Activate venv ---
Write-Host "=== Activating virtual environment ==="
. $venvAct

# --- Upgrade pip & install deps ---
Write-Host "=== Upgrading pip (quiet) ==="
python -m pip install --upgrade pip | Out-Null

Write-Host "=== Installing requirements.txt ==="
pip install -r "$here\requirements.txt"

# --- HARD syntax gate (pipeline + all extractors) ---
Write-Host "=== Syntax check: pipeline + extractors ==="
$targets = @($pipeline) + ($extractors | ForEach-Object { $_.FullName })
python -m py_compile @targets
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Syntax errors above. Fix and re-run." -ForegroundColor Red
    exit 1
}
Write-Host "✅ All scripts compiled cleanly" -ForegroundColor Green

# --- Run pipeline with optional debug ---
$env:PIPE_DEBUG = if ($env:PIPE_DEBUG) { $env:PIPE_DEBUG } else { "0" }
Write-Host "=== Running finances_pipeline.py (PIPE_DEBUG=$env:PIPE_DEBUG) ==="
try {
    python "$pipeline"
    if (Test-Path $outXlsx) {
        Write-Host "✅ Done. Output: $outXlsx" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Pipeline finished but $outXlsx was not created." -ForegroundColor Red
        Write-Host "   Check console for earlier errors (Excel lock, permissions, etc.)."
        exit 1
    }
}
catch {
    Write-Host "❌ Pipeline crashed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
