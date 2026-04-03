param(
  [string]$Host = "106.54.2.9",
  [string]$User = "ubuntu",
  [string]$KeyPath = "$env:USERPROFILE\.ssh\txssh2.pem"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
  throw "SSH key not found: $KeyPath"
}

$remoteCmd = "sudo bash /opt/gewuxueshu/scripts/update_prod_server.sh"
ssh -i "$KeyPath" "$User@$Host" $remoteCmd

