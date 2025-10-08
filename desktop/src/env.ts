import path from 'path';

/**
 * 中文注释：isDev 用于识别当前是否运行在开发模式下，便于主进程决定加载本地 Vite 服务或打包后的静态文件。
 * 判断逻辑：命令行带 --dev 或环境变量 NODE_ENV=development 时视为开发模式。
 */
export const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

/**
 * 中文注释：后端默认监听 127.0.0.1:8000，保持回环地址以避免暴露到局域网；
 * 允许通过环境变量覆盖端口，方便排查冲突。
 */
export const backendPort = Number(process.env.MM_BACKEND_PORT || 8000);

/**
 * 中文注释：开发模式下 Electron 渲染进程直接访问 Vite Dev Server，便于热更新；
 * 生产模式下则使用 app:// 自定义协议加载打包后的 web/dist 静态文件。
 */
export const devServerUrl = process.env.MM_DEV_SERVER_URL || 'http://localhost:5173';

/**
 * 中文注释：该路径在生产模式下指向打包后的 web 静态资源目录。
 * Electron Builder 会将 web/dist 拷贝到 desktop/dist 同级目录的 web-dist 中。
 */
export function resolveWebDistPath(currentDir: string): string {
  return path.resolve(currentDir, '../web-dist');
}

/**
 * 中文注释：开发脚本提供了 MM_ELECTRON_SKIP_BACKEND=1，用于在 uvicorn --reload 已由外部进程启动时跳过内置后端管理。
 */
export const skipBackendSpawn = process.env.MM_ELECTRON_SKIP_BACKEND === '1' || process.env.MM_ELECTRON_SKIP_BACKEND === 'true';
