import React from "react";

/**
 * MelodyPanel 组件：在动机基础上拓展旋律线条，允许用户撰写与标注想法。
 * - 使用多行文本域记录旋律片段描述；
 * - 点击确认按钮后通知上层继续流程。
 */
interface MelodyPanelProps {
  notes: string;
  onNotesChange: (value: string) => void;
  onConfirm: () => void;
  disabled: boolean;
}

const MelodyPanel: React.FC<MelodyPanelProps> = ({ notes, onNotesChange, onConfirm, disabled }) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Melody Builder</h2>
        <p className="text-sm text-gray-400">
          Develop the motif into full phrases. Capture contour ideas or lyrical hooks before arranging.
        </p>
      </header>
      <div className="flex flex-col gap-4">
        <label className="text-xs uppercase tracking-[0.25em] text-gray-500">Melodic Sketch</label>
        <textarea
          className="min-h-[200px] rounded-lg border border-gray-700 bg-black/40 p-4 text-sm text-gray-100 outline-none focus:border-bloodred focus:ring-1 focus:ring-bloodred/60"
          value={notes}
          onChange={(event) => onNotesChange(event.target.value)}
          placeholder="Detail how the motif evolves across A/B sections, dynamics, or counter lines."
        />
        <button
          type="button"
          className="metal-button mt-2 w-full rounded-md px-6 py-3 text-sm"
          onClick={onConfirm}
          disabled={disabled || !notes.trim()}
        >
          Build Melody
        </button>
      </div>
    </section>
  );
};

export default MelodyPanel;
