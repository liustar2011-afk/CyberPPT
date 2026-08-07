param(
  [ValidateSet('User','Repo','LegacyCodex')]
  [string]$Scope = 'User'
)
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($Scope -eq 'User') { $Target = Join-Path $HOME '.agents\skills\word-to-ppt-script' }
elseif ($Scope -eq 'Repo') { $Target = Join-Path (Get-Location) '.agents\skills\word-to-ppt-script' }
else { $Target = Join-Path $HOME '.codex\skills\word-to-ppt-script' }
if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
Copy-Item -Recurse -Force $Root $Target
$Tests = Join-Path $Target 'tests'
if (Test-Path $Tests) { Remove-Item -Recurse -Force $Tests }
Write-Output $Target
