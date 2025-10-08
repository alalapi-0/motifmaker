import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";

// ✅ 当前版本仅保留英文语言，方便国际化扩展：保留 i18n 架构，未来可通过新增 zh/en/jp/fr 等词典 JSON 恢复多语言切换。
export type Lang = "en";

/**
 * 词条键值映射：所有 UI 文案统一从此处读取，保持英文 UI 一致性。
 * - key 仍沿用模块化命名，便于后续扩展更多语言；
 * - value 完全使用英文，避免界面出现中文残留。
 */
export const dictionary = {
  en: {
    "status.running": "Running",
    "status.idle": "Idle",
    "status.backendHealthy": "Backend healthy",
    "status.backendIssue": "Backend unreachable",
    "status.lastChecked": "Last checked",
    "status.version": "Backend version",
    "status.environment": "API base",
    "status.language": "Language",
    "status.theme": "Theme",
    "status.themeLight": "Light",
    "status.themeDark": "Dark",
    "status.refresh": "Refresh health",
    "status.healthChecking": "Checking...",
    "status.healthError": "Unable to reach backend",
    "status.englishOnly": "English Only",

    "prompt.title": "Prompt",
    "prompt.subtitle": "Describe your musical idea: mood, instrumentation, length, and highlights.",
    "prompt.templates": "Prompt Templates",
    "prompt.placeholder": "Enter your musical prompt here...",
    "prompt.generate": "Generate",
    "prompt.generating": "Generating...",
    "prompt.keyboardHint": "Tip: Press Alt+Enter to generate",

    "params.title": "Parameter Overrides",
    "params.subtitle": "Adjust key values for the next render. Overrides are merged then validated by the backend.",
    "params.tempo": "Tempo (BPM)",
    "params.meter": "Meter",
    "params.key": "Key",
    "params.mode": "Mode",
    "params.instrumentation": "Instruments",
    "params.instrumentationHint": "Use commas to separate instruments. Leave empty to keep backend defaults.",
    "params.harmonyOptions": "Harmony Options",
    "params.secondaryDominant": "Enable Secondary Dominant",
    "params.reset": "Reset to Parsed Result",
    "params.resetHint": "Drop local overrides and use the latest backend values",
    "params.sliderAria": "Use arrow keys for fine adjustments",

    "form.title": "Form Structure",
    "form.subtitle": "Press Enter to edit, Esc to cancel, and use arrow keys to move between cells.",
    "form.empty": "Generate to see section data and tweak details here.",
    "form.column.section": "Section",
    "form.column.bars": "Bars",
    "form.column.tension": "Tension",
    "form.column.motif": "Motif",
    "form.column.freeze": "Freeze",
    "form.column.actions": "Action",
    "form.validation.bars": "Enter an integer between 1 and 128",
    "form.validation.tension": "Enter an integer between 0 and 100",
    "form.validation.motif": "Motif label is required",
    "form.freezeSelected": "Freeze Selected Motifs",
    "form.freezeHint": "Frozen motifs won't be replaced during regeneration. Select rows then apply.",
    "form.regenerateMode": "Regeneration Mode",
    "form.regenerateMelodyOnly": "Melody Only",
    "form.regenerateMelodyHarmony": "Melody + Harmony",
    "form.regenerate": "Regenerate Section",
    "form.keyboardHelp": "Tip: focus a cell and press Enter to edit. Press Enter again to commit or Esc to cancel.",
    "form.frozenTag": "Frozen",

    "player.title": "Player",
    "player.subtitle": "Browser requires a user gesture to start audio the first time.",
    "player.noMidi": "No MIDI available. Please generate or render first.",
    "player.play": "Play",
    "player.pause": "Pause",
    "player.loop": "Loop",
    "player.loopActive": "Looping",
    "player.seekLabel": "Seek",
    "player.elapsed": "Elapsed",
    "player.duration": "Duration",
    "player.loading": "Parsing MIDI...",
    "player.error": "Failed to parse MIDI. Check whether the file exists.",
    "player.muteHint": "If no sound plays, check system volume or browser mute settings.",

    "piano.title": "Piano roll",
    "piano.subtitle": "Hover to inspect notes. Click the timeline to sync with the player.",
    "piano.noData": "No note data yet. Generate a project to inspect the melody track.",
    "piano.zoom": "Time zoom",
    "piano.clickToSeek": "Click to jump to a position",
    "piano.hoverPitch": "Pitch",
    "piano.hoverDuration": "Duration",
    "piano.hoverStart": "Start",
    "piano.limitations": "Tip: with many notes, lower the zoom or scroll around. Only pitch and duration are rendered.",

    "download.title": "Downloads & Project",
    "download.subtitle": "Download links only; no MIDI/JSON files are stored in the repository.",
    "download.midi": "Download MIDI",
    "download.json": "Download JSON",
    "download.copyJson": "Copy project JSON",
    "download.copySuccess": "Copied to clipboard",
    "download.copyFail": "Copy failed. Check clipboard permissions.",
    "download.exportView": "Export View Settings",
    "download.viewSaved": "View settings saved locally",
    "download.viewHint": "Includes piano roll zoom and theme preferences.",
    "download.projectPlaceholder": "Project name (e.g. city_night_v1)",
    "download.save": "Save Project",
    "download.load": "Load Project",

    "json.title": "Summary",
    "json.trackStats": "Track Stats",
    "json.projectSpec": "Project Spec",
    "json.toggleOpen": "Expand JSON",
    "json.toggleClose": "Collapse JSON",
    "json.empty": "Waiting for data...",

    "logs.title": "Activity Log (Latest 10)",
    "logs.empty": "No activity yet. Generate or render to populate logs.",
    "logs.clear": "Clear logs",

    "alert.error": "Error",

    "log.generateStart": "Generating project from prompt",
    "log.generateSuccess": "Generation succeeded",
    "log.generateError": "Generation failed",
    "log.renderOverride": "Re-rendered with overrides",
    "log.renderError": "Re-rendering failed",
    "log.regenerateStart": "Regenerating section",
    "log.regenerateSuccess": "Section regeneration completed",
    "log.regenerateError": "Section regeneration failed",
    "log.freezeStart": "Freezing selected motifs",
    "log.freezeSuccess": "Motifs frozen",
    "log.freezeError": "Failed to freeze motifs",
    "log.saveStart": "Saving project",
    "log.saveSuccess": "Project saved successfully",
    "log.saveError": "Failed to save project",
    "log.loadStart": "Loading project",
    "log.loadSuccess": "Project loaded successfully",
    "log.loadError": "Failed to load project",
    "log.midiParseError": "Failed to parse MIDI. Piano roll disabled.",
    "log.viewSaved": "View settings stored in localStorage",
  },
} as const;

