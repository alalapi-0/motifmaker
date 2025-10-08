import React from "react";

/**
 * RenderPanel 组件：最终试听与下载界面，展示项目 ID 与标题。
 * - 当混音结果可用时提供音频播放器；
 * - 继续沿用金属色块背景营造收官仪式感。
 */
interface RenderPanelProps {
  audioUrl: string | null;
  midiUrl: string | null;
  projectTitle: string | null;
  projectId: string;
}

const RenderPanel: React.FC<RenderPanelProps> = ({ audioUrl, midiUrl, projectTitle, projectId }) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Final Track</h2>
        <p className="text-sm text-gray-400">
          Celebrate the completed piece. Export assets and get ready for the next iteration.
        </p>
      </header>
      <div className="rounded-xl border border-bloodred/30 bg-gradient-to-br from-graysteel/40 via-black/60 to-black/80 p-6">
        <div className="flex flex-col gap-4 text-sm text-gray-300">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Project ID</p>
            <p className="text-lg font-semibold text-white">{projectId}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Track Title</p>
            <p className="text-xl font-bold text-white">{projectTitle ?? "Untitled Metal Render"}</p>
          </div>
          {audioUrl ? (
            <div className="flex flex-col gap-3">
              <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Preview</p>
              <audio controls className="w-full rounded-lg border border-bloodred/40 bg-black/50 p-2">
                <source src={audioUrl} />
                Your browser does not support the audio element.
              </audio>
              <p className="text-sm text-gray-400">🎵 Track Ready!</p>
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Render the mix to unlock the final preview. The player will appear here once audio is available.
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              className="metal-button inline-flex items-center justify-center rounded-md px-6 py-3 text-sm"
              href={midiUrl ?? "#"}
              download
              aria-disabled={!midiUrl}
              onClick={(event) => {
                if (!midiUrl) {
                  event.preventDefault();
                }
              }}
            >
              Download MIDI
            </a>
            <a
              className="metal-button inline-flex items-center justify-center rounded-md px-6 py-3 text-sm"
              href={audioUrl ?? "#"}
              download
              aria-disabled={!audioUrl}
              onClick={(event) => {
                if (!audioUrl) {
                  event.preventDefault();
                }
              }}
            >
              Download Audio
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};

export default RenderPanel;
