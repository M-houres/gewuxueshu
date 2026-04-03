param(
  [switch]$SkipBackendTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$backend = Join-Path $root "backend"

function Write-Step($msg) {
  Write-Host ""
  Write-Host "[quality] $msg"
}

Write-Step "Frontend build"
Push-Location $frontend
try {
  if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    cmd /c "npm install --ignore-scripts"
    if ($LASTEXITCODE -ne 0) {
      throw "Frontend dependencies install failed."
    }
  }
  cmd /c "npm run build"
  if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed."
  }
}
finally {
  Pop-Location
}

if ($SkipBackendTests) {
  Write-Step "Skip backend tests by flag"
  exit 0
}

$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  $python = "python"
}

Write-Step "Backend tests"
Push-Location $backend
try {
  & $python -c "import fastapi" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Skip backend tests: dependencies missing."
    Write-Host "Hint: cd backend; $python -m pip install -r requirements.txt"
    exit 0
  }
  & $python -m pytest -q
  if ($LASTEXITCODE -ne 0) {
    throw "Backend tests failed."
  }
}
finally {
  Pop-Location
}

Write-Step "Quality gate passed"
