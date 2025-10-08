import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PromptPanel from "./components/PromptPanel";
import ParamsPanel from "./components/ParamsPanel";
import FormTable, { RegenerateMode } from "./components/FormTable";
import Player from "./components/Player";
import DownloadBar from "./components/DownloadBar";
import PianoRoll, { PianoRollNote } from "./components/PianoRoll";
import TopStatusBar from "./components/TopStatusBar";
import {
  ParamOverrides,
  ProjectSpec,
  RenderSuccess,
  freezeMotif,
  generate,
  loadProject,
  mergeSpecWithOverrides,
  regenerateSection,
  renderProject,
  resolveAssetUrl,
  saveProject,
} from "./api";
import { useI18n, TranslationKey } from "./hooks/useI18n";
import { Midi } from "@tonejs/midi";

interface RequestState {
  loading: boolean;
  error: string | null;
}

interface AlertMessage {
  id: number;
  message: string;
}

interface LogEntry {
  id: number;
  key: TranslationKey;
  level: "info" | "success" | "error";
  timestamp: number;
  extra?: string;
}

const VIEW_STORAGE_KEY = "motifmaker.viewSettings";
const THEME_STORAGE_KEY = "motifmaker.theme";

const DEFAULT_PROMPT = "城市夜景、温暖而克制、B 段最高张力、现代古典+电子、约2分钟";

/**
 * App 组件：整合前端所有功能模块，管理请求状态与布局。
 * - 左侧为 Prompt 与参数覆盖，右侧包含下载、播放器、Piano-Roll 与段落表格；
 * - 顶部状态条轮询健康信息，底部日志区记录最近操作；
 * - 通过 AbortController 及请求状态避免竞态，保障 UI 可预期。
 */
