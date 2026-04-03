param(
  [string]$ServerHost = "106.54.2.9",
  [string]$User = "ubuntu",
  [string]$KeyPath = "$env:USERPROFILE\.ssh\txssh2.pem"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
  throw "SSH key not found: $KeyPath"
}

$remoteCmd = "sudo sed -i 's/\r$//' /opt/gewuxueshu/scripts/update_prod_server.sh && sudo bash /opt/gewuxueshu/scripts/update_prod_server.sh"
ssh -i "$KeyPath" "$User@$ServerHost" $remoteCmd
