import React from "react";

/**
 * MidiPanel 组件：承接旋律草稿，触发 /render 生成新的 MIDI 结构。
 * - 允许输入分段与节奏规划；
 * - 渲染成功后反馈可下载链接，提醒进入混音阶段。
 */
interface MidiPanelProps {
  arrangement: string;
  onArrangementChange: (value: string) => void;
  onArrange: () => void;
  loading: boolean;
  disabled: boolean;
  midiUrl: string | null;
  error?: string | null;
}

const MidiPanel: React.FC<MidiPanelProps> = ({
  arrangement,
  onArrangementChange,
  onArrange,
  loading,
  disabled,
  midiUrl,
  error,
}) => {
  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">MIDI Arranger</h2>
        <p className="text-sm text-gray-400">
          Define structure, harmonic density, and transitions. The arranger will consolidate everything into a new MIDI file.
        </p>
      </header>
      <div className="flex flex-col gap-4">
        <label className="text-xs uppercase tracking-[0.25em] text-gray-500">Arrangement Blueprint</label>
        <textarea
          className="min-h-[200px] rounded-lg border border-gray-700 bg-black/40 p-4 text-sm text-gray-100 outline-none focus:border-bloodred focus:ring-1 focus:ring-bloodred/60"
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
        {error && <p className="text-xs text-bloodred">{error}</p>}
        {midiUrl && (
          <div className="mt-4 rounded-lg border border-bloodred/30 bg-black/40 p-4 text-xs text-gray-300">
            <p className="font-semibold text-white">MIDI Ready</p>
            <p className="mt-2 text-sm text-gray-400">
              Download the generated MIDI and head into the mixing console when you are satisfied with the structure.
            </p>
            <a
              className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-bloodred hover:text-red-400"
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
