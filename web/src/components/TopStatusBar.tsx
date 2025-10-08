import React, { useCallback, useEffect, useRef, useState } from "react";
import { healthz, version } from "../api"; // 仅保留健康检查与版本接口，隐藏其他调试信息。

export interface TopStatusBarProps {
  busy: boolean; // 保留接口以兼容现有调用，但 UI 不再展示运维细节。
  lastError: string | null; // 保留接口以兼容现有调用，但 UI 不再展示运维细节。
  theme: "light" | "dark"; // 保留接口以兼容现有调用，但 UI 不再展示运维细节。
  onThemeChange: (theme: "light" | "dark") => void; // 保留接口以兼容现有调用，但 UI 不再展示运维细节。
}

/**
 * TopStatusBar 组件：仅向终端用户展示系统可用性与版本号，隐藏所有运维细节。
 * 设计重点：
 * 1. useEffect 内部执行 30 秒轮询，并在返回函数中清理定时器与 AbortController，避免内存泄漏；
 * 2. 利用 useRef 记录组件是否已卸载，防止异步请求返回后再 setState；
 * 3. UI 只包含在线状态点与版本文本，其余调试字段仅在内部调用链使用。
 */
const TopStatusBar: React.FC<TopStatusBarProps> = () => {
  const [isOnline, setIsOnline] = useState(false); // 仅记录是否在线，终端用户无需看到更多运维细节。
  const [versionInfo, setVersionInfo] = useState<string | null>(null); // 记录后端版本号，展示给用户确认服务版本。
  const mountedRef = useRef(true); // 记录组件挂载状态，避免卸载后更新。
  const controllerRef = useRef<AbortController | null>(null); // 保存最近一次请求的 AbortController。

  const fetchStatus = useCallback(async () => {
    // 若已有请求在进行，先主动取消避免竞态数据覆盖，保持状态点准确。
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      // 仅拉取健康检查与版本信息，作为在线状态与版本号的唯一数据源。
      const [healthResult, versionResult] = await Promise.all([
        healthz(controller.signal),
        version(controller.signal),
      ]);
      if (!mountedRef.current) return;
      setIsOnline(Boolean(healthResult.ok)); // 健康检查成功即视为在线，UI 仅需呈现可用性。
      setVersionInfo(versionResult.version); // 版本号供用户识别部署版本，不暴露其他配置。
    } catch (error) {
      if (!mountedRef.current) return;
      setIsOnline(false); // 请求失败时标记为离线，避免界面出现调试细节。
    } finally {
      controllerRef.current = null;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    // 首次挂载时主动拉取一次，随后每 30 秒轮询一次。
    let cancelled = false;
    const run = async () => {
      await fetchStatus();
    };
    run();

    const interval = window.setInterval(() => {
      if (!cancelled) {
        fetchStatus();
      }
    }, 30000);

    return () => {
      cancelled = true;
      mountedRef.current = false;
      controllerRef.current?.abort();
      window.clearInterval(interval);
    };
  }, [fetchStatus]);

  const statusDotClass = isOnline
    ? "bg-emerald-500 dark:bg-emerald-400"
    : "bg-slate-400 dark:bg-slate-500"; // 根据在线状态决定颜色组合，仅突出可用性结果。

  return (
    <header
      className="border-b border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
      aria-live="polite"
    >
      {/* 外层容器延续原有排版，但仅呈现在线状态与版本号。 */}
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3 text-xs sm:text-sm">
        <div className="flex items-center gap-2">
          {/* 单一状态点与文案，体现“仅展示可用性”这一运维约束。 */}
          <span className="flex items-center gap-2 rounded-full bg-slate-200/60 px-3 py-1 dark:bg-slate-800/60">
            <span className={`inline-block h-2 w-2 rounded-full ${statusDotClass}`} />
            <span className="font-medium text-slate-700 dark:text-slate-200">{isOnline ? "Online" : "Offline"}</span>
          </span>
        </div>
        <span className="text-slate-500 dark:text-slate-400">
          {/* 版本号直接展示为 v{version}，便于用户识别当前部署版本。 */}
          v{versionInfo ?? "--"}
        </span>
      </div>
    </header>
  );
};

export default TopStatusBar;
