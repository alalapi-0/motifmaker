import React from "react";
import clsx from "clsx";
import { ParamOverrides, ProjectSpec } from "../api";

/**
 * ParamsPanel 组件：展示节奏、调性、配器等参数的临时覆盖控件。
 * 这些参数不会直接修改当前 ProjectSpec，而是在提交请求时由 App 合并，
 * 这样可以保持前端灵活性，同时确保后端拥有最终解释权。
 */
export interface ParamsPanelProps {
  projectSpec: ProjectSpec | null; // 当前后端下发的规格，可为空。
  overrides: ParamOverrides; // 用户在前端调整的临时参数。
  onOverridesChange: (next: ParamOverrides) => void; // 通知上层更新覆盖值。
}

const INSTRUMENT_OPTIONS = [
  "piano",
  "strings",
  "synth pad",
  "drums",
  "bass",
  "woodwinds",
];

const ParamsPanel: React.FC<ParamsPanelProps> = ({
  projectSpec,
  overrides,
  onOverridesChange,
}) => {
  // 帮助函数：生成新的覆盖对象，保持不可变数据结构。
  const setOverride = <K extends keyof ParamOverrides>(key: K, value: ParamOverrides[K]) => {
    onOverridesChange({
      ...overrides,
      [key]: value,
    });
  };

  const effectiveTempo = overrides.tempo_bpm ?? projectSpec?.tempo_bpm ?? 100; // 展示值优先使用覆盖，其次是后端原值，最后兜底默认。
  const effectiveMeter = overrides.meter ?? projectSpec?.meter ?? "4/4";
  const effectiveKey = overrides.key ?? projectSpec?.key ?? "C";
  const effectiveMode = overrides.mode ?? projectSpec?.mode ?? "major";
  const effectiveInstrumentation = overrides.instrumentation ?? projectSpec?.instrumentation ?? ["piano"];
  const useSecondaryDominant = overrides.harmony_options?.use_secondary_dominant ?? projectSpec?.harmony_options?.use_secondary_dominant ?? false;

  return (
    <section className="space-y-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-sm">
      <header className="space-y-1">
        <h2 className="text-sm font-semibold text-slate-200">参数覆盖</h2>
        <p className="text-xs text-slate-400">
          下方调节项只影响下一次请求的 payload，后端会在生成时合并这些覆盖值并进行合法性校验。
        </p>
      </header>

      <div className="space-y-2">
        <label className="text-xs font-medium text-slate-300">Tempo (BPM)</label>
        <sl-slider
          min={60}
          max={140}
          step={1}
          value={effectiveTempo}
          onSlChange={(event) => {
            // Shoelace Slider 的 value 为字符串或数字，统一转为数字存储。
            const target = event.target as HTMLInputElement;
            setOverride("tempo_bpm", Number(target.value));
          }}
        ></sl-slider>
        <span className="text-xs text-slate-400">当前：{effectiveTempo} BPM</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-2 text-xs text-slate-300">
          <span className="font-medium">拍号 (Meter)</span>
          <sl-select
            value={effectiveMeter}
            onSlChange={(event) => {
              const target = event.target as HTMLSelectElement;
              setOverride("meter", target.value);
            }}
          >
            <sl-option value="4/4">4/4</sl-option>
            <sl-option value="3/4">3/4</sl-option>
          </sl-select>
        </label>

        <label className="space-y-2 text-xs text-slate-300">
          <span className="font-medium">调性 (Key / Mode)</span>
          <div className="grid grid-cols-2 gap-2">
            <sl-input
              value={effectiveKey}
              placeholder="C"
              onSlChange={(event) => {
                const target = event.target as HTMLInputElement;
                setOverride("key", target.value.toUpperCase());
              }}
            ></sl-input>
            <sl-select
              value={effectiveMode}
              onSlChange={(event) => {
                const target = event.target as HTMLSelectElement;
                setOverride("mode", target.value);
              }}
            >
              <sl-option value="major">Major</sl-option>
              <sl-option value="minor">Minor</sl-option>
              <sl-option value="dorian">Dorian</sl-option>
            </sl-select>
          </div>
        </label>
      </div>

      <div className="space-y-2">
        <span className="text-xs font-medium text-slate-300">Instrumentation 配器选择</span>
        <div className="flex flex-wrap gap-2">
          {INSTRUMENT_OPTIONS.map((instrument) => {
            const checked = effectiveInstrumentation.includes(instrument);
            return (
              <label
                key={instrument}
                className={clsx(
                  "flex items-center gap-2 rounded-full border px-3 py-1 text-xs",
                  checked ? "border-cyan-400 bg-cyan-500/20" : "border-slate-700"
                )}
              >
                <sl-checkbox
                  checked={checked}
                  onSlChange={(event) => {
                    const target = event.target as HTMLInputElement;
                    const next = new Set(effectiveInstrumentation);
                    if (target.checked) {
                      next.add(instrument);
                    } else {
                      next.delete(instrument);
                    }
                    setOverride("instrumentation", Array.from(next));
                  }}
                ></sl-checkbox>
                {instrument}
              </label>
            );
          })}
        </div>
        <p className="text-xs text-slate-400">
          覆盖配器时仅调整提交给后端的列表，后端仍会根据实际可用音色进行裁剪或补全。
        </p>
      </div>

      <div className="rounded-md bg-slate-800/60 p-3 text-xs text-slate-300">
        <label className="flex items-center gap-2">
          <sl-switch
            checked={useSecondaryDominant}
            onSlChange={(event) => {
              const target = event.target as HTMLInputElement;
              setOverride("harmony_options", {
                ...overrides.harmony_options,
                use_secondary_dominant: target.checked,
              });
            }}
          ></sl-switch>
          启用二级属和声（useSecondaryDominant）
        </label>
        <p className="mt-2 text-[11px] text-slate-400">
          说明：若开启该选项，后端会优先尝试在和声生成时插入二级属功能；若后端认为当前调性不适合，会自动忽略。
        </p>
      </div>
    </section>
  );
};

export default ParamsPanel;