export type TranslationKey = keyof typeof dictionary.en;

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
  available: typeof dictionary;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "motifmaker.lang"; // 仍写入 localStorage，便于未来恢复多语言时沿用同一键值。

/**
 * Provider 负责持久化语言设置、更新 <html lang> 属性，并向下游暴露 t() 函数。
 * 当前仅有英文语言，但保留状态与 setter，方便后续扩展其它语言包。
 */
export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const detectDefault = useCallback((): Lang => {
    // 即使未来新增语言，也可在此读取 localStorage 或浏览器偏好；当前直接回退到英文。
    if (typeof window === "undefined") {
      return "en";
    }
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && stored in dictionary) {
      return stored as Lang;
    }
    return "en";
  }, []);

  const [lang, setLangState] = useState<Lang>(detectDefault);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, lang);
      document.documentElement.lang = "en"; // 固定 HTML lang 属性为英文，保障可访问性。
    }
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    // 当前仅支持英文，但保留 setter 以便未来新增语言时直接复用该接口。
    setLangState(next);
  }, []);

  const translate = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>) => {
      const table = dictionary[lang] ?? dictionary.en; // 永远回退到英文，避免缺失时渲染原 key。
      const template = table[key] ?? key;
      if (!vars) {
        return template;
      }
      return template.replace(/{{(\w+)}}/g, (_, token) => {
        const value = vars[token];
        return value !== undefined ? String(value) : `{{${token}}}`;
      });
    },
    [lang]
  );

  const value = useMemo<I18nContextValue>(
    () => ({ lang, setLang, t: translate, available: dictionary }),
    [lang, setLang, translate]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export default I18nContext;
