$ErrorActionPreference = "Stop"

$key = Read-Host "sk-yzwAIZzGEOwWEBGrMkp6Hf4jsP6DfSy7zlDWKhmnx2pSQMIa"
if ([string]::IsNullOrWhiteSpace($key)) {
    throw "STABILITY_API_KEY is required."
}

$envPath = Join-Path (Get-Location) ".env"
$content = @(
    "# Local secrets for StyleScape-MVP"
    "# Do not share this file."
    "STABILITY_API_KEY=$($key.Trim())"
)

Set-Content -LiteralPath $envPath -Value $content -Encoding UTF8
Write-Host "Saved STABILITY_API_KEY to .env"
Write-Host "Now run: .\venv\Scripts\python.exe app.py"
