import React from "react";
import { SlRange, SlSelect, SlOption } from "@shoelace-style/shoelace/dist/react";

/**
 * MixPanel 组件：模拟混音台调参，提供混响、声像、音量与预设选择。
 * - 控件基于 Shoelace，实现统一的金属红主题；
 * - 点击 Render 按钮会调用后端 /render/audio 接口获取占位音频。
 */
export type MixStyle = "cinematic" | "electronic" | "lo-fi" | "pop";

export interface MixSettings {
  reverb: number;
  pan: number;
  volume: number;
  intensity: number;
  preset: string;
  style: MixStyle;
}

interface MixPanelProps {
  settings: MixSettings;
  onSettingsChange: (value: MixSettings) => void;
  onRender: () => void;
  loading: boolean;
  disabled: boolean;
  error: string | null;
  audioUrl: string | null;
}

const numericKeys: Array<keyof Pick<MixSettings, "reverb" | "pan" | "volume" | "intensity">> = [
  "reverb",
  "pan",
  "volume",
  "intensity",
];

const MixPanel: React.FC<MixPanelProps> = ({ settings, onSettingsChange, onRender, loading, disabled, error, audioUrl }) => {
  const handleRangeChange = (key: (typeof numericKeys)[number]) => (event: CustomEvent) => {
    // Shoelace 事件目标为输入元素，取其 value 并转换为数字。
    const target = event.target as HTMLInputElement;
    const value = Number(target.value);
    onSettingsChange({ ...settings, [key]: value });
  };

  const handlePresetChange = (event: CustomEvent) => {
    const target = event.target as HTMLSelectElement;
    onSettingsChange({ ...settings, preset: target.value });
  };

  const handleStyleChange = (event: CustomEvent) => {
    const target = event.target as HTMLSelectElement;
    onSettingsChange({ ...settings, style: target.value as MixStyle });
  };

  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Mixing Console</h2>
        <p className="text-sm text-gray-400">
          Fine-tune space and balance before rendering audio. These controls will map to the upcoming waveform engine.
        </p>
      </header>
      <div className="grid gap-8 md:grid-cols-2">
        <div className="space-y-6">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Reverb</label>
            <SlRange
              className="w-full"
              min={0}
              max={100}
              value={settings.reverb}
              onSlInput={handleRangeChange("reverb")}
            />
            <p className="mt-2 text-xs text-gray-400">Decay intensity mapped from 0% (dry) to 100% (arena).</p>
          </div>
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Pan</label>
            <SlRange
              className="w-full"
              min={-100}
              max={100}
              value={settings.pan}
              onSlInput={handleRangeChange("pan")}
            />
            <p className="mt-2 text-xs text-gray-400">Negative values move left, positive values move right.</p>
          </div>
        </div>
        <div className="space-y-6">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Intensity</label>
            <SlRange
              className="w-full"
              min={0}
              max={100}
              value={settings.intensity}
              onSlInput={handleRangeChange("intensity")}
            />
            <p className="mt-2 text-xs text-gray-400">
              Controls how aggressive the renderer should interpret dynamics and drive.
            </p>
          </div>
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Volume (dB)</label>
            <SlRange
              className="w-full"
              min={-24}
              max={6}
              step={0.5}
              value={settings.volume}
              onSlInput={handleRangeChange("volume")}
            />
            <p className="mt-2 text-xs text-gray-400">Adjust gain before limiting. 0 dB keeps the original loudness.</p>
          </div>
        </div>
      </div>
      <div className="mt-6 grid gap-8 md:grid-cols-2">
        <div className="space-y-6">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Instrument Preset</label>
            <SlSelect value={settings.preset} onSlChange={handlePresetChange} className="w-full">
              <SlOption value="metal-suite">Metal Suite</SlOption>
              <SlOption value="synth-arena">Synth Arena</SlOption>
              <SlOption value="strings-hybrid">Strings Hybrid</SlOption>
              <SlOption value="percussion-drive">Percussion Drive</SlOption>
            </SlSelect>
            <p className="mt-2 text-xs text-gray-400">
              Presets represent different multi-track templates and will map to real instruments later.
            </p>
          </div>
        </div>
        <div className="space-y-6">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Render Style</label>
            <SlSelect value={settings.style} onSlChange={handleStyleChange} className="w-full">
              <SlOption value="cinematic">Cinematic</SlOption>
              <SlOption value="electronic">Electronic</SlOption>
              <SlOption value="lo-fi">Lo-Fi</SlOption>
              <SlOption value="pop">Pop</SlOption>
            </SlSelect>
            <p className="mt-2 text-xs text-gray-400">
              Select the AI model flavour before rendering. Each style maps to a different set of prompts downstream.
            </p>
          </div>
        </div>
      </div>
      {error && <p className="mt-6 text-xs text-bloodred">{error}</p>}
      {audioUrl && (
        <div className="mt-6 space-y-2">
          <p className="text-xs uppercase tracking-[0.25em] text-gray-500">Latest Render</p>
          <audio controls className="w-full rounded-lg border border-bloodred/40 bg-black/50 p-2">
            <source src={audioUrl} />
            Your browser does not support the audio element.
          </audio>
        </div>
      )}
      <button
        type="button"
        className="metal-button mt-8 w-full rounded-md px-6 py-3 text-sm"
        onClick={onRender}
        disabled={disabled || loading}
      >
        {loading ? "Rendering Audio..." : "Mix & Render to Audio"}
      </button>
    </section>
  );
};

export default MixPanel;
