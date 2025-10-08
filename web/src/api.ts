/**
 * 与后端 FastAPI 交互的统一封装，负责构建请求、解析响应以及错误透传。
 * 由于 Round B 聚焦前端体验，我们在此整理所有接口定义，
 * 并确保类型与后端 Pydantic 模型保持同步，便于后续演进时静态检查。
 */

// -----------------------------
// 类型声明区域
// -----------------------------

/**
 * 单个曲式段落结构，对应后端 schema.FormSection。
 * 提供 section 标签、小节数、张力以及引用的动机标签。
 */
export interface FormSection {
  section: string; // 段落标签，例如 Intro/A/B/Bridge。
  bars: number; // 小节数，UI 侧限制在 1-128。
  tension: number; // 张力 0-100，结合表格滑块展示。
  motif_label: string; // 关联的动机标签，用于局部再生成或冻结。
}

/**
 * 动机规格的简化描述，后端可能包含更多字段（节奏、轮廓等）。
 * 我们仅声明常用字段，并通过索引签名允许扩展，保持向后兼容。
 */
export interface MotifSpecMeta {
  name?: string;
  description?: string;
  _frozen?: boolean; // 标记动机是否已冻结，前端据此禁用再生或打标。
  [extra: string]: unknown;
}

/**
 * ProjectSpec 是生成骨架的核心结构，囊括调性、速度、配器等信息。
 * 由于后端在 Pydantic 中包含大量字段，这里显式列出主要属性并保留索引签名，
 * 以便未来新增字段时无需立即修改前端。
 */
export interface ProjectSpec {
  title?: string;
  tempo_bpm: number;
  meter: string;
  key: string;
  mode: string;
  style?: string;
  instrumentation: string[];
  motif_specs: Record<string, MotifSpecMeta>;
  form: FormSection[];
  rhythm_density?: string;
  motif_style?: string;
  harmony_level?: string;
  use_secondary_dominant?: boolean;
  generated_sections?: Record<string, Record<string, unknown>> | null;
  [extra: string]: unknown;
}

/**
 * 渲染接口的统一返回体，对应 success_response(result)。
 * 包含输出目录、MIDI/JSON 路径、统计信息以及最新 ProjectSpec。
 */
export interface RenderSuccess {
  output_dir: string;
  spec: string;
  summary: string;
  midi: string | null;
  project: ProjectSpec;
  sections: Record<string, Record<string, unknown>>;
  track_stats: Array<Record<string, unknown>>;
}

/**
 * 保存工程后的返回体，携带服务器上的文件路径。
 */
export interface SaveSuccess {
  path: string;
}

/**
 * 载入工程返回体，包含 ProjectSpec 与源路径。
 */
export interface LoadSuccess {
  project: ProjectSpec;
  path: string;
}

/**
 * 冻结动机后的返回体，后端返回更新后的 ProjectSpec。
 */
export interface FreezeSuccess {
  project: ProjectSpec;
}

/**
 * 音频渲染结果结构，记录占位合成返回的核心字段。
 */
export interface AudioRenderResult {
  audio_url: string;
  duration_sec: number;
  renderer: string;
  style: string;
  intensity: number;
}

/**
 * /healthz 健康检查响应。
 */
export interface HealthResponse {
  ok: true;
  ts: number;
}

/**
 * /version 响应，仅含语义化版本号。
 */
export interface VersionResponse {
  version: string;
}

/**
 * /config-public 响应，暴露非敏感配置，供状态栏显示。
 */
export interface ConfigPublicResponse {
  output_dir: string;
  projects_dir: string;
  allowed_origins: string[];
}

/**
 * 参数覆盖结构：前端在 UI 中提供临时修改，提交请求前会与 ProjectSpec 合并，
 * 由后端再次校验，保证非法值不会污染服务器端状态。
 */
export interface ParamOverrides {
  tempo_bpm?: number;
  meter?: string;
  key?: string;
  mode?: string;
  instrumentation?: string[];
  harmony_options?: {
    use_secondary_dominant?: boolean;
  };
}

