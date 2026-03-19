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
& $PythonExe -m pip install pyinstaller | Out-Host

Write-Host "==> 安装后端依赖"
& $PythonExe -m pip install -r (Join-Path $backendDir "requirements.txt") | Out-Host

Write-Host "==> 安装 Playwright Chromium 到桌面资源目录"
$env:PLAYWRIGHT_BROWSERS_PATH = $playwrightDir
& $PythonExe -m playwright install chromium | Out-Host

Write-Host "==> 构建 Python 后端可执行程序"
Push-Location $backendDir
try {
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
        desktop_entry.py | Out-Host
}
finally {
    Pop-Location
}

Write-Host "==> 复制后端资源"
Copy-Item (Join-Path $distDir "EasygetBackend") (Join-Path $resourceRoot "EasygetBackend") -Recurse -Force

Write-Host "后端桌面资源已生成: $resourceRoot"
