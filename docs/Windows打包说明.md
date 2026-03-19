# Easyget Windows 打包说明

## 目标产物
- Windows 安装包（`NSIS`）
- 安装后双击即可启动 `Easyget`
- 应用会自动拉起内置后端，不需要用户手动开两个终端

## 打包方案
- 前端：`Vite + React` 先构建为静态资源
- 后端：`FastAPI` 使用 `PyInstaller` 打包为 `EasygetBackend.exe`
- 桌面壳：`Electron`
- 浏览器运行时：将 `Playwright Chromium` 一并放入安装包

## 首次准备
1. 安装 Node.js 18+。
2. 安装 Python 3.11 左右版本，并确保 `python` 可在终端执行。
3. 安装前后端依赖：

```powershell
npm run install:frontend
cd backend
python -m pip install -r requirements.txt
cd ..
```

## 一键打包
在项目根目录执行：

```powershell
npm run desktop:build
```

如果你的 Python 命令不是 `python`，可以直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -PythonExe py
```

## 输出位置
- 安装包目录：`release/`
- 后端中间产物：`desktop-resources/backend/`

## 运行机制
- Electron 启动后会先拉起内置后端。
- 后端默认监听 `127.0.0.1:8000`。
- 桌面版数据默认写入当前用户目录下的 `Easyget` 应用数据目录，而不是安装目录。
- `Playwright` 浏览器资源会从安装包自带目录读取，因此本地搜索功能可继续使用。

## 注意事项
- 安装包体积会明显增大，因为包含了 Chromium 浏览器运行时。
- 如果 `8000` 端口被其他程序占用，桌面版启动会失败，需要先释放该端口。
- 杀毒软件可能会对首次打包出的 `exe` 做额外扫描，这属于常见现象。
