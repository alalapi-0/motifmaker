import React from "react";

/**
 * PromptPanel 组件：负责展示自然语言输入框与预设模板，
 * 引导用户快速填写灵感描述并触发“一键生成”流程。
 */
export interface PromptPanelProps {
  promptText: string; // 当前的自然语言 Prompt 文本。
  onPromptChange: (value: string) => void; // 文本更新时的回调。
  onGenerate: () => void; // 点击“一键生成”后的回调，由 App 触发后端请求。
  loading: boolean; // 是否处于加载状态，用于禁用按钮与展示提示。
}

const PROMPT_TEMPLATES: string[] = [
  "城市夜景、温暖而克制、B 段最高张力、现代古典+电子、约2分钟",
  "赛博朋克追逐场景、快速节奏、带有不规则鼓组与金属合成器",
  "日落海边、柔和摇摆、Lo-Fi 质感、加入爵士和声色彩",
];

const PromptPanel: React.FC<PromptPanelProps> = ({
  promptText,
  onPromptChange,
  onGenerate,
  loading,
}) => {
  return (
    <section className="space-y-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-sm">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">自然语言 Prompt</h2>
        <span className="text-xs text-slate-400">描述情绪/配器/时长/段落重点</span>
      </header>
      <div className="space-y-2">
        <label className="text-xs text-slate-400">快速套用模板</label>
        <div className="flex flex-wrap gap-2">
          {PROMPT_TEMPLATES.map((template) => (
            <sl-button
              key={template}
              size="small"
              variant="text"
              className="rounded-full bg-slate-800 px-3 text-xs text-slate-200"
              onClick={() => onPromptChange(template)}
            >
              {template}
            </sl-button>
          ))}
        </div>
      </div>
      <sl-textarea
        value={promptText}
        rows={4}
        placeholder="例：城市夜景的 Lo-Fi 节奏，配器包含钢琴与弦乐"
        className="block text-sm"
        onSlInput={(event) => {
          // Shoelace 的 sl-input 事件中，event.target 即为 textarea 元素实例。
          const target = event.target as HTMLInputElement;
          onPromptChange(target.value);
        }}
      ></sl-textarea>
      <sl-button
        variant="primary"
        className="w-full"
        disabled={loading}
        onClick={onGenerate}
      >
        {loading ? "生成中..." : "一键生成"}
      </sl-button>
      <p className="text-xs text-slate-400">
        点击按钮后将调用后端 /generate 接口，后端完成骨架生成后会返回 MIDI 与 JSON 摘要。
      </p>
    </section>
  );
};

export default PromptPanel;
