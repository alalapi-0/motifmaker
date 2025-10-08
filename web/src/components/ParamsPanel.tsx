import React, { useMemo } from "react";
import { ParamOverrides, ProjectSpec } from "../api";
import { useI18n } from "../hooks/useI18n";

export interface ParamsPanelProps {
  projectSpec: ProjectSpec | null; // 当前后端下发的规格，可为空。
  overrides: ParamOverrides; // 用户在前端调整的临时参数。
  onOverridesChange: (next: ParamOverrides) => void; // 通知上层更新覆盖值。
  onResetOverrides: () => void; // 恢复为最新解析结果。
  disabled?: boolean; // 当请求执行中时禁用控件。
}

/**
 * ParamsPanel 组件：展示并修改 Tempo、拍号、调式、配器与和声选项等覆盖参数。
 * - 重置按钮可撤销所有覆盖并恢复为最新解析结果；
 * - Slider/Select/Input 均补充了键盘操作提示，符合可访问性要求；
 * - instrumentation 文本框采用逗号分隔，便于快速批量编辑。
 */
const ParamsPanel: React.FC<ParamsPanelProps> = ({
  projectSpec,
  overrides,
  onOverridesChange,
  onResetOverrides,
  disabled,
}) => {
  const { t } = useI18n();

  const effectiveTempo = overrides.tempo_bpm ?? projectSpec?.tempo_bpm ?? 100;
  const effectiveMeter = overrides.meter ?? projectSpec?.meter ?? "4/4";
  const effectiveKey = overrides.key ?? projectSpec?.key ?? "C";
  const effectiveMode = overrides.mode ?? projectSpec?.mode ?? "major";
  const effectiveInstrumentation = overrides.instrumentation ?? projectSpec?.instrumentation ?? [];
  const useSecondaryDominant =
    overrides.harmony_options?.use_secondary_dominant ?? projectSpec?.use_secondary_dominant ?? false;

  const instrumentationInput = useMemo(
    () => effectiveInstrumentation.join(", "),
    [effectiveInstrumentation]
  );

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("params.title")}</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">{t("params.subtitle")}</p>
        </div>
        <button
          type="button"
          className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 transition hover:border-slate-400 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
          onClick={onResetOverrides}
          disabled={disabled}
        >
          {t("params.reset")}
        </button>
      </header>

      <div className="space-y-3">
        <label className="block text-xs text-slate-500 dark:text-slate-400">
          <span className="mb-1 block font-medium text-slate-900 dark:text-slate-200">{t("params.tempo")}</span>
          <sl-slider
            min={40}
            max={220}
            step={1}
            value={effectiveTempo}
            disabled={disabled}
            aria-label={t("params.tempo")}
            onSlChange={(event: CustomEvent) => {
              const target = event.target as HTMLInputElement;
              onOverridesChange({
                ...overrides,
                tempo_bpm: Number(target.value),
              });
            }}
          ></sl-slider>
          {/* Shoelace Slider 默认支持左右方向键按步长调整，提示文本在段落中说明。*/}
          <span className="mt-1 block text-[11px] text-slate-400 dark:text-slate-500">{effectiveTempo} BPM · {t("params.sliderAria")}</span>
        </label>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-xs text-slate-500 dark:text-slate-400">
            <span className="font-medium text-slate-900 dark:text-slate-200">{t("params.meter")}</span>
            <sl-select
              value={effectiveMeter}
              disabled={disabled}
              onSlChange={(event: CustomEvent) => {
                const target = event.target as HTMLSelectElement;
                onOverridesChange({
                  ...overrides,
                  meter: target.value,
                });
              }}
            >
              <sl-option value="4/4">4/4</sl-option>
              <sl-option value="3/4">3/4</sl-option>
            </sl-select>
          </label>

          <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400">
            <label className="space-y-1">
              <span className="font-medium text-slate-900 dark:text-slate-200">{t("params.key")}</span>
              <sl-input
                value={effectiveKey}
                disabled={disabled}
                onSlChange={(event: CustomEvent) => {
                  const target = event.target as HTMLInputElement;
                  onOverridesChange({
                    ...overrides,
                    key: target.value.toUpperCase(),
                  });
                }}
              ></sl-input>
            </label>
            <label className="space-y-1">
              <span className="font-medium text-slate-900 dark:text-slate-200">{t("params.mode")}</span>
              <sl-select
                value={effectiveMode}
                disabled={disabled}
                onSlChange={(event: CustomEvent) => {
                  const target = event.target as HTMLSelectElement;
                  onOverridesChange({
                    ...overrides,
                    mode: target.value,
                  });
                }}
              >
                <sl-option value="major">Major</sl-option>
                <sl-option value="minor">Minor</sl-option>
                <sl-option value="dorian">Dorian</sl-option>
              </sl-select>
            </label>
          </div>
        </div>

        <label className="block text-xs text-slate-500 dark:text-slate-400">
          <span className="mb-1 block font-medium text-slate-900 dark:text-slate-200">{t("params.instrumentation")}</span>
          <sl-textarea
            value={instrumentationInput}
            placeholder="piano, strings, bass"
            disabled={disabled}
            onSlChange={(event: CustomEvent) => {
              const target = event.target as HTMLTextAreaElement;
              const raw = target.value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean);
              onOverridesChange({
                ...overrides,
                instrumentation: raw.length > 0 ? raw : undefined,
              });
            }}
          ></sl-textarea>
          <span className="mt-1 block text-[11px] text-slate-400 dark:text-slate-500">{t("params.instrumentationHint")}</span>
        </label>

        <div className="rounded-md border border-slate-200 bg-slate-100 p-3 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
          <label className="flex items-center gap-2">
            <span className="font-medium text-slate-900 dark:text-slate-200">{t("params.harmonyOptions")}</span>
            <sl-switch
              checked={useSecondaryDominant}
              disabled={disabled}
              onSlChange={(event: CustomEvent) => {
                const target = event.target as HTMLInputElement;
                onOverridesChange({
                  ...overrides,
                  harmony_options: {
                    ...overrides.harmony_options,
                    use_secondary_dominant: target.checked,
                  },
                });
              }}
            ></sl-switch>
            <span>{t("params.secondaryDominant")}</span>
          </label>
        </div>
      </div>
    </section>
  );
};

export default ParamsPanel;