/**
 * 统一的 API 错误对象，保留 HTTP 状态码、后端错误码与详细信息。
 * 我们不在此吞掉错误，而是交给上层 UI 处理，便于提示用户具体原因。
 */
export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;

  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// -----------------------------
// 基础配置与工具函数
// -----------------------------

// 通过 Vite 环境变量读取 API 基础地址，默认指向本地开发服务器。
export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "http://127.0.0.1:8000";

/**
 * 构造后端资源的可访问 URL。
 * 若 path 已经是绝对地址则直接返回；若为本地文件路径，则拼接 /download 路径。
 */
export function resolveAssetUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) {
    return path; // 后端已返回完整 URL 时无需处理。
  }
  if (path.startsWith("/")) {
    const base = API_BASE.replace(/\/?$/, "");
    return `${base}${path}`; // 处理以 / 开头的静态资源路径，常见于占位音频。
  }
  const base = API_BASE.replace(/\/?$/, "");
  // 通过 download 端点安全读取输出目录，避免直接暴露文件系统结构。
  const encoded = encodeURIComponent(path);
  return `${base}/download?path=${encoded}`;
}

/**
 * 内部辅助函数：解析 POST 响应并抛出结构化错误。
 * 所有 POST 接口都会返回 { ok: boolean, result | error } 结构。
 */
async function postJson<T>(
  path: string,
  payload: unknown,
  signal?: AbortSignal
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  let data: unknown = null;
  try {
    data = await response.json();
  } catch (error) {
    // API 返回体解析失败时统一输出英文提示，避免前端弹窗出现中文残留。
    throw new ApiError("Failed to parse response body. Please check the network or backend logs.", response.status);
  }

  const parsed = data as
    | { ok: true; result: T }
    | { ok: false; error: { code?: string; message: string; details?: unknown } };

  if (!response.ok || !parsed.ok) {
    const errorPayload = !parsed.ok
      ? parsed.error
      : { message: `HTTP ${response.status}`, code: undefined };
    throw new ApiError(
      errorPayload.message ?? "Unknown error",
      response.status,
      errorPayload.code,
      errorPayload.details
    );
  }

  return parsed.result;
}

/**
 * GET 请求工具：健康检查/版本等接口直接返回实体 JSON。
 */
