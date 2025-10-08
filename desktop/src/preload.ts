import { contextBridge, ipcRenderer } from 'electron';

/**
 * 中文注释：通过 contextBridge 暴露受限 API，避免直接开放 Node 能力导致的远程代码执行风险。
 * 仅提供读取版本号、检测运行环境与打开日志目录三个能力，满足前端调试需求。
 */
const api = {
  /**
   * 中文注释：读取主进程传来的应用版本号，前端可在设置页面展示。
   */
  getVersion: () => ipcRenderer.invoke('mm:get-version'),
  /**
   * 中文注释：返回桌面端的提供者信息，用于区分浏览器/PWA 与 Electron。
   */
  getProvider: () => 'electron',
  /**
   * 中文注释：请求主进程打开日志目录，便于用户提交调试信息。
   */
  openLogs: () => ipcRenderer.invoke('mm:open-logs')
};

contextBridge.exposeInMainWorld('mm', api);
