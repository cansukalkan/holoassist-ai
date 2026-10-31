# Append development API credentials without displaying or replacing existing secrets.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envPath)) { throw 'Create the local .env before configuring API credentials.' }
$content = [System.IO.File]::ReadAllText($envPath)
$operatorConfigured = $content -match '(?m)^HOLOASSIST_API_OPERATOR_TOKEN=.+$'
$reviewerConfigured = $content -match '(?m)^HOLOASSIST_API_REVIEWER_TOKEN=.+$'
if ($operatorConfigured -and $reviewerConfigured) { Write-Output 'Existing local API credentials preserved.'; exit 0 }
if ($operatorConfigured -or $reviewerConfigured) { throw 'Partial API credentials exist; configure both explicitly without overwriting secrets.' }
if ($content -match '(?m)^HOLOASSIST_API_(OPERATOR|REVIEWER)_TOKEN=') { throw 'Blank API settings exist; configure them explicitly.' }
function New-LocalToken {
    $tokenBytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($tokenBytes) } finally { $rng.Dispose() }
    return [System.BitConverter]::ToString($tokenBytes).Replace('-', '').ToLowerInvariant()
}
$content += "`nHOLOASSIST_API_OPERATOR_TOKEN=" + (New-LocalToken)
$content += "`nHOLOASSIST_API_REVIEWER_TOKEN=" + (New-LocalToken) + "`n"
[System.IO.File]::WriteAllText($envPath, $content, [System.Text.UTF8Encoding]::new($false))
Write-Output 'Local API credentials created; no secrets displayed.'
