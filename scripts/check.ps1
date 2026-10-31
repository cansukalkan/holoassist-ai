# Doğrulama: depo kökünden çalıştırın; ilk hata ile durur.
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
foreach ($arguments in @(@('-m','pytest'), @('-m','ruff','check','.'), @('-m','pip','check'))) {
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
