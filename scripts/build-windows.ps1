param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

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

Write-Host "==> 构建前端"
Push-Location (Join-Path $repoRoot "frontend")
try {
    Invoke-NativeStep "前端依赖安装" { npm install }
    Invoke-NativeStep "前端构建" { npm run build }
}
finally {
    Pop-Location
}

Write-Host "==> 构建后端桌面资源"
Invoke-NativeStep "后端桌面资源构建" {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build-backend.ps1") -PythonExe $PythonExe
}

Write-Host "==> 安装桌面打包依赖"
Push-Location $repoRoot
try {
    Invoke-NativeStep "桌面打包依赖安装" { npm install }
    Invoke-NativeStep "Electron 安装包构建" { npx electron-builder --win nsis --x64 }
}
finally {
    Pop-Location
}

Write-Host "Windows 安装包输出目录: $(Join-Path $repoRoot 'release')"
