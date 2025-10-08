import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";

/**
 * 轻量级的多语言上下文：本轮仅需中英文切换，因此不引入成熟 i18n 库，
 * 通过手写字典与 Hook 组合满足基础需求。后续若要扩展更多语言，可替换为
 * i18next 等方案，同时保留本文件中对 localStorage、占位插值的约定。
 */
export type Lang = "zh" | "en";

/**
 * 词条键值映射：所有 UI 文案统一从此处读取。
 * - key 采用 "模块.含义" 的形式，便于检索；
 * - value 支持 {{placeholder}} 占位符，用于动态插值。
 */
export const dictionary = {
  zh: {
    "status.running": "运行中",
    "status.idle": "空闲",
    "status.backendHealthy": "后端正常",
    "status.backendIssue": "后端异常",
    "status.lastChecked": "上次检查",
    "status.version": "后端版本",
    "status.environment": "接口地址",
    "status.language": "语言",
    "status.theme": "主题",
    "status.themeLight": "浅色",
    "status.themeDark": "深色",
    "status.refresh": "刷新健康状态",
    "status.healthChecking": "正在检查...",
    "status.healthError": "无法连接后端",

    "prompt.title": "自然语言 Prompt",
    "prompt.subtitle": "描述情绪/配器/时长/段落重点，支持键盘 Tab 导航",
    "prompt.templates": "快速套用模板",
    "prompt.placeholder": "例：城市夜景的 Lo-Fi 节奏，配器包含钢琴与弦乐",
    "prompt.generate": "一键生成",
    "prompt.generating": "生成中...",
    "prompt.keyboardHint": "提示：按 Alt+Enter 也可触发生成",

    "params.title": "参数覆盖",
    "params.subtitle": "调整下次渲染时的关键参数，提交请求前会自动合并并交由后端校验",
    "params.tempo": "速度 (BPM)",
    "params.meter": "拍号",
    "params.key": "调性",
    "params.mode": "调式",
    "params.instrumentation": "配器列表",
    "params.instrumentationHint": "使用逗号分隔，Enter 提交；保留空白表示沿用后端解析结果",
    "params.harmonyOptions": "和声选项",
    "params.secondaryDominant": "启用二级属和声",
    "params.reset": "重置为解析结果",
    "params.resetHint": "撤销前端覆盖，回到最新的后端数据",
    "params.sliderAria": "使用方向键可按步长微调",

    "form.title": "曲式段落表",
    "form.subtitle": "Enter 进入编辑，Esc 取消，方向键在单元格间导航",
    "form.empty": "生成后可在此查看曲式段落，并对每段进行细节调整。",
    "form.column.section": "段落",
    "form.column.bars": "小节数",
    "form.column.tension": "张力",
    "form.column.motif": "动机标签",
    "form.column.freeze": "冻结",
    "form.column.actions": "操作",
    "form.validation.bars": "请输入 1-128 之间的整数",
    "form.validation.tension": "请输入 0-100 之间的整数",
    "form.validation.motif": "动机标签不能为空",
    "form.freezeSelected": "冻结选中的动机",
    "form.freezeHint": "冻结后后端不会再替换对应动机，可批量勾选后执行",
    "form.regenerateMode": "再生成模式",
    "form.regenerateMelodyOnly": "仅旋律",
    "form.regenerateMelodyHarmony": "旋律+和声",
    "form.regenerate": "局部再生成",
    "form.keyboardHelp": "说明：Focus 在单元格时按 Enter 开始编辑，编辑完成后 Enter 保存，Esc 取消。",
    "form.frozenTag": "已冻结",

    "player.title": "在线播放预览",
    "player.subtitle": "提示：浏览器首次播放需用户交互以解除静音策略",
    "player.noMidi": "暂无可播放的 MIDI，请先进行一次生成或渲染。",
    "player.play": "播放",
    "player.pause": "暂停",
    "player.loop": "循环播放",
    "player.loopActive": "循环中",
    "player.seekLabel": "拖动定位",
    "player.elapsed": "当前",
    "player.duration": "总长",
    "player.loading": "正在解析 MIDI...",
    "player.error": "MIDI 解析失败，请检查下载文件是否存在",
    "player.muteHint": "若听不到声音，请确认系统音量或浏览器是否静音",

    "piano.title": "Piano-Roll 可视化",
    "piano.subtitle": "悬停查看音符信息，点击时间轴可与播放器联动",
    "piano.noData": "暂无音符数据，可生成后查看主旋律轨迹。",
    "piano.zoom": "时间缩放",
    "piano.clickToSeek": "点击任意位置可跳转播放进度",
    "piano.hoverPitch": "音高",
    "piano.hoverDuration": "时值",
    "piano.hoverStart": "起始",
    "piano.limitations": "提示：若音符数量很多，可降低缩放倍率或拖动滚动条查看；当前仅展示音高与时值，不含力度。",

    "download.title": "文件与工程管理",
    "download.subtitle": "下载按钮仅提供链接，不会将任何 .mid/.json 纳入仓库",
    "download.midi": "下载 MIDI",
    "download.json": "下载 JSON",
    "download.copyJson": "复制骨架 JSON",
    "download.copySuccess": "已复制到剪贴板",
    "download.copyFail": "复制失败，请检查浏览器权限",
    "download.exportView": "导出当前视图设置",
    "download.viewSaved": "视图设置已保存到本地",
    "download.viewHint": "包含 Piano-Roll 缩放、主题与语言偏好",
    "download.projectPlaceholder": "工程名称，如 city_night_v1",
    "download.save": "保存工程",
    "download.load": "载入工程",

    "json.title": "生成摘要",
    "json.trackStats": "轨道统计",
    "json.projectSpec": "ProjectSpec",
    "json.toggleOpen": "展开 JSON",
    "json.toggleClose": "折叠 JSON",
    "json.empty": "等待生成...",

    "logs.title": "操作日志 (最近 10 条)",
    "logs.empty": "尚无日志，触发生成或渲染后可在此查看状态。",
    "logs.clear": "清空日志",

    "alert.error": "错误",

    "log.generateStart": "开始根据 Prompt 生成骨架",
    "log.generateSuccess": "生成成功，已获取最新 ProjectSpec",
    "log.generateError": "生成失败",
    "log.renderOverride": "已根据覆盖参数重新渲染",
    "log.renderError": "重新渲染失败",
    "log.regenerateStart": "开始局部再生成",
    "log.regenerateSuccess": "局部再生成完成",
    "log.regenerateError": "局部再生成失败",
    "log.freezeStart": "正在冻结选中的动机",
    "log.freezeSuccess": "动机冻结完成",
    "log.freezeError": "冻结动机失败",
    "log.saveStart": "正在保存工程",
    "log.saveSuccess": "工程保存完成",
    "log.saveError": "保存工程失败",
    "log.loadStart": "正在载入工程",
    "log.loadSuccess": "工程载入完成",
    "log.loadError": "载入工程失败",
    "log.midiParseError": "解析 MIDI 失败，Piano-Roll 将暂不可用",
    "log.viewSaved": "视图设置已写入 localStorage",
  },
  en: {
    "status.running": "Running",
    "status.idle": "Idle",
    "status.backendHealthy": "Backend healthy",
    "status.backendIssue": "Backend unreachable",
    "status.lastChecked": "Last check",
    "status.version": "Backend version",
    "status.environment": "API base",
    "status.language": "Language",
    "status.theme": "Theme",
    "status.themeLight": "Light",
    "status.themeDark": "Dark",
    "status.refresh": "Refresh health",
    "status.healthChecking": "Checking...",
    "status.healthError": "Unable to reach backend",

    "prompt.title": "Prompt",
    "prompt.subtitle": "Describe mood/instrumentation/length. Use Tab to move across controls.",
    "prompt.templates": "Templates",
    "prompt.placeholder": "e.g. Lo-Fi at night with piano and strings",
    "prompt.generate": "Generate",
    "prompt.generating": "Generating...",
    "prompt.keyboardHint": "Tip: press Alt+Enter to trigger generation",

    "params.title": "Parameter overrides",
    "params.subtitle": "Adjust values for the next render. Overrides are merged then validated by the backend.",
    "params.tempo": "Tempo (BPM)",
    "params.meter": "Meter",
    "params.key": "Key",
    "params.mode": "Mode",
    "params.instrumentation": "Instrumentation",
    "params.instrumentationHint": "Comma separated list. Leave empty to keep backend defaults.",
    "params.harmonyOptions": "Harmony options",
    "params.secondaryDominant": "Enable secondary dominant",
    "params.reset": "Reset to parsed result",
    "params.resetHint": "Drop local overrides and use the latest backend values",
    "params.sliderAria": "Use arrow keys to fine tune",

    "form.title": "Form table",
    "form.subtitle": "Press Enter to edit, Esc to cancel, arrow keys to move",
    "form.empty": "Generate to see structural sections and tweak details here.",
    "form.column.section": "Section",
    "form.column.bars": "Bars",
    "form.column.tension": "Tension",
    "form.column.motif": "Motif",
    "form.column.freeze": "Freeze",
    "form.column.actions": "Actions",
    "form.validation.bars": "Enter an integer between 1 and 128",
    "form.validation.tension": "Enter an integer between 0 and 100",
    "form.validation.motif": "Motif label is required",
    "form.freezeSelected": "Freeze selected motifs",
    "form.freezeHint": "Frozen motifs won't be replaced during regeneration. Select rows then apply.",
    "form.regenerateMode": "Regeneration mode",
    "form.regenerateMelodyOnly": "Melody only",
    "form.regenerateMelodyHarmony": "Melody + harmony",
    "form.regenerate": "Regenerate",
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
    "piano.subtitle": "Hover to inspect notes. Click timeline to sync with the player.",
    "piano.noData": "No note data yet. Generate a project to inspect the melody track.",
    "piano.zoom": "Time zoom",
    "piano.clickToSeek": "Click to jump to a position",
    "piano.hoverPitch": "Pitch",
    "piano.hoverDuration": "Duration",
    "piano.hoverStart": "Start",
    "piano.limitations": "Tip: with many notes, lower the zoom or scroll around. Only pitch and duration are rendered.",

    "download.title": "Downloads & project",
    "download.subtitle": "Downloads are links only; no MIDI/JSON will enter the repository.",
    "download.midi": "Download MIDI",
    "download.json": "Download JSON",
    "download.copyJson": "Copy project JSON",
    "download.copySuccess": "Copied to clipboard",
    "download.copyFail": "Copy failed. Check clipboard permissions.",
    "download.exportView": "Export view settings",
    "download.viewSaved": "View settings saved locally",
    "download.viewHint": "Includes piano roll zoom, theme and language",
    "download.projectPlaceholder": "Project name, e.g. city_night_v1",
    "download.save": "Save project",
    "download.load": "Load project",

    "json.title": "Summary",
    "json.trackStats": "Track stats",
    "json.projectSpec": "Project spec",
    "json.toggleOpen": "Expand JSON",
    "json.toggleClose": "Collapse JSON",
    "json.empty": "Waiting for data...",

    "logs.title": "Activity log (latest 10)",
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
    "log.freezeError": "Freeze motifs failed",
    "log.saveStart": "Saving project",
    "log.saveSuccess": "Project saved",
    "log.saveError": "Save project failed",
    "log.loadStart": "Loading project",
    "log.loadSuccess": "Project loaded",
    "log.loadError": "Load project failed",
    "log.midiParseError": "Failed to parse MIDI. Piano roll disabled.",
    "log.viewSaved": "View settings stored in localStorage",
  },
} as const;

export type TranslationKey = keyof typeof dictionary.zh;

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
  available: typeof dictionary;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "motifmaker.lang"; // localStorage 键，持久化语言偏好。

/**
 * Provider 负责持久化语言设置、更新 <html lang> 属性，并向下游暴露 t() 函数。
 */
export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const detectDefault = useCallback((): Lang => {
    if (typeof window === "undefined") {
      return "zh"; // SSR 场景兜底使用中文。
    }
    const stored = window.localStorage.getItem(STORAGE_KEY) as Lang | null;
    if (stored === "zh" || stored === "en") {
      return stored;
    }
    const navigatorLang = window.navigator.language.toLowerCase();
    return navigatorLang.startsWith("zh") ? "zh" : "en";
  }, []);

  const [lang, setLangState] = useState<Lang>(detectDefault);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, lang);
      document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    }
  }, [lang]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
  }, []);

  const translate = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>) => {
      const table = dictionary[lang] ?? dictionary.zh;
      const fallback = dictionary.zh;
      const template = table[key] ?? fallback[key] ?? key;
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
