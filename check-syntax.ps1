Write-Host "=== Checking pipeline and extractors for syntax errors ==="

$files = @("finances_pipeline.py") + (Get-ChildItem -Path "scripts/image-scripts" -Filter *.py | ForEach-Object { $_.FullName })
$python = Get-Command python | Select-Object -ExpandProperty Source

$process = Start-Process -FilePath $python -ArgumentList "-m py_compile $($files -join ' ')" -NoNewWindow -PassThru -Wait

if ($process.ExitCode -eq 0) {
    Write-Host "✅ All scripts compiled cleanly"
}
else {
    Write-Host "❌ One or more scripts have syntax errors (see above)"
}
