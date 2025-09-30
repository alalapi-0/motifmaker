import React, { useState } from "react";
import { API_BASE } from "../api";

interface DownloadBarProps {
  midiPath: string | null;
  specPath: string | null;
  onSaveProject: () => Promise<void>;
  onLoadProject: () => Promise<void>;
}

const DownloadBar: React.FC<DownloadBarProps> = ({
  midiPath,
  specPath,
  onSaveProject,
  onLoadProject,
}) => {
  const [busy, setBusy] = useState(false);

  const downloadFile = async (path: string, filename: string) => {
    const response = await fetch(
      `${API_BASE}/download?path=${encodeURIComponent(path)}`
    );
    if (!response.ok) {
      throw new Error("下载失败");
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.URL.revokeObjectURL(url);
  };

  const handleMidiDownload = async () => {
    if (!midiPath) return;
    setBusy(true);
    try {
      const filename = midiPath.split("/").pop() ?? "track.mid";
      await downloadFile(midiPath, filename);
    } finally {
      setBusy(false);
    }
  };

  const handleSpecDownload = async () => {
    if (!specPath) return;
    setBusy(true);
    try {
      const filename = specPath.split("/").pop() ?? "spec.json";
      await downloadFile(specPath, filename);
    } finally {
      setBusy(false);
    }
  };

  const wrapAsync = async (runner: () => Promise<void>) => {
    setBusy(true);
    try {
      await runner();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2 text-xs">
      <button
        type="button"
        className="rounded-md bg-cyan-600 px-3 py-2 font-semibold text-slate-900 disabled:opacity-50"
        onClick={handleMidiDownload}
        disabled={!midiPath || busy}
      >
        下载 MIDI
      </button>
      <button
        type="button"
        className="rounded-md bg-slate-700 px-3 py-2 font-semibold text-slate-100 disabled:opacity-50"
        onClick={handleSpecDownload}
        disabled={!specPath || busy}
      >
        下载 Spec JSON
      </button>
      <button
        type="button"
        className="rounded-md bg-emerald-500 px-3 py-2 font-semibold text-slate-900 disabled:opacity-50"
        onClick={() => wrapAsync(onSaveProject)}
      >
        保存工程
      </button>
      <button
        type="button"
        className="rounded-md bg-amber-500 px-3 py-2 font-semibold text-slate-900 disabled:opacity-50"
        onClick={() => wrapAsync(onLoadProject)}
      >
        载入工程
      </button>
    </div>
  );
};

export default DownloadBar;
