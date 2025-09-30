import React, { useEffect, useState } from "react";
import { GenerateOptions } from "../api";

interface ParamState {
  key: string;
  mode: string;
  tempo_bpm: number;
  meter: string;
  instrumentation: string[];
}

interface ParamsPanelProps {
  state: ParamState;
  options: GenerateOptions;
  selectedTracks: string[];
  onStateChange: (updates: Partial<ParamState>) => void;
  onOptionsChange: (updates: Partial<GenerateOptions>) => void;
  onTracksChange: (tracks: string[]) => void;
}

const ALL_TRACKS = ["melody", "harmony", "bass", "percussion"];
const ALL_INSTRUMENTS = [
  "piano",
  "strings",
  "acoustic-guitar",
  "synth-pad",
  "brass",
  "percussion",
];

const ParamsPanel: React.FC<ParamsPanelProps> = ({
  state,
  options,
  selectedTracks,
  onStateChange,
  onOptionsChange,
  onTracksChange,
}) => {
  const [mood, setMood] = useState(60);

  useEffect(() => {
    // 当用户调整情绪滑块时映射到 harmony_level，50 以下视为 basic，以上为 colorful。
    const harmony_level = mood < 50 ? "basic" : "colorful";
    if (options.harmony_level !== harmony_level) {
      onOptionsChange({ harmony_level });
    }
  }, [mood, onOptionsChange, options.harmony_level]);

  const toggleTrack = (track: string) => {
    const set = new Set(selectedTracks);
    if (set.has(track)) {
      set.delete(track);
    } else {
      set.add(track);
    }
    onTracksChange(Array.from(set));
  };

  const toggleInstrument = (instrument: string) => {
    const set = new Set(state.instrumentation);
    if (set.has(instrument)) {
      set.delete(instrument);
    } else {
      set.add(instrument);
    }
    onStateChange({ instrumentation: Array.from(set) });
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-slate-300">情绪强度</label>
        <input
          type="range"
          min={0}
          max={100}
          value={mood}
          onChange={(event) => setMood(Number(event.target.value))}
          className="w-full"
        />
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <label className="flex flex-col space-y-1">
          <span>调性</span>
          <select
            className="rounded-md bg-slate-800 p-2"
            value={state.key}
            onChange={(event) => onStateChange({ key: event.target.value })}
          >
            {["C", "D", "E", "F", "G", "A", "Bb", "Eb"].map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col space-y-1">
          <span>调式</span>
          <select
            className="rounded-md bg-slate-800 p-2"
            value={state.mode}
            onChange={(event) => onStateChange({ mode: event.target.value })}
          >
            <option value="major">大调</option>
            <option value="minor">小调</option>
          </select>
        </label>
        <label className="flex flex-col space-y-1">
          <span>速度 (BPM)</span>
          <input
            type="number"
            className="rounded-md bg-slate-800 p-2"
            value={state.tempo_bpm}
            onChange={(event) =>
              onStateChange({ tempo_bpm: Number(event.target.value) })
            }
          />
        </label>
        <label className="flex flex-col space-y-1">
          <span>拍号</span>
          <select
            className="rounded-md bg-slate-800 p-2"
            value={state.meter}
            onChange={(event) => onStateChange({ meter: event.target.value })}
          >
            {["4/4", "3/4", "6/8"].map((meter) => (
              <option key={meter} value={meter}>
                {meter}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="space-y-2 text-xs">
        <span className="font-semibold">配器选择</span>
        <div className="grid grid-cols-2 gap-2">
          {ALL_INSTRUMENTS.map((instrument) => {
            const checked = state.instrumentation.includes(instrument);
            return (
              <label key={instrument} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleInstrument(instrument)}
                />
                <span>{instrument}</span>
              </label>
            );
          })}
        </div>
      </div>
      <div className="space-y-2 text-xs">
        <span className="font-semibold">导出分轨</span>
        <div className="grid grid-cols-2 gap-2">
          {ALL_TRACKS.map((track) => {
            const checked = selectedTracks.includes(track);
            return (
              <label key={track} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleTrack(track)}
                />
                <span>{track}</span>
              </label>
            );
          })}
        </div>
      </div>
      <div className="space-y-2 text-xs">
        <span className="font-semibold">动机风格</span>
        <select
          className="w-full rounded-md bg-slate-800 p-2"
          value={options.motif_style ?? ""}
          onChange={(event) =>
            onOptionsChange({ motif_style: event.target.value || undefined })
          }
        >
          <option value="">自动</option>
          <option value="ascending_arc">上行回落</option>
          <option value="wavering">波浪</option>
          <option value="zigzag">曲折</option>
        </select>
      </div>
      <div className="space-y-2 text-xs">
        <span className="font-semibold">节奏密度</span>
        <select
          className="w-full rounded-md bg-slate-800 p-2"
          value={options.rhythm_density ?? ""}
          onChange={(event) =>
            onOptionsChange({ rhythm_density: event.target.value || undefined })
          }
        >
          <option value="">自动</option>
          <option value="low">稀疏</option>
          <option value="medium">适中</option>
          <option value="high">紧凑</option>
        </select>
      </div>
    </div>
  );
};

export default ParamsPanel;
