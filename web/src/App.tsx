import React, { useCallback, useMemo, useState } from "react";
import PromptPanel from "./components/PromptPanel";
import ParamsPanel from "./components/ParamsPanel";
import FormTable from "./components/FormTable";
import Player from "./components/Player";
import DownloadBar from "./components/DownloadBar";
import {
  GenerateResponse,
  ParamOverrides,
  ProjectSpec,
  generate,
  loadProject,
  regenerateSection,
  resolveAssetUrl,
  saveProject,
} from "./api";

/**
 * App 组件：作为整个前端的状态容器与布局入口。
 * - 负责维护 Prompt 文本、ProjectSpec、最后一次生成的摘要信息等核心状态；
 * - 将参数覆盖与表格编辑后的规格统一提交给后端，避免状态分裂；
 * - 组织左侧的输入面板与右侧的预览/播放器/下载模块。
 */
const App: React.FC = () => {
  const [promptText, setPromptText] = useState(
    "城市夜景、温暖而克制、B 段最高张力、现代古典+电子、约2分钟"
  ); // Prompt 文本，默认提供示例引导。
  const [projectSpec, setProjectSpec] = useState<ProjectSpec | null>(null); // 当前在前端缓存的 ProjectSpec。
  const [lastResult, setLastResult] = useState<GenerateResponse | null>(null); // 最近一次生成/再生返回的摘要信息。
  const [paramOverrides, setParamOverrides] = useState<ParamOverrides>({}); // 用户临时调整的参数覆盖。
  const [isLoading, setIsLoading] = useState(false); // 全局加载状态，控制按钮禁用。
  const [feedback, setFeedback] = useState<{ type: "info" | "error"; message: string } | null>(
    null
  ); // 统一的信息/错误提示。
  const [jsonCollapsed, setJsonCollapsed] = useState(false); // JSON 预览是否折叠，便于在小屏幕上节约空间。

  // 将覆盖参数合并到 ProjectSpec 的帮助函数，后端仍然会做最终校验。
  const mergeSpecWithOverrides = useCallback(
    (spec: ProjectSpec, overrides: ParamOverrides): ProjectSpec => ({
      ...spec,
      tempo_bpm: overrides.tempo_bpm ?? spec.tempo_bpm,
      meter: overrides.meter ?? spec.meter,
      key: overrides.key ?? spec.key,
      mode: overrides.mode ?? spec.mode,
      instrumentation: overrides.instrumentation ?? spec.instrumentation,
      harmony_options: {
        ...(spec.harmony_options ?? {}),
        ...(overrides.harmony_options ?? {}),
      },
    }),
    []
  );

  const handleGenerate = useCallback(async () => {
    setIsLoading(true);
    setFeedback({ type: "info", message: "正在生成骨架，请稍候..." });
    try {
      const response = await generate(promptText, paramOverrides);
      const mergedSpec = mergeSpecWithOverrides(response.project_spec, paramOverrides);
      setProjectSpec(mergedSpec);
      setLastResult(response);
      setFeedback({ type: "info", message: "生成完成，可在右侧查看 JSON 与试听。" });
    } catch (error) {
      setFeedback({ type: "error", message: (error as Error).message });
    } finally {
      setIsLoading(false);
    }
  }, [mergeSpecWithOverrides, paramOverrides, promptText]);

  const handleOverridesChange = useCallback((next: ParamOverrides) => {
    setParamOverrides(next);
    // 若已有 ProjectSpec，则实时更新前端缓存的规格以便预览保持同步。
    setProjectSpec((prev) => (prev ? mergeSpecWithOverrides(prev, next) : prev));
  }, [mergeSpecWithOverrides]);

  const handleUpdateSection = useCallback(
    (index: number, updates: Partial<ProjectSpec["form"][number]>) => {
      setProjectSpec((prev) => {
        if (!prev) return prev;
        const form = prev.form.map((section, idx) =>
          idx === index ? { ...section, ...updates } : section
        );
        return { ...prev, form };
      });
    },
    []
  );

  const handleRegenerateSection = useCallback(
    async (index: number, keepMotif: boolean) => {
      if (!projectSpec) return;
      setIsLoading(true);
      setFeedback({ type: "info", message: "正在局部再生成指定段落..." });
      try {
        const specForRequest = mergeSpecWithOverrides(projectSpec, paramOverrides);
        const response = await regenerateSection(specForRequest, index, keepMotif);
        const mergedSpec = mergeSpecWithOverrides(response.project_spec, paramOverrides);
        setProjectSpec(mergedSpec);
        setLastResult(response);
        setFeedback({ type: "info", message: "局部再生完成，播放器与表格已更新。" });
      } catch (error) {
        setFeedback({ type: "error", message: (error as Error).message });
      } finally {
        setIsLoading(false);
      }
    },
    [mergeSpecWithOverrides, paramOverrides, projectSpec]
  );

  const handleSaveProject = useCallback(
    async (name: string) => {
      if (!projectSpec) {
        setFeedback({ type: "error", message: "当前没有可保存的 ProjectSpec。" });
        return;
      }
      setIsLoading(true);
      setFeedback({ type: "info", message: "正在保存工程到服务器..." });
      try {
        const specForSave = mergeSpecWithOverrides(projectSpec, paramOverrides);
        await saveProject(specForSave, name);
        setFeedback({ type: "info", message: `工程 ${name} 已保存。` });
      } catch (error) {
        setFeedback({ type: "error", message: (error as Error).message });
      } finally {
        setIsLoading(false);
      }
    },
    [mergeSpecWithOverrides, paramOverrides, projectSpec]
  );

  const handleLoadProject = useCallback(
    async (name: string) => {
      setIsLoading(true);
      setFeedback({ type: "info", message: "正在从服务器载入工程..." });
      try {
        const spec = await loadProject(name);
        const mergedSpec = mergeSpecWithOverrides(spec, paramOverrides);
        setProjectSpec(mergedSpec);
        setLastResult(null);
        setFeedback({ type: "info", message: `工程 ${name} 已载入，请手动触发生成以获取最新 MIDI。` });
      } catch (error) {
        setFeedback({ type: "error", message: (error as Error).message });
      } finally {
        setIsLoading(false);
      }
    },
    [mergeSpecWithOverrides, paramOverrides]
  );

  const midiUrl = useMemo(() => resolveAssetUrl(lastResult?.mid_path), [lastResult]);
  const jsonUrl = useMemo(() => resolveAssetUrl(lastResult?.json_path), [lastResult]);

  const trackSummary = useMemo(() => {
    if (!lastResult) return "";
    return JSON.stringify(lastResult.track_stats, null, 2);
  }, [lastResult]);

  const projectJson = useMemo(() => {
    if (!projectSpec) return "{}";
    return JSON.stringify(projectSpec, null, 2);
  }, [projectSpec]);

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        {/* 左侧控制面板：Prompt 输入与参数覆盖 */}
        <div className="space-y-6">
          <PromptPanel
            promptText={promptText}
            onPromptChange={setPromptText}
            onGenerate={handleGenerate}
            loading={isLoading}
          />
          <ParamsPanel
            projectSpec={projectSpec}
            overrides={paramOverrides}
            onOverridesChange={handleOverridesChange}
          />
        </div>

        {/* 右侧内容区：下载/播放器/表格/JSON 预览 */}
        <div className="space-y-6">
          <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
            <DownloadBar
              midiUrl={midiUrl}
              jsonUrl={jsonUrl}
              onSaveProject={handleSaveProject}
              onLoadProject={handleLoadProject}
              loading={isLoading}
            />
            <Player midiUrl={midiUrl} />
          </div>

          <FormTable
            projectSpec={projectSpec}
            onUpdateSection={handleUpdateSection}
            onRegenerateSection={handleRegenerateSection}
          />

          <section className="space-y-3 rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-xs">
            <header className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-200">生成摘要</h3>
              <button
                type="button"
                className="text-xs text-cyan-400 hover:underline"
                onClick={() => setJsonCollapsed((prev) => !prev)}
              >
                {jsonCollapsed ? "展开 JSON" : "折叠 JSON"}
              </button>
            </header>
            <p className="text-slate-400">
              该区域展示 lastResult.track_stats 以及当前 ProjectSpec，便于排查后端结构。
            </p>
            {!jsonCollapsed && (
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-md border border-slate-800 bg-slate-950/60 p-3">
                  <h4 className="mb-2 font-medium text-slate-300">Track Stats</h4>
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-slate-200">
                    {trackSummary || "等待生成..."}
                  </pre>
                </div>
                <div className="rounded-md border border-slate-800 bg-slate-950/60 p-3">
                  <h4 className="mb-2 font-medium text-slate-300">ProjectSpec</h4>
                  <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-slate-200">
                    {projectJson}
                  </pre>
                </div>
              </div>
            )}
          </section>

          {feedback && (
            <div
              className={`rounded-md border p-3 text-xs ${
                feedback.type === "error"
                  ? "border-red-500/60 bg-red-500/10 text-red-200"
                  : "border-cyan-500/60 bg-cyan-500/10 text-cyan-200"
              }`}
            >
              {feedback.message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
