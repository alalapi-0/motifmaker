/**
 * 中文注释：集中维护 CSP 字符串，避免在 main.ts 中手写长文本导致难以维护。
 * 策略：仅允许加载自身资源、data URI 图片，网络请求限制为回环地址后端，以降低被恶意页面劫持的风险；
 * 在开发模式下额外允许连接本地 Vite Dev Server 的 WebSocket，以支持热更新。
 */
export function buildCsp(backendPort: number, devServerUrl?: string): string {
  const connectSources = ["'self'", `http://127.0.0.1:${backendPort}`];
  if (devServerUrl) {
    try {
      const url = new URL(devServerUrl);
      connectSources.push(`http://${url.hostname}:${url.port}`);
      connectSources.push(`ws://${url.hostname}:${url.port}`);
    } catch (error) {
      // 中文注释：如果解析失败则忽略，保持生产策略，避免错误 URL 打开额外白名单。
    }
  }
  const directives: string[] = [
    "default-src 'self'",
    "script-src 'self'",
    "img-src 'self' data:",
    `connect-src ${connectSources.join(' ')}`,
    "media-src 'self' blob:",
    "style-src 'self' 'unsafe-inline'"
  ];
  return directives.join('; ');
}
