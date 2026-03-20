const { app, BrowserWindow, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');
const fs = require('fs');
const net = require('net');
const path = require('path');

let backendProcess = null;
let mainWindow = null;
let isQuitting = false;
let backendStopRequested = false;
let backendPort = null;
let apiBaseUrl = null;
let healthcheckUrl = null;
let backendInstanceToken = null;

if (!app.requestSingleInstanceLock()) {
  app.quit();
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function canListenOnPort(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.on('error', () => resolve(false));
    server.listen(port, '127.0.0.1', () => {
      server.close(() => resolve(true));
    });
  });
}

async function findAvailablePort(preferredPort, attempts = 20) {
  for (let offset = 0; offset < attempts; offset += 1) {
    const candidate = preferredPort + offset;
    // eslint-disable-next-line no-await-in-loop
    if (await canListenOnPort(candidate)) {
      return candidate;
    }
  }
  throw new Error(`无法找到可用端口，起始端口: ${preferredPort}`);
}

function getBundledPlaywrightPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend', 'ms-playwright');
  }
  return path.join(app.getAppPath(), 'desktop-resources', 'backend', 'ms-playwright');
}

function resolveBackendCommand() {
  if (app.isPackaged) {
    const command = path.join(process.resourcesPath, 'backend', 'EasygetBackend', 'EasygetBackend.exe');
    return {
      command,
      args: [],
      cwd: path.dirname(command)
    };
  }

  const command = process.env.PYTHON_PATH || 'python';
  return {
    command,
    args: [path.join(app.getAppPath(), 'backend', 'desktop_entry.py')],
    cwd: app.getAppPath()
  };
}

function stopBackendProcess() {
  if (!backendProcess || backendProcess.killed) {
    return;
  }

  backendStopRequested = true;
  const pid = backendProcess.pid;
  if (process.platform === 'win32' && pid) {
    spawn('taskkill', ['/pid', String(pid), '/T', '/F'], { windowsHide: true });
  } else {
    backendProcess.kill('SIGTERM');
  }

  backendProcess = null;
}

async function waitForBackend(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!backendProcess) {
      throw new Error('后端进程在启动完成前已经退出');
    }

    try {
      const response = await fetch(healthcheckUrl);
      if (response.ok) {
        const payload = await response.json().catch(() => ({}));
        if (payload.instance_token === backendInstanceToken) {
          return;
        }
      }
    } catch (error) {
      // Continue polling until timeout.
    }
    await delay(500);
  }

  throw new Error(`后端服务未能在 ${timeoutMs / 1000} 秒内启动`);
}

async function startBackend() {
  const { command, args, cwd } = resolveBackendCommand();
  const needsFileCheck = app.isPackaged || path.isAbsolute(command) || command.includes(path.sep);
  if (needsFileCheck && !fs.existsSync(command)) {
    throw new Error(`未找到后端启动文件: ${command}`);
  }

  backendStopRequested = false;
  backendPort = await findAvailablePort(Number(process.env.EASYGET_BACKEND_PORT || (app.isPackaged ? 18000 : 8000)));
  apiBaseUrl = `http://127.0.0.1:${backendPort}/api`;
  healthcheckUrl = `http://127.0.0.1:${backendPort}/health`;
  backendInstanceToken = randomUUID();
  process.env.EASYGET_API_BASE_URL = apiBaseUrl;
  process.env.EASYGET_BACKEND_PORT = String(backendPort);
  process.env.EASYGET_INSTANCE_TOKEN = backendInstanceToken;

  const playwrightPath = getBundledPlaywrightPath();
  const env = {
    ...process.env,
    EASYGET_APP_DATA_DIR: app.getPath('userData'),
    EASYGET_BACKEND_PORT: String(backendPort),
    EASYGET_API_BASE_URL: apiBaseUrl,
    EASYGET_INSTANCE_TOKEN: backendInstanceToken
  };
  if (fs.existsSync(playwrightPath)) {
    env.PLAYWRIGHT_BROWSERS_PATH = playwrightPath;
  }

  backendProcess = spawn(command, args, {
    cwd,
    env,
    windowsHide: true,
    stdio: 'ignore'
  });

  backendProcess.on('exit', (code) => {
    backendProcess = null;
    if (!isQuitting && !backendStopRequested) {
      dialog.showErrorBox('Easyget 后端已退出', `后端进程意外退出，退出码: ${code ?? 'unknown'}`);
      app.quit();
    }
  });

  await waitForBackend();
}

function wireExternalLinks(window) {
  window.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  window.webContents.on('will-navigate', (event, url) => {
    const isAppUrl = url.startsWith('file://') || url.startsWith('devtools://');
    if (!isAppUrl) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
}

async function createWindow() {
  const iconPath = path.join(app.getAppPath(), 'logo.png');
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 900,
    minHeight: 760,
    show: false,
    title: 'Easyget',
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [
        `--easyget-api-base-url=${apiBaseUrl || 'http://127.0.0.1:8000/api'}`
      ]
    }
  });

  wireExternalLinks(mainWindow);

  const indexPath = path.join(app.getAppPath(), 'frontend', 'dist', 'index.html');
  await mainWindow.loadFile(indexPath);
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
  mainWindow.on('closed', () => {
    mainWindow = null;
    if (process.platform !== 'darwin') {
      stopBackendProcess();
    }
  });
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    await createWindow();
  } catch (error) {
    dialog.showErrorBox('Easyget 启动失败', String(error instanceof Error ? error.message : error));
    app.quit();
  }
});

app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    await createWindow();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  stopBackendProcess();
});

app.on('will-quit', () => {
  isQuitting = true;
  stopBackendProcess();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopBackendProcess();
    app.quit();
  }
});

process.on('exit', () => {
  stopBackendProcess();
});

process.on('SIGINT', () => {
  stopBackendProcess();
  process.exit(0);
});

process.on('SIGTERM', () => {
  stopBackendProcess();
  process.exit(0);
});
