import React, { useState } from "react";
import { useI18n } from "../hooks/useI18n";

export interface DownloadBarProps {
  midiUrl: string | null; // 后端返回的 MIDI 文件完整链接。
  jsonUrl: string | null; // 后端返回的 JSON 文件完整链接。
  projectJson: string; // 当前 ProjectSpec 的 JSON 字符串，用于复制。
  onSaveProject: (name: string) => Promise<void> | void; // 触发保存操作。
  onLoadProject: (name: string) => Promise<void> | void; // 触发加载操作。
  onExportView: () => Promise<void> | void; // 导出视图设置到 localStorage。
  saveLoading: boolean; // 保存按钮的加载状态。
  loadLoading: boolean; // 载入按钮的加载状态。
  exportLoading: boolean; // 导出视图设置按钮状态。
}

/**
 * DownloadBar 组件：集中管理下载、复制、视图导出与工程保存/载入入口。
 * - 新增复制骨架 JSON 与导出视图设置（写入 localStorage）的能力；
 * - 保存/载入按钮根据各自请求状态展示 Shoelace loading 动画；
 * - 使用本地状态提示操作结果，便于用户确认。
 */
const DownloadBar: React.FC<DownloadBarProps> = ({
  midiUrl,
  jsonUrl,
  projectJson,
  onSaveProject,
  onLoadProject,
  onExportView,
  saveLoading,
  loadLoading,
  exportLoading,
}) => {
  const { t } = useI18n();
  const [projectName, setProjectName] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleSave = async () => {
    if (!projectName.trim()) {
      setFeedback(t("download.projectPlaceholder"));
      return;
    }
    await onSaveProject(projectName.trim());
    setFeedback(t("log.saveSuccess"));
  };

  const handleLoad = async () => {
    if (!projectName.trim()) {
      setFeedback(t("download.projectPlaceholder"));
      return;
    }
    await onLoadProject(projectName.trim());
    setFeedback(t("log.loadSuccess"));
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(projectJson);
      setFeedback(t("download.copySuccess"));
    } catch (error) {
      console.error("copy failed", error);
      setFeedback(t("download.copyFail"));
    }
  };

  const handleExportView = async () => {
    await onExportView();
    setFeedback(t("download.viewSaved"));
  };

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-900 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{t("download.title")}</h3>
        <span className="text-xs text-slate-500 dark:text-slate-400">{t("download.subtitle")}</span>
      </header>
      <div className="flex flex-wrap gap-2 text-xs">
        <sl-button size="small" variant="default" href={midiUrl ?? undefined} target="_blank" rel="noreferrer" disabled={!midiUrl}>
          {t("download.midi")}
        </sl-button>
        <sl-button size="small" variant="default" href={jsonUrl ?? undefined} target="_blank" rel="noreferrer" disabled={!jsonUrl}>
          {t("download.json")}
        </sl-button>
        <sl-button size="small" variant="default" disabled={!projectJson} onClick={handleCopy}>
          {t("download.copyJson")}
        </sl-button>
        <sl-button size="small" variant="default" disabled={exportLoading} loading={exportLoading} onClick={handleExportView}>
          {t("download.exportView")}
        </sl-button>
      </div>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">{t("download.viewHint")}</p>
      <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
        <sl-input
          placeholder={t("download.projectPlaceholder")}
          value={projectName}
          onSlChange={(event: CustomEvent) => {
            const target = event.target as HTMLInputElement; // Shoelace 输入组件的 target 即为内部 input。
            setProjectName(target.value);
          }}
        ></sl-input>
        <sl-button size="small" variant="primary" disabled={saveLoading} loading={saveLoading} onClick={handleSave}>
          {t("download.save")}
        </sl-button>
        <sl-button size="small" variant="default" disabled={loadLoading} loading={loadLoading} onClick={handleLoad}>
          {t("download.load")}
        </sl-button>
      </div>
      {feedback && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400">{feedback}</p>
      )}
    </section>
  );
};

export default DownloadBar;
