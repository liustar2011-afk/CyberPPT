$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
python tools/bootstrap.py --backend auto
python tools/doctor.py
Write-Host "Ready. Example: python enhance.py page.png"
