import React from "react";

/**
 * MotifPanel 组件：负责引导用户输入 Prompt 并触发动机生成。
 * - 左侧提供 Prompt 文本域；
 * - 右侧展示最近一次生成摘要，强调需要锁定后才能前往下一步。
 */
interface MotifPanelProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  onGenerate: () => void;
  loading: boolean;
  error: string | null;
  summary: string | null;
  projectTitle: string | null;
}

const MotifPanel: React.FC<MotifPanelProps> = ({
  prompt,
  onPromptChange,
  onGenerate,
  loading,
  error,
  summary,
  projectTitle,
}) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Motif Forge</h2>
        <p className="text-sm text-gray-400">
          Enter a vivid description and forge a primary motif before expanding the arrangement.
        </p>
      </header>
      <div className="grid gap-8 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          <label className="text-xs uppercase tracking-[0.25em] text-gray-500">Creative Prompt</label>
          <textarea
            className="min-h-[220px] rounded-lg border border-gray-700 bg-black/40 p-4 text-sm text-gray-100 outline-none focus:border-bloodred focus:ring-1 focus:ring-bloodred/60"
            value={prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            placeholder="Describe the atmosphere, pacing, and instrumentation you want to explore."
          />
          {error && <p className="text-xs text-bloodred">{error}</p>}
          <button
            type="button"
            className="metal-button mt-2 w-full rounded-md px-6 py-3 text-sm"
            onClick={onGenerate}
            disabled={loading || !prompt.trim()}
          >
            {loading ? "Generating..." : "Generate Motif"}
          </button>
        </div>
        <div className="rounded-lg border border-bloodred/20 bg-black/30 p-4">
          <h3 className="text-lg font-semibold text-white">Latest Result</h3>
          {summary ? (
            <div className="mt-3 space-y-3 text-sm text-gray-300">
              <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Project Title</p>
              <p className="text-base text-white">{projectTitle ?? "Untitled"}</p>
              <p className="text-xs uppercase tracking-[0.2em] text-gray-500">Motif Notes</p>
              <p className="whitespace-pre-line text-sm text-gray-200">{summary}</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-500">
              Motif metadata will appear here after generation. Lock the idea before moving forward.
            </p>
          )}
        </div>
      </div>
    </section>
  );
};

export default MotifPanel;
