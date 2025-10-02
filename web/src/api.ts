/**
 * 与后端 FastAPI 交互的统一封装，负责构建请求、解析响应以及错误处理。
 * 所有函数均提供中文文档说明，便于前后端协同调试。
 */

// ProjectSpec 中的曲式段落结构定义。
export interface FormSection {
  section: string; // 段落标签，例如 Intro/A/B/Bridge。
  bars: number; // 小节数，决定段落时长。
  tension: number; // 张力曲线，常以 0-10 表示。
  motif_label: string; // 关联的动机标签，便于局部再生时定位素材。
}

// ProjectSpec 的核心结构，对应后端 schema.ProjectSpec。
export interface ProjectSpec {
  title?: string; // 可选标题字段，后端若无则忽略。
  tempo_bpm: number; // 基础速度（BPM）。
  meter: string; // 拍号，例如 "4/4"。
  key: string; // 主音（C/D/E...）。
  mode: string; // 调式（major/minor 等）。
  instrumentation: string[]; // 配器列表，由后端最终校验。
  harmony_options?: {
    use_secondary_dominant?: boolean; // 是否开启二级属功能。
  };
  form: FormSection[]; // 曲式段落数组。
  [extra: string]: unknown; // 允许后端扩展其他字段（动机字典等）。
}

// 生成或再生成接口的统一返回类型。
export interface GenerateResponse {
  project_spec: ProjectSpec; // 最新的工程规格。
  mid_path: string; // 后端生成的 MIDI 相对路径。
  json_path: string; // 后端生成的 JSON 相对路径。
  track_stats: Record<string, unknown>; // 分轨统计信息，供 UI 摘要展示。
  duration_sec_est?: number; // 估算时长（可选）。
}

// 参数覆盖对象，前端临时维护，提交时与 ProjectSpec 合并，由后端做最终校验。
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

// 通过 Vite 环境变量读取 API 基础地址，默认指向本地开发服务器。
export const API_BASE: string =
  (import.meta as any).env?.VITE_API_BASE ?? "http://127.0.0.1:8000";

// 帮助组件将后端返回的相对路径拼接成可访问的完整 URL。
export function resolveAssetUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) {
    return path; // 已经是绝对地址则直接返回。
  }
  const base = API_BASE.replace(/\/?$/, "/"); // 确保 base 以单个斜杠结尾。
  const normalized = path.replace(/^\/+/, ""); // 去掉相对路径开头的斜杠。
  return `${base}${normalized}`;
}

// 通用请求封装：统一设置 POST、JSON Header，并在非 2xx 时抛出详细错误。
async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API 请求失败：${response.status} ${detail}`);
  }
  return (await response.json()) as T;
}

/**
 * 触发全量生成：向 /generate 提交自然语言 Prompt 及参数覆盖。
 * @param prompt 用户输入的描述文本。
 * @param overrides 参数覆盖对象，可选。
 * @param outPrefix 输出前缀，便于自定义文件夹（可选）。
 * @returns 后端返回的最新工程规格与文件路径。
 */
export async function generate(
  prompt: string,
  overrides?: ParamOverrides,
  outPrefix?: string
): Promise<GenerateResponse> {
  return postJson<GenerateResponse>("/generate", {
    prompt,
    overrides,
    out_prefix: outPrefix,
  });
}

/**
 * 局部再生成：仅针对某一段落重新生成素材，避免整体重算。
 * @param spec 当前的 ProjectSpec，用于让后端定位现有工程。
 * @param sectionIndex 需要再生的段落索引（从 0 开始）。
 * @param keepMotif 是否保留原动机标签，true 表示仅更新细节。
 * @param outPrefix 输出前缀，方便分版本保存（可选）。
 * @returns 更新后的工程规格与文件路径。
 */
export async function regenerateSection(
  spec: ProjectSpec,
  sectionIndex: number,
  keepMotif: boolean,
  outPrefix?: string
): Promise<GenerateResponse> {
  return postJson<GenerateResponse>("/regenerate-section", {
    spec,
    section_index: sectionIndex,
    keep_motif: keepMotif,
    out_prefix: outPrefix,
  });
}

/**
 * 保存工程到后端：通常写入 projects/ 目录，便于以后继续编辑。
 * @param spec 需要持久化的工程规格。
 * @param name 保存时使用的工程名称。
 */
export async function saveProject(spec: ProjectSpec, name: string): Promise<void> {
  await postJson<unknown>("/save-project", { spec, name });
}

/**
 * 从后端载入既有工程。
 * @param name 已保存的工程名称。
 * @returns 返回完整的 ProjectSpec，供前端继续编辑。
 */
export async function loadProject(name: string): Promise<ProjectSpec> {
  const result = await postJson<{ project_spec: ProjectSpec }>("/load-project", {
    name,
  });
  return result.project_spec;
}
