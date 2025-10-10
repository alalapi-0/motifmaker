import { app, BrowserWindow, dialog, ipcMain, protocol, session, shell } from 'electron';
import path from 'path';
import fs from 'fs';
import { backendManager } from './backend';
import { buildCsp } from './csp';
import { backendPort, devServerUrl, isDev, resolveWebDistPath } from './env';

let mainWindow: BrowserWindow | null = null;
let quitting = false;

/**
 * 中文注释：限制外部网络请求，确保渲染进程只能与本机后端通信；
 * 开发模式下额外允许访问 Vite Dev Server，以支持热更新资源与 HMR WebSocket。
 */
function setupRequestWhitelist() {
  const sess = session.defaultSession;
  const allowedOrigins = new Set<string>([`127.0.0.1:${backendPort}`]);
  if (isDev) {
    try {
      const devUrl = new URL(devServerUrl);
      allowedOrigins.add(`${devUrl.hostname}:${devUrl.port}`);
      if (devUrl.hostname === 'localhost') {
        allowedOrigins.add(`127.0.0.1:${devUrl.port}`);
      }
    } catch (error) {
      console.warn('Dev server url parse failed', error);
    }
  }
  sess.webRequest.onBeforeRequest((details, callback) => {
    const { url } = details;
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('ws://') || url.startsWith('wss://')) {
      try {
        const parsed = new URL(url);
        const originKey = `${parsed.hostname}:${parsed.port || (parsed.protocol === 'https:' || parsed.protocol === 'wss:' ? '443' : '80')}`;
        if (!allowedOrigins.has(originKey)) {
          console.warn('Blocked request to', url);
          callback({ cancel: true });
          return;
        }
      } catch (error) {
        console.warn('Failed to parse url', url, error);
        callback({ cancel: true });
        return;
      }
    }
    callback({ cancel: false });
  });
}

/**
 * 中文注释：注册 app:// 自定义协议，将请求映射到打包后的 web-dist 静态资源目录，
 * 避免在生产环境依赖本地 http 服务，减少攻击面。
 */
function registerProductionProtocol() {
  if (isDev) {
    return;
  }
  protocol.registerFileProtocol('app', (request, callback) => {
    try {
      const url = new URL(request.url);
      let relativePath = decodeURIComponent(url.pathname);
      if (!relativePath || relativePath === '/' || relativePath === '//') {
        relativePath = '/index.html';
      }
      const sanitizedPath = path.normalize(relativePath).replace(/^\/+/, '');
      const baseDir = resolveWebDistPath(__dirname);
      const fullPath = path.join(baseDir, sanitizedPath);
      callback({ path: fullPath });
    } catch (error) {
      console.error('Failed to resolve app protocol url', request.url, error);
      callback({ error: -6 });
    }
  });
}

/**
 * 中文注释：创建主窗口并加载前端；在生产环境使用自定义协议，在开发环境连接 Vite。
 */
async function createWindow() {
  try {
    await backendManager.ensureStarted();
  } catch (error) {
    console.error('Backend failed to start', error);
    dialog.showErrorBox('Backend not ready', '后端未能正常启动，应用将退出。请检查 Python 依赖或端口占用后重试。');
    app.quit();
    return;
  }

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    backgroundColor: '#0b0b0b',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true
    }
  });

  mainWindow.on('ready-to-show', () => {
    // 中文注释：等待页面资源准备完毕再显示窗口，避免白屏闪烁。
    mainWindow?.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));

  if (isDev) {
    await mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    const indexUrl = 'app://index.html';
    await mainWindow.loadURL(indexUrl);
  }
}

/**
 * 中文注释：为所有响应注入 CSP 头，确保渲染进程遵循我们定义的安全策略。
 */
function setupCsp() {
  const policy = buildCsp(backendPort, isDev ? devServerUrl : undefined);
  const sess = session.defaultSession;
  sess.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = {
      ...details.responseHeaders,
      'Content-Security-Policy': [policy]
    } as Record<string, string[]>;
    // 中文注释：类型定义仅接受字符串，为保留数组写法在此断言为 any，实际运行时行为保持不变。
    callback({ responseHeaders: responseHeaders as any });
  });
}

/**
 * 中文注释：注册 IPC 通道，让渲染进程在严格隔离的前提下访问必要信息。
 */
function registerIpcHandlers() {
  ipcMain.handle('mm:get-version', () => app.getVersion());
  ipcMain.handle('mm:open-logs', async () => {
    const logDir = app.getPath('logs');
    // 中文注释：确保目录存在后再调用 shell.openPath，避免部分系统上返回错误。
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    await shell.openPath(logDir);
    return logDir;
  });
}

app.whenReady().then(async () => {
  setupRequestWhitelist();
  setupCsp();
  registerIpcHandlers();
  registerProductionProtocol();
  await createWindow();

  app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // 中文注释：macOS 遵循原生习惯保留菜单栏，其余平台直接退出。
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', (event) => {
  if (quitting) {
    return;
  }
  event.preventDefault();
  quitting = true;
  backendManager
    .stop()
    .catch((error) => {
      console.error('Failed to stop backend gracefully', error);
    })
    .finally(() => {
      app.exit();
    });
});

process.on('exit', () => {
  // 中文注释：兜底逻辑，防止异常崩溃时后端遗留。
  backendManager.stop().catch(() => undefined);
});