const App: React.FC = () => {
  const { t, lang } = useI18n();
  const [promptText, setPromptText] = useState(DEFAULT_PROMPT);
  const [baseSpec, setBaseSpec] = useState<ProjectSpec | null>(null); // 后端权威 ProjectSpec，表格编辑直接更新该状态。
  const [lastRender, setLastRender] = useState<RenderSuccess | null>(null); // 最近一次渲染结果，驱动下载与播放器。
  const [overrides, setOverrides] = useState<ParamOverrides>({}); // 参数覆盖集合，下次请求前会合并到 baseSpec。
  const [generateState, setGenerateState] = useState<RequestState>({ loading: false, error: null }); // /generate 状态。
  const [renderState, setRenderState] = useState<RequestState>({ loading: false, error: null }); // 覆盖参数触发的二次渲染状态。
  const [regenerateState, setRegenerateState] = useState<RequestState>({ loading: false, error: null }); // /regenerate-section 状态。
  const [saveState, setSaveState] = useState<RequestState>({ loading: false, error: null }); // /save-project 状态。
  const [loadState, setLoadState] = useState<RequestState>({ loading: false, error: null }); // /load-project 状态。
  const [freezeState, setFreezeState] = useState<RequestState>({ loading: false, error: null }); // /freeze-motif 状态。
  const [alerts, setAlerts] = useState<AlertMessage[]>([]); // Shoelace sl-alert 队列，展示错误提示。
  const alertIdRef = useRef(0);
  const [logs, setLogs] = useState<LogEntry[]>([]); // 最近 10 条操作日志。
  const logIdRef = useRef(0);
  const [jsonCollapsed, setJsonCollapsed] = useState(false);
  const [pianoNotes, setPianoNotes] = useState<PianoRollNote[]>([]); // Piano-Roll 绘制的音符列表。
  const [playbackTime, setPlaybackTime] = useState(0); // 播放器当前秒数。
  const [playerDuration, setPlayerDuration] = useState(0); // 播放器解析到的曲目总长。
  const [pendingSeek, setPendingSeek] = useState<number | null>(null); // 来自 Piano-Roll 的定位请求。
  const [exportingView, setExportingView] = useState(false); // 导出视图设置时的加载状态。

  const initialScale = useMemo(() => {
    if (typeof window === "undefined") return 120;
    try {
      const stored = window.localStorage.getItem(VIEW_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (typeof parsed.pianoScale === "number") {
          return parsed.pianoScale;
        }
      }
    } catch (error) {
      console.warn("failed to read view settings", error);
    }
    return 120;
  }, []); // 读取本地存储的 Piano-Roll 缩放倍率，便于跨会话保持视图。
  const [pianoScale, setPianoScale] = useState<number>(initialScale);

  const initialTheme = useMemo(() => {
    if (typeof window === "undefined") return "dark" as const;
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as "light" | "dark" | null;
    if (stored === "light" || stored === "dark") {
      return stored;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }, []); // 主题默认读取 localStorage，若无记录则依据系统偏好。
  const [theme, setTheme] = useState<"light" | "dark">(initialTheme);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.classList.toggle("dark", theme === "dark");
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    }
  }, [theme]);

  const generateController = useRef<AbortController | null>(null);
  const regenerateController = useRef<AbortController | null>(null);
  const saveController = useRef<AbortController | null>(null);
  const loadController = useRef<AbortController | null>(null);
  const freezeController = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      generateController.current?.abort();
      regenerateController.current?.abort();
      saveController.current?.abort();
      loadController.current?.abort();
      freezeController.current?.abort();
    };
  }, []);

  const showErrorAlert = useCallback((message: string) => {
    // 将错误消息推入 alerts 队列，由 Shoelace sl-alert 展示并允许手动关闭。
    setAlerts((prev) => [...prev, { id: alertIdRef.current++, message }]);
  }, []);

  const appendLog = useCallback(
    (key: TranslationKey, level: "info" | "success" | "error", extra?: string) => {
      // 日志仅保留最近 10 条，存储翻译 key 以便语言切换时自动更新文案。
      setLogs((prev) => [
        {
          id: logIdRef.current++,
          key,
          level,
          timestamp: Date.now(),
          extra,
        },
        ...prev,
      ].slice(0, 10));
    },
    []
  );

  const effectiveSpec = useMemo(() => {
    if (!baseSpec) return null;
    return mergeSpecWithOverrides(baseSpec, overrides);
  }, [baseSpec, overrides]);

  const midiUrl = useMemo(() => resolveAssetUrl(lastRender?.midi ?? null), [lastRender]);
  const jsonUrl = useMemo(() => resolveAssetUrl(lastRender?.spec ?? null), [lastRender]);

  const trackStatsJson = useMemo(() => {
    if (!lastRender) return t("json.empty");
    return JSON.stringify(lastRender.track_stats, null, 2);
  }, [lastRender, t]);

  const projectJson = useMemo(() => {
    if (!effectiveSpec) return "{}";
    return JSON.stringify(effectiveSpec, null, 2);
  }, [effectiveSpec]);

  const isBusy =
    generateState.loading ||
    renderState.loading ||
    regenerateState.loading ||
    saveState.loading ||
    loadState.loading ||
    freezeState.loading;

  const lastErrorMessage =
    generateState.error ||
    renderState.error ||
    regenerateState.error ||
    saveState.error ||
    loadState.error ||
    freezeState.error;

  const handleOverridesChange = useCallback((next: ParamOverrides) => {
    setOverrides(next);
  }, []);

  const handleResetOverrides = useCallback(() => {
    setOverrides({});
  }, []);

  const handleUpdateSection = useCallback(
    (index: number, updates: Partial<ProjectSpec["form"][number]>) => {
      setBaseSpec((prev) => {
        if (!prev) return prev;
        const form = prev.form.map((section, idx) =>
          idx === index ? { ...section, ...updates } : section
        );
        return { ...prev, form };
      });
    },
    []
  );

  const parseMidiForRoll = useCallback(
    async (url: string) => {
      // 解析 MIDI 用于 Piano-Roll 展示，取音符数量最多的轨作为主旋律轨迹。
      try {
        const response = await fetch(url);
        const buffer = await response.arrayBuffer();
        const midi = new Midi(buffer);
        const richestTrack = midi.tracks.reduce((best, track) => {
          if (!best || track.notes.length > best.notes.length) {
            return track;
          }
          return best;
        }, midi.tracks[0]);
        const notes: PianoRollNote[] = (richestTrack?.notes ?? []).map((note) => ({
          pitch: note.midi,
          start: note.time,
          duration: note.duration,
          velocity: note.velocity,
        }));
        setPianoNotes(notes);
        setPlayerDuration(midi.duration);
      } catch (error) {
        console.error("failed to parse midi for piano roll", error);
        appendLog("log.midiParseError", "error");
        showErrorAlert(t("player.error"));
      }
    },
    [appendLog, showErrorAlert, t]
  );

  useEffect(() => {
    const url = midiUrl;
    if (!url) {
      setPianoNotes([]);
      setPlayerDuration(0); // 清空可视化时也重置时长，避免显示旧数据。
      setPlaybackTime(0);
      return;
    }
    parseMidiForRoll(url);
  }, [midiUrl, parseMidiForRoll]);

  const handleGenerate = useCallback(async () => {
    // 一键生成：若存在历史请求则取消，通过 overrides 判断是否需要额外渲染。
    generateController.current?.abort();
    const controller = new AbortController();
    generateController.current = controller;
    setGenerateState({ loading: true, error: null });
    appendLog("log.generateStart", "info");
    try {
      const result = await generate(promptText, controller.signal);
      if (controller.signal.aborted) return;
      appendLog("log.generateSuccess", "success");
      setBaseSpec(result.project);
      setLastRender(result);
      if (Object.keys(overrides).length > 0) {
        setRenderState({ loading: true, error: null });
        const merged = mergeSpecWithOverrides(result.project, overrides);
        try {
          const renderResult = await renderProject(merged, controller.signal);
          if (controller.signal.aborted) {
            setRenderState({ loading: false, error: null });
            return;
          }
          setBaseSpec(renderResult.project);
          setLastRender(renderResult);
          appendLog("log.renderOverride", "info");
          setRenderState({ loading: false, error: null });
        } catch (error) {
          if ((error as Error).name === "AbortError") return;
          const message = (error as Error).message;
          setRenderState({ loading: false, error: message });
          appendLog("log.renderError", "error", message);
          showErrorAlert(message);
        }
      } else {
        setRenderState({ loading: false, error: null });
      }
    } catch (error) {
      if ((error as Error).name === "AbortError") return;
      const message = (error as Error).message;
      setGenerateState({ loading: false, error: message });
      appendLog("log.generateError", "error", message);
      showErrorAlert(message);
      return;
    } finally {
      if (!controller.signal.aborted) {
        setGenerateState((prev) => ({ ...prev, loading: false }));
      }
    }
  }, [appendLog, overrides, promptText, showErrorAlert]);

  const handleRegenerateSection = useCallback(
    async (index: number, mode: RegenerateMode) => {
      // 局部再生成：合并参数覆盖并根据模式决定是否保留动机，使用 AbortController 避免竞态。
      if (!baseSpec) return;
      regenerateController.current?.abort();
      const controller = new AbortController();
      regenerateController.current = controller;
      setRegenerateState({ loading: true, error: null });
      appendLog("log.regenerateStart", "info");
      try {
        const specForRequest = mergeSpecWithOverrides(baseSpec, overrides);
        const keepMotif = mode === "melody";
        const result = await regenerateSection(
          specForRequest,
          index,
          keepMotif,
          controller.signal
        );
        if (controller.signal.aborted) return;
        setBaseSpec(result.project);
        setLastRender(result);
        appendLog("log.regenerateSuccess", "success");
        setRegenerateState({ loading: false, error: null });
      } catch (error) {
        if ((error as Error).name === "AbortError") return;
        const message = (error as Error).message;
        setRegenerateState({ loading: false, error: message });
        appendLog("log.regenerateError", "error", message);
        showErrorAlert(message);
        return;
      } finally {
        if (!controller.signal.aborted) {
          setRegenerateState((prev) => ({ ...prev, loading: false }));
        }
      }
    },
    [appendLog, baseSpec, overrides, showErrorAlert]
  );

  const handleFreezeMotifs = useCallback(
    async (motifTags: string[]) => {
      // 批量冻结动机：提交当前覆盖后的 ProjectSpec 与勾选的标签。
      if (!baseSpec || motifTags.length === 0) return;
      freezeController.current?.abort();
      const controller = new AbortController();
      freezeController.current = controller;
      setFreezeState({ loading: true, error: null });
      appendLog("log.freezeStart", "info");
      try {
        const specForRequest = mergeSpecWithOverrides(baseSpec, overrides);
        const result = await freezeMotif(specForRequest, motifTags, controller.signal);
        if (controller.signal.aborted) return;
        setBaseSpec(result.project);
        appendLog("log.freezeSuccess", "success");
        setFreezeState({ loading: false, error: null });
      } catch (error) {
        if ((error as Error).name === "AbortError") return;
        const message = (error as Error).message;
        setFreezeState({ loading: false, error: message });
        appendLog("log.freezeError", "error", message);
        showErrorAlert(message);
        return;
      } finally {
        if (!controller.signal.aborted) {
          setFreezeState((prev) => ({ ...prev, loading: false }));
        }
      }
    },
    [appendLog, baseSpec, overrides, showErrorAlert]
  );

  const handleSaveProject = useCallback(
    async (name: string) => {
      // 保存工程：合并覆盖后写入服务器 projects/ 目录。
      if (!baseSpec) return;
      saveController.current?.abort();
      const controller = new AbortController();
      saveController.current = controller;
      setSaveState({ loading: true, error: null });
      appendLog("log.saveStart", "info");
      try {
        const payload = mergeSpecWithOverrides(baseSpec, overrides);
        await saveProject(payload, name, controller.signal);
        if (controller.signal.aborted) return;
        appendLog("log.saveSuccess", "success", name);
        setSaveState({ loading: false, error: null });
      } catch (error) {
        if ((error as Error).name === "AbortError") return;
        const message = (error as Error).message;
        setSaveState({ loading: false, error: message });
        appendLog("log.saveError", "error", message);
        showErrorAlert(message);
        return;
      } finally {
        if (!controller.signal.aborted) {
          setSaveState((prev) => ({ ...prev, loading: false }));
        }
      }
    },
    [appendLog, baseSpec, overrides, showErrorAlert]
  );

  const handleLoadProject = useCallback(
    async (name: string) => {
      // 载入工程：读取服务器端 JSON 并覆盖本地状态，同时清空当前渲染。
      loadController.current?.abort();
      const controller = new AbortController();
      loadController.current = controller;
      setLoadState({ loading: true, error: null });
      appendLog("log.loadStart", "info", name);
      try {
        const result = await loadProject(name, controller.signal);
        if (controller.signal.aborted) return;
        setBaseSpec(result.project);
        setLastRender(null);
        appendLog("log.loadSuccess", "success", name);
        setLoadState({ loading: false, error: null });
      } catch (error) {
        if ((error as Error).name === "AbortError") return;
        const message = (error as Error).message;
        setLoadState({ loading: false, error: message });
        appendLog("log.loadError", "error", message);
        showErrorAlert(message);
        return;
      } finally {
        if (!controller.signal.aborted) {
          setLoadState((prev) => ({ ...prev, loading: false }));
        }
      }
    },
    [appendLog, showErrorAlert]
  );

  const handleExportView = useCallback(async () => {
    // 导出视图设置：写入 Piano-Roll 缩放、主题与语言到 localStorage，便于再次加载。
    if (typeof window === "undefined") return;
    setExportingView(true);
    try {
      const payload = {
        pianoScale,
        theme,
        lang,
      };
      window.localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify(payload));
      appendLog("log.viewSaved", "success");
    } finally {
      setExportingView(false);
    }
  }, [appendLog, lang, pianoScale, theme]);

  const handlePlayerProgress = useCallback((time: number) => {
    setPlaybackTime(time);
  }, []);

  const handlePlayerDuration = useCallback((durationValue: number) => {
    setPlayerDuration(durationValue);
  }, []);

  const handleSeekFromRoll = useCallback((time: number) => {
    setPendingSeek(time);
    setPlaybackTime(time);
  }, []);

  const handleAlertClose = useCallback((id: number) => {
    setAlerts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  return (
    <div
      className={
        theme === "dark"
          ? "flex min-h-screen flex-col bg-slate-950 text-slate-100"
          : "flex min-h-screen flex-col bg-slate-100 text-slate-900"
      }
    >
      <TopStatusBar busy={isBusy} lastError={lastErrorMessage} theme={theme} onThemeChange={setTheme} />
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6">
        <div className="space-y-2">
          {alerts.map((alert) => (
            <sl-alert
              key={alert.id}
              variant="danger"
              open
              closable
              onSlAfterHide={() => handleAlertClose(alert.id)}
            >
              <span slot="icon">⚠️</span>
              {alert.message}
            </sl-alert>
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <div className="space-y-6">
            <PromptPanel
              promptText={promptText}
              onPromptChange={setPromptText}
              onGenerate={handleGenerate}
              loading={generateState.loading || renderState.loading}
            />
            <ParamsPanel
              projectSpec={baseSpec}
              overrides={overrides}
              onOverridesChange={handleOverridesChange}
              onResetOverrides={handleResetOverrides}
              disabled={generateState.loading || renderState.loading}
            />
          </div>
          <div className="space-y-6">
            <DownloadBar
              midiUrl={midiUrl}
              jsonUrl={jsonUrl}
              projectJson={projectJson}
              onSaveProject={handleSaveProject}
              onLoadProject={handleLoadProject}
              onExportView={handleExportView}
              saveLoading={saveState.loading}
              loadLoading={loadState.loading}
              exportLoading={exportingView}
            />
            <Player
              midiUrl={midiUrl}
              onProgress={handlePlayerProgress}
              onDuration={handlePlayerDuration}
              externalSeek={pendingSeek}
              onSeekApplied={() => setPendingSeek(null)}
              onError={(message) => showErrorAlert(message)}
            />
            <PianoRoll
              notes={pianoNotes}
              duration={playerDuration}
              currentTime={playbackTime}
              scale={pianoScale}
              onScaleChange={setPianoScale}
              onSeek={handleSeekFromRoll}
            />
            <FormTable
              projectSpec={effectiveSpec}
              onUpdateSection={handleUpdateSection}
              onRegenerateSection={handleRegenerateSection}
              regenerating={regenerateState.loading}
              onFreezeMotifs={handleFreezeMotifs}
              freezeLoading={freezeState.loading}
            />
            <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 text-xs shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100">
              <header className="flex items-center justify-between">
                <h3 className="font-semibold">{t("json.title")}</h3>
                <button
                  type="button"
                  className="text-xs text-cyan-500 hover:underline"
                  onClick={() => setJsonCollapsed((prev) => !prev)}
                >
                  {jsonCollapsed ? t("json.toggleOpen") : t("json.toggleClose")}
                </button>
              </header>
              {!jsonCollapsed && (
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="rounded border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/60">
                    <h4 className="mb-2 font-medium text-slate-900 dark:text-slate-100">{t("json.trackStats")}</h4>
                    <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-slate-800 dark:text-slate-200">{trackStatsJson}</pre>
                  </div>
                  <div className="rounded border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900/60">
                    <h4 className="mb-2 font-medium text-slate-900 dark:text-slate-100">{t("json.projectSpec")}</h4>
                    <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-slate-800 dark:text-slate-200">{projectJson}</pre>
                  </div>
                </div>
              )}
            </section>
          </div>
        </div>
      </main>
      <footer className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
        <div className="mx-auto w-full max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between gap-2">
            <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("logs.title")}</h4>
            <button
              type="button"
              className="text-xs text-cyan-500 hover:underline"
              onClick={() => setLogs([])}
            >
              {t("logs.clear")}
            </button>
          </div>
          {logs.length === 0 ? (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{t("logs.empty")}</p>
          ) : (
            <ul className="mt-2 space-y-1 text-xs">
              {logs.map((entry) => (
                <li
                  key={entry.id}
                  className={
                    entry.level === "success"
                      ? "text-emerald-500"
                      : entry.level === "error"
                      ? "text-red-500"
                      : "text-slate-600 dark:text-slate-300"
                  }
                >
                  <span className="mr-2 text-[11px] text-slate-400 dark:text-slate-500">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </span>
                  {t(entry.key)}
                  {entry.extra ? `：${entry.extra}` : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </footer>
    </div>
  );
};

export default App;
