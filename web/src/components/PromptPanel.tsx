import React, { useCallback } from "react";
import { useI18n } from "../hooks/useI18n";

/**
 * PromptPanel 组件：负责展示自然语言输入框与预设模板，
 * 引导用户快速填写灵感描述并触发“一键生成”流程。
 * 在本轮中我们强化了键盘可访问性（Alt+Enter 触发生成）并适配多语言。
 */
export interface PromptPanelProps {
  promptText: string; // 当前的自然语言 Prompt 文本。
  onPromptChange: (value: string) => void; // 文本更新时的回调。
  onGenerate: () => void; // 点击“一键生成”后的回调，由 App 触发后端请求。
  loading: boolean; // 是否处于加载状态，用于禁用按钮与展示提示。
}

// 预设模板统一改为英文描述，覆盖多种风格便于国际用户参考与快速上手。
const PROMPT_TEMPLATES: string[] = [
  "Dreamy lo-fi beat for a rainy evening, piano and vinyl textures, around 90 BPM",
  "High-energy cyberpunk chase with irregular drums and metallic synths, 140 BPM",
  "Sunset beach swing with gentle jazz harmony, relaxed groove near 110 BPM",
];

const PromptPanel: React.FC<PromptPanelProps> = ({
  promptText,
  onPromptChange,
  onGenerate,
  loading,
}) => {
  const { t } = useI18n();

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Alt+Enter 快捷键触发生成，便于键盘操作用户快速提交。
      if (event.altKey && event.key === "Enter") {
        event.preventDefault();
        onGenerate();
      }
    },
    [onGenerate]
  );

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("prompt.title")}</h2>
        <span className="text-xs text-slate-500 dark:text-slate-400">{t("prompt.subtitle")}</span>
      </header>
      <div className="space-y-2">
        <label className="text-xs text-slate-500 dark:text-slate-400">{t("prompt.templates")}</label>
        <div className="flex flex-wrap gap-2">
          {PROMPT_TEMPLATES.map((template) => (
            <button
              key={template}
              type="button"
              className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-400 hover:text-slate-900 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
              onClick={() => onPromptChange(template)}
            >
              {template}
            </button>
          ))}
        </div>
      </div>
      <sl-textarea
        value={promptText}
        rows={4}
        placeholder={t("prompt.placeholder")}
        className="block text-sm"
        aria-label={t("prompt.title")}
        onSlInput={(event: CustomEvent) => {
          const target = event.target as HTMLInputElement;
          onPromptChange(target.value);
        }}
        onKeyDown={handleKeyDown}
      ></sl-textarea>
      <sl-button
        variant="primary"
        className="w-full"
        disabled={loading}
        loading={loading}
        onClick={onGenerate}
      >
        {loading ? t("prompt.generating") : t("prompt.generate")}
      </sl-button>
      <p className="text-xs text-slate-500 dark:text-slate-400">{t("prompt.keyboardHint")}</p>
    </section>
  );
};

export default PromptPanel;
