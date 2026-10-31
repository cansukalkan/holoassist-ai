# Create local credentials without displaying or overwriting them.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) { throw '.env already exists; preserve it and configure PostgreSQL explicitly.' }
$template = Get-Content -LiteralPath (Join-Path $projectRoot '.env.example') -Raw
$passwordBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($passwordBytes) } finally { $rng.Dispose() }
$passwordValue = [System.BitConverter]::ToString($passwordBytes).Replace('-', '').ToLowerInvariant()
$template = $template.Replace('HOLOASSIST_POSTGRES_PASSWORD=', 'HOLOASSIST_POSTGRES_PASSWORD=' + $passwordValue)
$template = $template.Replace('HOLOASSIST_APPROVAL_BACKEND=sqlite', 'HOLOASSIST_APPROVAL_BACKEND=postgres')
[System.IO.File]::WriteAllText($envPath, $template, [System.Text.UTF8Encoding]::new($false))
Write-Output 'Local .env created for PostgreSQL; password was not displayed.'
