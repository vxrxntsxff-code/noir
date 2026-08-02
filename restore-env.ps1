# restore-env.ps1 — Restore Vercel env vars from .env.prod
# Usage: .\restore-env.ps1 [project-name]
# Default project: test

param([string]$Project = "test")

$ErrorActionPreference = "Stop"
$envFile = Join-Path $PSScriptRoot ".env.prod"

if (!(Test-Path $envFile)) {
    Write-Host "ERROR: .env.prod not found at $envFile" -ForegroundColor Red
    exit 1
}

Write-Host "Restoring env vars for project: $Project" -ForegroundColor Cyan

$vars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^([A-Z_][A-Z0-9_]*)=(.*)$') {
        $vars[$matches[1]] = $matches[2].Trim('"')
    }
}

foreach ($key in $vars.Keys) {
    $val = $vars[$key]
    Write-Host "  Setting $key..." -NoNewline
    # Remove first
    npx vercel env rm $key production --yes 2>&1 | Out-Null
    # Add
    if ($val -match "`n") {
        $val | npx vercel env add $key production --yes 2>&1 | Out-Null
    } else {
        npx vercel env add $key production --value $val --yes 2>&1 | Out-Null
    }
    Write-Host " OK" -ForegroundColor Green
}

Write-Host "`nDone. Deploy with: npx vercel deploy --prod --force --yes" -ForegroundColor Cyan
