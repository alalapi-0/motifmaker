// 该文件封装所有与后端交互的 HTTP 请求，便于组件调用。

export interface TrackStat {
  name: string;
  notes: number;
  duration_sec: number;
}

export interface RenderResponse {
  output_dir: string;
  spec: string;
  summary: string;
  midi: string | null;
  project: ProjectSpec;
  sections: Record<string, Record<string, unknown>>;
  track_stats: TrackStat[];
}

export interface ProjectSpec {
  form: { section: string; bars: number; tension: number; motif_label: string }[];
  key: string;
  mode: string;
  tempo_bpm: number;
  meter: string;
  style: string;
  instrumentation: string[];
  motif_specs: Record<string, Record<string, unknown>>;
  generated_sections?: Record<string, Record<string, unknown>>;
}

export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE ?? "http://127.0.0.1:8000";

// 封装 fetch，自动处理 JSON 与错误提示。
async function request<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API 调用失败: ${response.status} ${detail}`);
  }
  return (await response.json()) as T;
}

export interface GenerateOptions {
  motif_style?: string;
  rhythm_density?: string;
  harmony_level?: string;
  emit_midi?: boolean;
  tracks?: string[];
}

export async function generateFromPrompt(
  prompt: string,
  options?: GenerateOptions
): Promise<RenderResponse> {
  // 生成接口：提交自然语言 Prompt，并可传入 UI 覆盖参数。
  return request<RenderResponse>("/generate", { prompt, options });
}

export interface RegeneratePayload {
  spec: ProjectSpec;
  section_index: number;
  keep_motif: boolean;
  emit_midi: boolean;
  tracks?: string[];
}

export async function regenerateSection(
  payload: RegeneratePayload
): Promise<RenderResponse> {
  // 局部再生接口：将当前规格及段落索引送往后端，仅重新渲染目标片段。
  return request<RenderResponse>("/regenerate-section", payload);
}

export async function freezeMotif(
  spec: ProjectSpec,
  motifTags: string[]
): Promise<ProjectSpec> {
  // 动机冻结接口：后端返回更新后的 ProjectSpec 供 UI 持续使用。
  const result = await request<{ project: ProjectSpec }>("/freeze-motif", {
    spec,
    motif_tags: motifTags,
  });
  return result.project;
}

export async function saveProject(spec: ProjectSpec, name: string): Promise<string> {
  // 将当前工程保存到服务器 projects/ 目录，返回保存路径。
  const result = await request<{ path: string }>("/save-project", { spec, name });
  return result.path;
}

export async function loadProject(name: string): Promise<ProjectSpec> {
  // 载入已经保存的工程，通常用于恢复编辑会话。
  const result = await request<{ project: ProjectSpec }>("/load-project", { name });
  return result.project;
}

export async function renderExisting(
  spec: ProjectSpec,
  emitMidi: boolean,
  tracks?: string[]
): Promise<RenderResponse> {
  // 使用 /render 接口对现有规格重新渲染，便于载入工程后立刻得到最新输出。
  return request<RenderResponse>("/render", {
    project: spec,
    emit_midi: emitMidi,
    tracks,
  });
}
