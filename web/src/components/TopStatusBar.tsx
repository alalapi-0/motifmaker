import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, ConfigPublicResponse, HealthResponse, configPublic, healthz, version } from "../api";
import { useI18n } from "../hooks/useI18n";

export interface TopStatusBarProps {
  busy: boolean; // 当任意请求在执行时置为 true，用于显示“运行中”。
  lastError: string | null; // 最近一次错误文案，展示在状态条中便于排查。
  theme: "light" | "dark"; // 当前主题，供切换按钮展示状态。
  onThemeChange: (theme: "light" | "dark") => void; // 通知上层切换主题并持久化。
}

/**
 * TopStatusBar 组件：展示后端健康状态、版本信息、接口地址以及主题切换。
 * 设计重点：
 * 1. useEffect 内部执行 30 秒轮询，并在返回函数中清理定时器与 AbortController，避免内存泄漏；
 * 2. 利用 useRef 记录组件是否已卸载，防止异步请求返回后再 setState；
 * 3. 语言切换暂时下线，仅展示固定“English Only”提示；未来可恢复多语言时再启用下拉框。
 */
const TopStatusBar: React.FC<TopStatusBarProps> = ({ busy, lastError, theme, onThemeChange }) => {
  const { t } = useI18n();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [versionInfo, setVersionInfo] = useState<string | null>(null);
  const [publicConfig, setPublicConfig] = useState<ConfigPublicResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState<string | null>(null);
  const mountedRef = useRef(true); // 记录组件挂载状态，避免卸载后更新。
  const controllerRef = useRef<AbortController | null>(null); // 保存最近一次请求的 AbortController。

  const fetchStatus = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    // 若已有请求在进行，先主动取消避免竞态数据覆盖。
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      const [healthResult, versionResult, configResult] = await Promise.all([
        healthz(controller.signal),
        version(controller.signal),
        configPublic(controller.signal),
      ]);
      if (!mountedRef.current) return;
      setHealth(healthResult);
      setVersionInfo(versionResult.version);
      setPublicConfig(configResult);
    } catch (error) {
      if (!mountedRef.current) return;
      setHealthError((error as Error).message);
    } finally {
      if (mountedRef.current) {
        setHealthLoading(false);
      }
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

  const backendStatus = useMemo(() => {
    if (healthLoading) {
      return t("status.healthChecking");
    }
    if (healthError) {
      return t("status.healthError");
    }
    if (health) {
      return t("status.backendHealthy");
    }
    return t("status.backendIssue");
  }, [health, healthError, healthLoading, t]);

  const busyText = busy ? t("status.running") : t("status.idle");

  const lastChecked = useMemo(() => {
    if (!health) return "--";
    const date = new Date(health.ts);
    return date.toLocaleTimeString();
  }, [health]);

  return (
    <header
      className="border-b border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
      aria-live="polite"
    >
      <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-4 px-4 py-3 text-xs sm:text-sm">
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300">
            {busyText}
          </span>
          <span className="text-slate-500 dark:text-slate-400">{backendStatus}</span>
          {healthError && (
            <span className="rounded bg-amber-500/20 px-2 py-1 text-amber-700 dark:bg-amber-500/30 dark:text-amber-200">
              {healthError}
            </span>
          )}
          {lastError && (
            <span className="rounded bg-red-500/20 px-2 py-1 text-red-600 dark:bg-red-500/30 dark:text-red-200">
              {lastError}
            </span>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-1 sm:flex-row sm:items-center sm:justify-center sm:gap-3">
          <span>
            {t("status.version")}: {versionInfo ?? "--"}
          </span>
          <span>
            {t("status.environment")}: {API_BASE}
          </span>
          <span>
            {t("status.lastChecked")}: {lastChecked}
          </span>
        </div>

        <div className="flex flex-1 flex-wrap items-center justify-end gap-2">
          {publicConfig && (
            <span className="hidden text-slate-500 sm:inline dark:text-slate-400">
              {publicConfig.allowed_origins.join(", ")}
            </span>
          )}
          <button
            type="button"
            onClick={() => fetchStatus()}
            className="rounded border border-slate-300 px-2 py-1 text-slate-700 transition hover:border-slate-400 hover:text-slate-900 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
          >
            {t("status.refresh")}
          </button>
          <div className="flex items-center gap-2">
            <span className="text-slate-500 dark:text-slate-400">{t("status.language")}</span>
            {/* 当前版本固定为英文模式，未来如需多语言支持，可重新启用语言切换开关。*/}
            <span className="text-sm opacity-70">{t("status.englishOnly")}</span>
          </div>
          <label className="flex items-center gap-2">
            <span className="text-slate-500 dark:text-slate-400">{t("status.theme")}</span>
            <sl-switch
              checked={theme === "dark"}
              aria-label={theme === "dark" ? t("status.themeDark") : t("status.themeLight")}
              onSlChange={(event: CustomEvent) => {
                const target = event.target as HTMLInputElement;
                onThemeChange(target.checked ? "dark" : "light");
              }}
            ></sl-switch>
          </label>
        </div>
      </div>
    </header>
  );
};

export default TopStatusBar;
