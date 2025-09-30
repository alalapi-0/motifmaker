import React, { useMemo, useState } from "react";
import PromptPanel from "./components/PromptPanel";
import ParamsPanel from "./components/ParamsPanel";
import FormTable from "./components/FormTable";
import Player from "./components/Player";
import DownloadBar from "./components/DownloadBar";
import {
  GenerateOptions,
  ProjectSpec,
  RenderResponse,
  generateFromPrompt,
  regenerateSection,
  freezeMotif,
  saveProject,
  loadProject,
  renderExisting,
} from "./api";

interface ParamState {
  key: string;
  mode: string;
  tempo_bpm: number;
  meter: string;
  instrumentation: string[];
}

const DEFAULT_PARAM_STATE: ParamState = {
  key: "C",
  mode: "major",
  tempo_bpm: 100,
  meter: "4/4",
  instrumentation: ["piano"],
};

const DEFAULT_TRACKS = ["melody", "harmony", "bass", "percussion"];

const App: React.FC = () => {
  const [prompt, setPrompt] = useState("城市夜景 Lo-Fi 学习氛围");
  const [options, setOptions] = useState<GenerateOptions>({});
  const [paramState, setParamState] = useState<ParamState>(DEFAULT_PARAM_STATE);
  const [tracks, setTracks] = useState<string[]>(DEFAULT_TRACKS);
  const [projectSpec, setProjectSpec] = useState<ProjectSpec | null>(null);
  const [renderResult, setRenderResult] = useState<RenderResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const applyParamToSpec = (spec: ProjectSpec, state: ParamState): ProjectSpec => ({
    ...spec,
    key: state.key,
    mode: state.mode,
    tempo_bpm: state.tempo_bpm,
    meter: state.meter,
    instrumentation: state.instrumentation.length
      ? state.instrumentation
      : spec.instrumentation,
  });

  const handleGenerate = async () => {
    setLoading(true);
    setStatus("正在生成骨架...");
    try {
      const response = await generateFromPrompt(prompt, {
        ...options,
        emit_midi: true,
        tracks,
      });
      const adjusted = applyParamToSpec(response.project, paramState);
      setProjectSpec(adjusted);
      setRenderResult(response);
      setStatus("生成完成，可进一步编辑。");
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleParamChange = (updates: Partial<ParamState>) => {
    const nextState = { ...paramState, ...updates };
    setParamState(nextState);
    if (projectSpec) {
      setProjectSpec(applyParamToSpec(projectSpec, nextState));
    }
  };

  const handleOptionsChange = (updates: Partial<GenerateOptions>) => {
    setOptions((prev) => ({ ...prev, ...updates }));
  };

  const handleSectionUpdate = (
    index: number,
    updates: { bars?: number; tension?: number; motif_label?: string }
  ) => {
    if (!projectSpec) return;
    const form = projectSpec.form.map((section, idx) => {
      if (idx !== index) return section;
      return { ...section, ...updates };
    });
    setProjectSpec({ ...projectSpec, form });
  };

  const handleRegenerate = async (index: number, keepMotif: boolean) => {
    if (!projectSpec) return;
    setLoading(true);
    setStatus("局部再生中...");
    try {
      const response = await regenerateSection({
        spec: projectSpec,
        section_index: index,
        keep_motif: keepMotif,
        emit_midi: true,
        tracks,
      });
      const adjusted = applyParamToSpec(response.project, paramState);
      setProjectSpec(adjusted);
      setRenderResult(response);
      setStatus("局部再生完成。");
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleFreezeMotif = async (tag: string) => {
    if (!projectSpec) return;
    setLoading(true);
    try {
      const updated = await freezeMotif(projectSpec, [tag]);
      setProjectSpec(updated);
      setStatus(`动机 ${tag} 已冻结。`);
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProject = async () => {
    if (!projectSpec) return;
    const name = window.prompt("请输入要保存的工程名称", "city_night_v1");
    if (!name) return;
    try {
      await saveProject(projectSpec, name);
      setStatus(`工程 ${name} 已保存到服务器。`);
    } catch (error) {
      setStatus((error as Error).message);
    }
  };

  const handleLoadProject = async () => {
    const name = window.prompt("请输入要载入的工程名称", "city_night_v1");
    if (!name) return;
    setLoading(true);
    try {
      const spec = await loadProject(name);
      const adjusted = applyParamToSpec(spec, paramState);
      setProjectSpec(adjusted);
      const response = await renderExisting(adjusted, true, tracks);
      setRenderResult(response);
      setStatus(`工程 ${name} 已载入并重新渲染。`);
    } catch (error) {
      setStatus((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const jsonPreview = useMemo(() => {
    if (!renderResult) return "{}";
    return JSON.stringify(renderResult.sections, null, 2);
  }, [renderResult]);

  return (
    <div className="min-h-screen bg-slate-900 p-6 text-slate-100">
      <div className="mx-auto grid max-w-6xl gap-6 md:grid-cols-3">
        <div className="space-y-6">
          <PromptPanel
            prompt={prompt}
            onPromptChange={setPrompt}
            onGenerate={handleGenerate}
            loading={loading}
          />
          <ParamsPanel
            state={paramState}
            options={options}
            selectedTracks={tracks}
            onStateChange={handleParamChange}
            onOptionsChange={handleOptionsChange}
            onTracksChange={setTracks}
          />
        </div>
        <div className="md:col-span-2 space-y-6">
          <div className="flex flex-col gap-4 rounded-md border border-slate-700 p-4">
            <DownloadBar
              midiPath={renderResult?.midi ?? null}
              specPath={renderResult?.spec ?? null}
              onSaveProject={handleSaveProject}
              onLoadProject={handleLoadProject}
            />
            <Player midiPath={renderResult?.midi ?? null} />
          </div>
          <FormTable
            project={projectSpec}
            onUpdateSection={handleSectionUpdate}
            onRegenerate={handleRegenerate}
            onFreezeMotif={handleFreezeMotif}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-md border border-slate-700 p-4 text-xs">
              <h3 className="mb-2 font-semibold">骨架摘要 JSON</h3>
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-slate-300">
                {jsonPreview}
              </pre>
            </div>
            <div className="rounded-md border border-slate-700 p-4 text-xs">
              <h3 className="mb-2 font-semibold">当前规格</h3>
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap text-slate-300">
                {projectSpec ? JSON.stringify(projectSpec, null, 2) : "{}"}
              </pre>
            </div>
          </div>
          {status && (
            <div className="rounded-md border border-slate-700 p-3 text-xs text-slate-300">
              {status}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
