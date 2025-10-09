import React from "react";

interface RenderPanelProps {
  audioUrl: string | null;
  midiUrl: string | null;
  projectTitle: string | null;
  projectId: string;
}

const RenderPanel: React.FC<RenderPanelProps> = ({ audioUrl, midiUrl, projectTitle, projectId }) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed text-gray-200">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Final Track</h2>
        <p className="text-sm text-gray-300">
          Celebrate the completed piece. Export assets and get ready for the next iteration.
        </p>
        <p className="text-xs uppercase tracking-[0.3em] text-bloodred">Step 5 · Delivery</p>
      </header>
      <div className="rounded-xl border border-bloodred/30 bg-gradient-to-br from-graysteel/40 via-black/60 to-black/80 p-6">
        <div className="flex flex-col gap-4 text-sm text-gray-200">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-300">Project ID</p>
            <p className="text-lg font-semibold text-white">{projectId}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-gray-300">Track Title</p>
            <p className="text-xl font-bold text-white">{projectTitle ?? "Untitled Metal Render"}</p>
          </div>
          {audioUrl ? (
            <div className="flex flex-col gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-gray-300">Preview</p>
                <audio controls className="mt-2 w-full rounded-lg border border-bloodred/40 bg-black/50 p-2">
                  <source src={audioUrl} />
                  Your browser does not support the audio element.
                </audio>
              </div>
              <div className="flex flex-wrap gap-3">
                <a
                  className="metal-button inline-flex items-center justify-center rounded-md px-6 py-3 text-sm"
                  href={audioUrl}
                  download
                >
                  Download Audio
                </a>
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
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-300">Audio not rendered yet. Go to Mixing step.</p>
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
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

export default RenderPanel;
