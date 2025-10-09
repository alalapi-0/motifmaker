import React from "react";
import FriendlyError, { FriendlyErrorState } from "../FriendlyError";

interface MotifPanelProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  onGenerate: () => void;
  loading: boolean;
  error: FriendlyErrorState | null;
  summary: string | null;
  projectTitle: string | null;
  hasMotif: boolean;
}

const MotifPanel: React.FC<MotifPanelProps> = ({
  prompt,
  onPromptChange,
  onGenerate,
  loading,
  error,
  summary,
  projectTitle,
  hasMotif,
}) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed text-gray-200">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Motif Forge</h2>
        <p className="text-sm text-gray-300">
          Enter a vivid description and forge a primary motif before expanding the arrangement.
        </p>
        <p className="text-xs uppercase tracking-[0.3em] text-bloodred">
          {hasMotif ? "Motif locked" : "Step 1 of 5"}
        </p>
      </header>
      <div className="grid gap-8 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          <label className="text-xs uppercase tracking-[0.25em] text-gray-300">Creative Prompt</label>
          <textarea
            className="min-h-[220px] rounded-lg border border-gray-700/70 bg-black/40 p-4 text-sm text-gray-100 transition focus-visible:border-bloodred focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/60"
            value={prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            placeholder="Describe the atmosphere, pacing, and instrumentation you want to explore."
          />
          <button
            type="button"
            className="metal-button mt-2 w-full rounded-md px-6 py-3 text-sm"
            onClick={onGenerate}
            disabled={loading || !prompt.trim()}
          >
            {loading ? "Generating..." : hasMotif ? "Regenerate Motif" : "Generate Motif"}
          </button>
          {error && <FriendlyError {...error} />}
        </div>
        <div className="rounded-lg border border-bloodred/20 bg-black/30 p-4 text-sm text-gray-200">
          <h3 className="text-lg font-semibold text-white">Latest Result</h3>
          {summary ? (
            <div className="mt-3 space-y-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-gray-400">Project Title</p>
                <p className="text-base font-semibold text-white">{projectTitle ?? "Untitled"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-gray-400">Motif Notes</p>
                <p className="whitespace-pre-line text-sm text-gray-100">{summary}</p>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-gray-400">
              Motif metadata will appear here after generation. Lock the idea before moving forward.
            </p>
          )}
        </div>
      </div>
    </section>
  );
};

export default MotifPanel;
