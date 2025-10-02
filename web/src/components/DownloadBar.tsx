import React, { useState } from "react";

/**
 * DownloadBar 组件：提供 MIDI/JSON 下载链接及工程保存、载入入口。
 * 仅负责组织 UI 与输入，实际的文件访问和持久化操作由上层 App 控制。
 */
export interface DownloadBarProps {
  midiUrl: string | null; // 后端返回的 MIDI 文件完整链接。
  jsonUrl: string | null; // 后端返回的 JSON 文件完整链接。
  onSaveProject: (name: string) => Promise<void>; // 触发保存操作。
  onLoadProject: (name: string) => Promise<void>; // 触发加载操作。
  loading: boolean; // 用于在保存/加载过程中禁用控件。
}

const DownloadBar: React.FC<DownloadBarProps> = ({
  midiUrl,
  jsonUrl,
  onSaveProject,
  onLoadProject,
  loading,
}) => {
  const [projectName, setProjectName] = useState(""); // 前端输入的工程名。

  const handleSave = async () => {
    if (!projectName) {
      alert("请先输入工程名称再保存。");
      return;
    }
    await onSaveProject(projectName);
  };

  const handleLoad = async () => {
    if (!projectName) {
      alert("请先输入要载入的工程名称。");
      return;
    }
    await onLoadProject(projectName);
  };

  return (
    <section className="space-y-3 text-sm text-slate-200">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">文件与工程管理</h3>
        <span className="text-xs text-slate-400">
          下载按钮仅提供文件链接，不会将任何 .mid/.json 提交到仓库。
        </span>
      </header>
      <div className="flex flex-wrap gap-2 text-xs">
        <sl-button
          size="small"
          variant="default"
          href={midiUrl ?? undefined}
          target="_blank"
          rel="noreferrer"
          disabled={!midiUrl}
        >
          下载 MIDI
        </sl-button>
        <sl-button
          size="small"
          variant="default"
          href={jsonUrl ?? undefined}
          target="_blank"
          rel="noreferrer"
          disabled={!jsonUrl}
        >
          下载 JSON
        </sl-button>
      </div>
      <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
        <sl-input
          placeholder="工程名称，如 city_night_v1"
          value={projectName}
          onSlChange={(event) => {
            const target = event.target as HTMLInputElement;
            setProjectName(target.value);
          }}
        ></sl-input>
        <sl-button size="small" variant="primary" disabled={loading} onClick={handleSave}>
          保存工程
        </sl-button>
        <sl-button size="small" variant="text" disabled={loading} onClick={handleLoad}>
          载入工程
        </sl-button>
      </div>
    </section>
  );
};

export default DownloadBar;
