$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BuildRoot = Join-Path $ProjectRoot "build\package-windows"
$DistRoot = Join-Path $ProjectRoot "dist"
$Venv = Join-Path $BuildRoot "venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$DeploymentRoot = Join-Path $ProjectRoot "deployment"

if (Test-Path $BuildRoot) {
    Remove-Item $BuildRoot -Recurse -Force
}
if (Test-Path $DeploymentRoot) {
    Remove-Item $DeploymentRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null

python -m venv $Venv
& $Python -m pip install --upgrade pip
& $Python -m pip install -e $ProjectRoot
& $Python -m pip install "Nuitka[onefile]"

& $Python -m nuitka `
    (Join-Path $ProjectRoot "deploy_main.py") `
    --follow-imports `
    --enable-plugin=pyside6 `
    --output-dir=$DeploymentRoot `
    --output-filename=MyMediaEditor.exe `
    --onefile `
    --assume-yes-for-downloads `
    --noinclude-qt-translations `
    --include-qt-plugins=multimedia,networkinformation,platforminputcontexts

$Exe = Get-ChildItem `
    -Path $DeploymentRoot `
    -Filter "MyMediaEditor.exe" `
    -File `
    -Recurse | `
    Select-Object -First 1

if ($null -eq $Exe) {
    throw "Nuitka 결과 MyMediaEditor.exe를 찾지 못했습니다."
}

$Version = & $Python -c `
    "import tomllib, pathlib; print(tomllib.loads(pathlib.Path(r'$ProjectRoot\pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"

$PackageDir = Join-Path $BuildRoot "MyMediaEditor-$Version-windows-x64"
New-Item -ItemType Directory -Path $PackageDir | Out-Null
Copy-Item $Exe.FullName (Join-Path $PackageDir "MyMediaEditor.exe")
Copy-Item `
    (Join-Path $ProjectRoot "packaging\windows\README.txt") `
    (Join-Path $PackageDir "README.txt")

$ZipPath = Join-Path $DistRoot "MyMediaEditor-$Version-windows-x64.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath
Write-Host "Created: $ZipPath"
