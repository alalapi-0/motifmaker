import React from "react";
import FriendlyError, { FriendlyErrorState } from "../FriendlyError";

interface MidiPanelProps {
  arrangement: string;
  onArrangementChange: (value: string) => void;
  onArrange: () => void;
  loading: boolean;
  disabled: boolean;
  midiUrl: string | null;
  error?: FriendlyErrorState | null;
  ready: boolean;
}

const MidiPanel: React.FC<MidiPanelProps> = ({
  arrangement,
  onArrangementChange,
  onArrange,
  loading,
  disabled,
  midiUrl,
  error,
  ready,
}) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed text-gray-200">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">MIDI Arranger</h2>
        <p className="text-sm text-gray-300">
          Define structure, harmonic density, and transitions. The arranger will consolidate everything into a new MIDI file.
        </p>
        <p className="text-xs uppercase tracking-[0.3em] text-bloodred">
          {ready ? "Latest MIDI ready" : "Render a structure to unlock mixing"}
        </p>
      </header>
      <div className="flex flex-col gap-4">
        <label className="text-xs uppercase tracking-[0.25em] text-gray-300">Arrangement Blueprint</label>
        <textarea
          className="min-h-[200px] rounded-lg border border-gray-700/70 bg-black/40 p-4 text-sm text-gray-100 transition focus-visible:border-bloodred focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/60"
          value={arrangement}
          onChange={(event) => onArrangementChange(event.target.value)}
          placeholder="Describe section flow, percussion layers, or harmonic changes for the arranger."
        />
        <button
          type="button"
          className="metal-button mt-2 w-full rounded-md px-6 py-3 text-sm"
          onClick={onArrange}
          disabled={disabled || loading}
        >
          {loading ? "Arranging..." : "Arrange MIDI"}
        </button>
        {error && <FriendlyError {...error} />}
        {midiUrl && (
          <div className="mt-4 rounded-lg border border-bloodred/30 bg-black/40 p-4 text-xs text-gray-200">
            <p className="font-semibold text-white">MIDI Ready</p>
            <p className="mt-2 text-sm text-gray-300">
              Download the generated MIDI and head into the mixing console when you are satisfied with the structure.
            </p>
            <a
              className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-bloodred transition hover:text-red-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/70 focus-visible:ring-offset-2 focus-visible:ring-offset-black"
              href={midiUrl}
              target="_blank"
              rel="noreferrer"
            >
              Download Latest MIDI
            </a>
          </div>
        )}
      </div>
    </section>
  );
};

export default MidiPanel;
