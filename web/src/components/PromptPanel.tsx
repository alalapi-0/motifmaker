import React from "react";

interface PromptPanelProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  onGenerate: () => void;
  loading: boolean;
}

const PromptPanel: React.FC<PromptPanelProps> = ({
  prompt,
  onPromptChange,
  onGenerate,
  loading,
}) => {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-semibold">自然语言 Prompt</label>
      <textarea
        className="w-full rounded-md border border-slate-700 bg-slate-800 p-3 text-sm"
        rows={4}
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        placeholder="例：城市夜景的 Lo-Fi 节奏，带有电子合成器"
      />
      <button
        type="button"
        className="w-full rounded-md bg-cyan-500 py-2 text-sm font-semibold text-slate-900 transition hover:bg-cyan-400"
        onClick={onGenerate}
        disabled={loading}
      >
        {loading ? "生成中..." : "一键生成骨架"}
      </button>
    </div>
  );
};

export default PromptPanel;
