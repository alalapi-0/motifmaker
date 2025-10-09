import React from "react";

interface MelodyPanelProps {
  notes: string;
  onNotesChange: (value: string) => void;
  onConfirm: () => void;
  disabled: boolean;
  locked: boolean;
}

const MelodyPanel: React.FC<MelodyPanelProps> = ({ notes, onNotesChange, onConfirm, disabled, locked }) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed text-gray-200">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Melody Builder</h2>
        <p className="text-sm text-gray-300">
          Develop the motif into full phrases. Capture contour ideas or lyrical hooks before arranging.
        </p>
        <p className="text-xs uppercase tracking-[0.3em] text-bloodred">
          {locked ? "Melody locked" : "Write your sketch and confirm"}
        </p>
      </header>
      <div className="flex flex-col gap-4">
        <label className="text-xs uppercase tracking-[0.25em] text-gray-300">Melodic Sketch</label>
        <textarea
          className="min-h-[200px] rounded-lg border border-gray-700/70 bg-black/40 p-4 text-sm text-gray-100 transition focus-visible:border-bloodred focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/60"
          value={notes}
          onChange={(event) => onNotesChange(event.target.value)}
          placeholder="Detail how the motif evolves across A/B sections, dynamics, or counter lines."
        />
        <div className="flex flex-col gap-2">
          <button
            type="button"
            className="metal-button w-full rounded-md px-6 py-3 text-sm"
            onClick={onConfirm}
            disabled={disabled || !notes.trim()}
          >
            {locked ? "Update confirmation" : "Confirm melody"}
          </button>
          {locked && (
            <p className="text-xs text-gray-300">Melody is confirmed. Adjust text to unlock and refine.</p>
          )}
        </div>
      </div>
    </section>
  );
};

export default MelodyPanel;
