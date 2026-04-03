param(
  [string]$RootPath = "",
  [int]$IntervalSeconds = 600,
  [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RootPath)) {
  $RootPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if ([string]::IsNullOrWhiteSpace($LogPath)) {
  $LogPath = Join-Path $RootPath "docs\third_party_report_watch.log"
}

function Write-Log {
  param([string]$Message)
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $line = "[$ts] $Message"
  $dir = Split-Path -Parent $LogPath
  if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
  }
  Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Find-CandidateReports {
  param([string]$Base)
  $all = Get-ChildItem -Path $Base -Recurse -File -ErrorAction SilentlyContinue
  $all | Where-Object {
    $_.Name -match "第三方|审查|审计|review|audit|report|报告"
  }
}

Write-Log "watcher started. root=$RootPath interval=${IntervalSeconds}s"

$known = @{}
while ($true) {
  try {
    $files = Find-CandidateReports -Base $RootPath
    if (-not $files -or $files.Count -eq 0) {
      Write-Log "no report file found"
    } else {
      foreach ($f in $files) {
        $key = $f.FullName
        $stamp = $f.LastWriteTimeUtc.ToString("o")
        if (-not $known.ContainsKey($key)) {
          $known[$key] = $stamp
          Write-Log "new report candidate: $($f.FullName) last_write=$($f.LastWriteTime)"
        } elseif ($known[$key] -ne $stamp) {
          $known[$key] = $stamp
          Write-Log "report updated: $($f.FullName) last_write=$($f.LastWriteTime)"
        }
      }
    }
  } catch {
    Write-Log "watcher error: $($_.Exception.Message)"
  }
  Start-Sleep -Seconds $IntervalSeconds
}
