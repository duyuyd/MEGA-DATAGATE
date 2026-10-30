$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
if ($args.Count -gt 0) {
    $Out = $args[0]
} else {
    $Out = Join-Path "build" ("demo-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
}

python -m datagate inspect examples/incoming_customers.csv --out (Join-Path $Out "incoming")
python -m datagate compare examples/baseline.profile.json (Join-Path $Out "incoming/profile.json") --out (Join-Path $Out "drift")

& python -m datagate validate examples/incoming_customers.csv --contract examples/customers.contract.json --out (Join-Path $Out "validation")
$ValidationStatus = $LASTEXITCODE
if ($ValidationStatus -eq 1) {
    Write-Host "Expected: the synthetic sample contains contract violations."
} elseif ($ValidationStatus -ne 0) {
    throw "DataGate validation failed operationally (exit $ValidationStatus)."
}

python -m datagate clean examples/incoming_customers.csv --contract examples/customers.contract.json --out (Join-Path $Out "cleaned_customers.csv")
Write-Host "Demo artifacts: $Out"
