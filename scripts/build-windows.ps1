param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "==> 构建前端"
Push-Location (Join-Path $repoRoot "frontend")
try {
    npm install | Out-Host
    npm run build | Out-Host
}
finally {
    Pop-Location
}

Write-Host "==> 构建后端桌面资源"
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build-backend.ps1") -PythonExe $PythonExe | Out-Host

Write-Host "==> 安装桌面打包依赖"
Push-Location $repoRoot
try {
    npm install | Out-Host
    npx electron-builder --win nsis --x64 | Out-Host
}
finally {
    Pop-Location
}

Write-Host "Windows 安装包输出目录: $(Join-Path $repoRoot 'release')"
