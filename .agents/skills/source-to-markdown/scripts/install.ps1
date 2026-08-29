param(
    [switch]$Ocr,
    [ValidateSet("pdf", "pptx", "xlsx")]
    [string]$Extra
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Venv = Join-Path $Root ".venv"

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv $Venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv $Venv
} else {
    throw "Python 3.10+ was not found on PATH."
}

$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install markitdown
if ($Ocr) {
    & $VenvPython -m pip install markitdown-ocr openai
} elseif ($Extra) {
    & $VenvPython -m pip install "markitdown[$Extra]"
}

& $VenvPython (Join-Path $Root "scripts\convert.py") --help | Out-Null
Write-Host "Installed source-to-markdown runtime in $Venv"
