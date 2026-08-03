$ErrorActionPreference = "Stop"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DestDir = Join-Path $HOME ".agents\skills\source-to-ppt-script"
if (Test-Path $DestDir) { Remove-Item -Recurse -Force $DestDir }
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
@("SKILL.md", "LICENSE.txt", "agents", "scripts", "references", "assets") | ForEach-Object {
    Copy-Item -Recurse -Force (Join-Path $SourceDir $_) $DestDir
}
Write-Host "Installed to $DestDir"
Write-Host "Restart Codex if the skill does not appear immediately."