async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method: "GET", signal });
  if (!response.ok) {
    throw new ApiError(`HTTP ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

// -----------------------------
// 业务接口封装
// -----------------------------

/**
 * 根据自然语言 Prompt 调用 /generate，默认请求后端导出 MIDI。
 * 这里不附带参数覆盖，保持后端解析的权威性，前端若需覆盖会在后续调用 /render。
 */
export async function generate(
  prompt: string,
  signal?: AbortSignal
): Promise<RenderSuccess> {
  return postJson<RenderSuccess>(
    "/generate",
    {
      prompt,
      options: {
        emit_midi: true,
      },
    },
    signal
  );
}

/**
 * 使用编辑后的 ProjectSpec 调用 /render，生成新的 MIDI/统计信息。
 */
export async function renderProject(
  project: ProjectSpec,
  signal?: AbortSignal
): Promise<RenderSuccess> {
  return postJson<RenderSuccess>(
    "/render",
    {
      project,
      emit_midi: true,
    },
    signal
  );
}

/**
 * 局部再生成指定段落，mode 控制是否保留动机。
 */
export async function regenerateSection(
  spec: ProjectSpec,
  sectionIndex: number,
  keepMotif: boolean,
  signal?: AbortSignal
): Promise<RenderSuccess> {
  return postJson<RenderSuccess>(
    "/regenerate-section",
    {
      spec,
      section_index: sectionIndex,
      keep_motif: keepMotif,
      emit_midi: true,
    },
    signal
  );
}

/**
 * 冻结若干动机标签，返回更新后的 ProjectSpec。
 */
export async function freezeMotif(
  spec: ProjectSpec,
  motifTags: string[],
  signal?: AbortSignal
): Promise<FreezeSuccess> {
  return postJson<FreezeSuccess>(
    "/freeze-motif",
    {
      spec,
      motif_tags: motifTags,
    },
    signal
  );
}

/**
 * 保存工程至后端 projects/ 目录。
 */
export async function saveProject(
  spec: ProjectSpec,
  name: string,
  signal?: AbortSignal
): Promise<SaveSuccess> {
  return postJson<SaveSuccess>(
    "/save-project",
    { spec, name },
    signal
  );
}

/**
 * 载入既有工程，返回完整 ProjectSpec。
 */
export async function loadProject(
  name: string,
  signal?: AbortSignal
): Promise<LoadSuccess> {
  return postJson<LoadSuccess>(
    "/load-project",
    { name },
    signal
  );
}

/**
 * renderAudio: 调用 /render/ 接口，将 MIDI 上传或传 midi_path，返回 audio_url。
 * params:
 *  - file?: File         // 可选，直接上传的 MIDI 文件
 *  - midiPath?: string   // 可选，已有的 outputs/*.mid 路径
 *  - style: string       // 渲染风格
 *  - intensity: number   // 0..1，强度
 * 说明：二选一传入 file 或 midiPath。服务端将返回 { ok, result: { audio_url, ... } }
 * 中文注释：错误处理使用 ApiError 统一透传；FormData 便于混合文件与文本字段。
 */
export async function renderAudio(
  params: { file?: File; midiPath?: string; style: string; intensity: number },
  signal?: AbortSignal
): Promise<AudioRenderResult> {
  const form = new FormData();
  if (params.file) {
    form.append("midi_file", params.file);
  }
  if (!params.file && params.midiPath) {
    form.append("midi_path", params.midiPath);
  }
  form.append("style", params.style);
  form.append("intensity", String(params.intensity));

  const response = await fetch(`${API_BASE}/render/`, {
    method: "POST",
    body: form,
    signal,
  });

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    throw new ApiError("Audio render failed. Please try again later.", response.status);
  }

  const data = payload as {
    ok?: boolean;
    result?: AudioRenderResult;
    error?: { message?: string; code?: string; details?: unknown };
  };

  if (!response.ok || data.ok !== true || !data.result) {
    const message = data.error?.message || "Audio render failed. Please try again later.";
    throw new ApiError(message, response.status, data.error?.code, data.error?.details);
  }

  return data.result;
}

/**
 * 健康检查接口，供 TopStatusBar 轮询。
 */
export async function healthz(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson<HealthResponse>("/healthz", signal);
}

/**
 * 查询后端版本号。
 */
export async function version(signal?: AbortSignal): Promise<VersionResponse> {
  return getJson<VersionResponse>("/version", signal);
}

/**
 * 读取可公开配置，展示输出目录、允许的跨域来源等信息。
 */
export async function configPublic(
  signal?: AbortSignal
): Promise<ConfigPublicResponse> {
  const result = await getJson<{
    output_dir: string;
    projects_dir: string | string[];
    allowed_origins: string[];
  }>("/config-public", signal);
  return {
    ...result,
    projects_dir: Array.isArray(result.projects_dir)
      ? result.projects_dir.join(", ")
      : result.projects_dir,
  };
}

// -----------------------------
// 参数覆盖工具函数
// -----------------------------

/**
 * 将前端的参数覆盖合并到 ProjectSpec，保持不可变数据结构以便 React 检测变更。
 * 合并逻辑保持简单：若覆盖值为空则回退到原始 spec。
 */
export function mergeSpecWithOverrides(
  spec: ProjectSpec,
  overrides: ParamOverrides
): ProjectSpec {
  return {
    ...spec,
    tempo_bpm: overrides.tempo_bpm ?? spec.tempo_bpm,
    meter: overrides.meter ?? spec.meter,
    key: overrides.key ?? spec.key,
    mode: overrides.mode ?? spec.mode,
    instrumentation: overrides.instrumentation ?? spec.instrumentation,
    use_secondary_dominant:
      overrides.harmony_options?.use_secondary_dominant ??
      spec.use_secondary_dominant,
  };
}
