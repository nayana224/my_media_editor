$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Windows PowerShell does not throw on a nonzero native process exit code.
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE"
    }
}

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildRoot = Join-Path $ProjectRoot "build\package-windows"
$DistRoot = Join-Path $ProjectRoot "dist"
$Venv = Join-Path $BuildRoot "venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$DeploymentRoot = Join-Path $BuildRoot "deployment"
Invoke-Checked python @("-c", "import sys, platform; sys.exit(0 if sys.version_info >= (3, 11) and platform.machine().lower() in ('amd64', 'x86_64') and sys.maxsize > 2**32 else 'Build requires Python 3.11+ x64')")

if (Test-Path $BuildRoot) { Remove-Item $BuildRoot -Recurse -Force }
New-Item -ItemType Directory -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null
Invoke-Checked python @("-m", "venv", $Venv)
Invoke-Checked $Python @("-m", "pip", "install", "-e", $ProjectRoot, "-r", (Join-Path $ProjectRoot "packaging\requirements-build.txt"))
Invoke-Checked $Python @(
    "-m", "nuitka", (Join-Path $ProjectRoot "deploy_main.py"),
    "--enable-plugin=pyside6", "--output-dir=$DeploymentRoot",
    "--output-filename=MyMediaEditor.exe", "--onefile", "--assume-yes-for-downloads",
    "--noinclude-qt-translations", "--nofollow-import-to=imageio_ffmpeg",
    "--include-qt-plugins=multimedia,networkinformation,platforminputcontexts"
)
$Exe = Join-Path $DeploymentRoot "MyMediaEditor.exe"
if (-not (Test-Path $Exe -PathType Leaf)) { throw "Nuitka onefile executable missing: $Exe" }

$Version = & $Python -c "import importlib.metadata; print(importlib.metadata.version('media-editor'))"
if ($LASTEXITCODE -ne 0 -or -not $Version) { throw "Unable to read package version" }
$PackageDir = Join-Path $BuildRoot "MyMediaEditor-$Version-windows-x64"
Invoke-Checked $Python @(
    (Join-Path $ProjectRoot "scripts\bundle_ffmpeg.py"),
    "--platform", "windows-x64", "--destination", $PackageDir,
    "--cache", (Join-Path $ProjectRoot "build\downloads")
)
Copy-Item $Exe (Join-Path $PackageDir "MyMediaEditor.exe")
Copy-Item (Join-Path $ProjectRoot "packaging\windows\README.txt") (Join-Path $PackageDir "README.txt")
$ZipPath = Join-Path $DistRoot "MyMediaEditor-$Version-windows-x64.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath
Write-Host "Created: $ZipPath"
