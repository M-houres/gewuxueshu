param(
  [switch]$SkipBackendTests
)

$ErrorActionPreference = "Stop"
$cmdScript = Join-Path $PSScriptRoot "quality_gate.cmd"

if (-not (Test-Path $cmdScript)) {
  throw "Missing quality gate cmd script: $cmdScript"
}

if ($SkipBackendTests) {
  & cmd /c "`"$cmdScript`" --skip-backend"
} else {
  & cmd /c "`"$cmdScript`""
}

if ($LASTEXITCODE -ne 0) {
  throw "Quality gate failed."
}
