param([switch]$NoBuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and rerun this script.' }
try {
    $tags = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 10
} catch {
    throw 'Start Ollama (ollama serve) before starting CodeImpact.'
}
$models = @($tags.models.name)
foreach ($required in @('codellama:latest', 'nomic-embed-text:latest')) {
    if ($models -notcontains $required) {
        throw "Required model is missing: $required. Run: ollama pull $required"
    }
}
if ($NoBuild) { docker compose up -d } else { docker compose up --build -d }
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose did not complete successfully. Check the output above.' }
Write-Host 'CodeImpact: http://127.0.0.1:5070/'
Write-Host 'RepoPilot: http://127.0.0.1:5050/'
Write-Host 'Status: docker compose ps'
