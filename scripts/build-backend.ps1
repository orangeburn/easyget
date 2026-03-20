param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$resourceRoot = Join-Path $repoRoot "desktop-resources\backend"
$playwrightDir = Join-Path $resourceRoot "ms-playwright"
$distDir = Join-Path $backendDir "dist-desktop"
$buildDir = Join-Path $backendDir "build-desktop"
$specDir = Join-Path $backendDir "build-spec"
$backendOutputDir = Join-Path $distDir "EasygetBackend"
$backendExe = Join-Path $backendOutputDir "EasygetBackend.exe"

function Invoke-NativeStep {
    param(
        [string]$StepName,
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$StepName 失败，退出码: $LASTEXITCODE"
    }
}

Write-Host "==> 清理旧的后端打包产物"
if (Test-Path $resourceRoot) {
    Remove-Item $resourceRoot -Recurse -Force
}
if (Test-Path $distDir) {
    Remove-Item $distDir -Recurse -Force
}
if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}
if (Test-Path $specDir) {
    Remove-Item $specDir -Recurse -Force
}

New-Item -ItemType Directory -Path $resourceRoot | Out-Null

Write-Host "==> 安装 PyInstaller"
Invoke-NativeStep "安装 PyInstaller" { & $PythonExe -m pip install pyinstaller }

Write-Host "==> 安装后端依赖"
Invoke-NativeStep "安装后端依赖" { & $PythonExe -m pip install -r (Join-Path $backendDir "requirements.txt") }

Write-Host "==> 安装 Playwright Chromium 到桌面资源目录"
$env:PLAYWRIGHT_BROWSERS_PATH = $playwrightDir
Invoke-NativeStep "安装 Playwright Chromium" { & $PythonExe -m playwright install chromium }

Write-Host "==> 构建 Python 后端可执行程序"
Push-Location $backendDir
try {
    Invoke-NativeStep "PyInstaller 打包" {
        & $PythonExe -m PyInstaller `
            --noconfirm `
            --clean `
            --onedir `
            --name EasygetBackend `
            --distpath $distDir `
            --workpath $buildDir `
            --specpath $specDir `
            --paths $backendDir `
            --collect-submodules app `
            --collect-all playwright `
            --collect-all playwright_stealth `
            --hidden-import uvicorn.logging `
            --hidden-import uvicorn.loops.auto `
            --hidden-import uvicorn.protocols.http.auto `
            --hidden-import uvicorn.protocols.websockets.auto `
            --hidden-import uvicorn.lifespan.on `
            desktop_entry.py
    }
}
finally {
    Pop-Location
}

Write-Host "==> 复制后端资源"
if (-not (Test-Path $backendExe)) {
    throw "后端可执行文件不存在: $backendExe"
}

Copy-Item $backendOutputDir (Join-Path $resourceRoot "EasygetBackend") -Recurse -Force

Write-Host "后端桌面资源已生成: $resourceRoot"
