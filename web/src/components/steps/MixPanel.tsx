import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SlAlert, SlRadio, SlRadioGroup } from "@shoelace-style/shoelace/dist/react";

import { AudioRenderResult, configPublic, renderAudio, resolveAssetUrl } from "../../api";

/**
 * MixPanel 组件：在流程的混音阶段触发音频渲染，占位实现会在本地生成正弦波音频。
 * 中文注释：
 * - 该阶段负责将前序生成的 MIDI 转化为可试听的 WAV，未来只需替换 renderAudio 的实现即可接入外部 AI 服务；
 * - 组件内部管理上传/路径选择、风格与强度调节，并在成功后将结果回传给父组件；
 * - 保持 UI 文案为英文，方便后续接入国际化或设计系统。
 */

const STYLE_OPTIONS = ["cinematic", "electronic", "lo-fi", "pop"] as const;
export type StyleOption = (typeof STYLE_OPTIONS)[number];

type SourceOption = "last" | "upload";

interface MixPanelProps {
  lastMidiPath: string | null;
  lastMidiUrl: string | null;
  audioUrl: string | null;
  style: StyleOption;
  intensity: number;
  onStyleChange: (value: StyleOption) => void;
  onIntensityChange: (value: number) => void;
  onAudioRendered: (payload: { resolvedUrl: string; rawUrl: string; meta: AudioRenderResult }) => void;
}

const MixPanel: React.FC<MixPanelProps> = ({
  lastMidiPath,
  lastMidiUrl,
  audioUrl,
  style,
  intensity,
  onStyleChange,
  onIntensityChange,
  onAudioRendered,
}) => {
  const canUseLast = Boolean(lastMidiPath);
  const [source, setSource] = useState<SourceOption>(canUseLast ? "last" : "upload");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<string>("placeholder");

  useEffect(() => {
    // 中文注释：首次挂载时读取公开配置，获知当前音频 Provider 类型供 UI 提示使用。
    let cancelled = false;
    const controller = new AbortController();
    configPublic(controller.signal)
      .then((info) => {
        if (!cancelled) {
          setProvider(info.audio_provider);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setProvider("unknown");
        }
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    // 中文注释：当新的 MIDI 路径生成时，默认切换为“使用最近一次生成的 MIDI”。
    if (lastMidiPath) {
      setSource("last");
    } else {
      setSource("upload");
    }
  }, [lastMidiPath]);

  const resolvedMidiUrl = useMemo(() => resolveAssetUrl(lastMidiUrl), [lastMidiUrl]);

  const handleSourceChange = useCallback((event: CustomEvent<{ value: string }>) => {
    const value = event.detail.value as SourceOption;
    setSource(value);
    setError(null);
  }, []);

  const handleFileChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setUploadFile(file);
    setError(null);
  }, []);

  const handleStyleChange = useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      onStyleChange(event.target.value as StyleOption);
    },
    [onStyleChange]
  );

  const handleIntensityChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      onIntensityChange(Number(event.target.value));
    },
    [onIntensityChange]
  );

  const handleRender = useCallback(async () => {
    // 中文注释：调用 renderAudio 前重置错误提示并显示加载状态。
    setError(null);
    setLoading(true);
    try {
      let file: File | undefined;
      let midiPath: string | undefined;

      if (source === "upload") {
        if (!uploadFile) {
          throw new Error("Please upload a MIDI file first.");
        }
        file = uploadFile;
      } else {
        if (!lastMidiPath) {
          throw new Error("No generated MIDI found. Upload one instead.");
        }
        midiPath = lastMidiPath;
      }

      const result = await renderAudio({
        file,
        midiPath,
        style,
        intensity,
      });

      const resolved = resolveAssetUrl(result.audio_url);
      if (!resolved) {
        throw new Error("Audio URL missing from render response.");
      }

      onAudioRendered({ resolvedUrl: resolved, rawUrl: result.audio_url, meta: result });
    } catch (err) {
      const message = (err as Error).message || "Audio render failed. Please try again later.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [source, uploadFile, lastMidiPath, style, intensity, onAudioRendered]);

  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Mix & Render</h2>
        <p className="text-sm text-gray-400">
          Convert your MIDI into an audio preview. This placeholder engine emits a sine wave but keeps the workflow intact.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-5">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Source</label>
            <SlRadioGroup value={source} onSlChange={handleSourceChange} className="space-y-2">
              <SlRadio value="last" disabled={!canUseLast}>
                Use last generated MIDI
              </SlRadio>
              <SlRadio value="upload">Upload MIDI</SlRadio>
            </SlRadioGroup>
            {source === "last" && resolvedMidiUrl && (
              <p className="mt-2 text-xs text-gray-400">
                Latest MIDI: <a href={resolvedMidiUrl} className="text-bloodred underline" download>
                  Download reference
                </a>
              </p>
            )}
            {source === "upload" && (
              <div className="mt-3">
                <input
                  type="file"
                  accept=".mid,.midi"
                  onChange={handleFileChange}
                  className="block w-full text-xs text-gray-300 file:mr-4 file:rounded-md file:border-0 file:bg-bloodred/80 file:px-4 file:py-2 file:text-white"
                />
                <p className="mt-2 text-xs text-gray-500">
                  Upload a local MIDI file to render with the placeholder engine.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-5">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Style</label>
            <select
              value={style}
              onChange={handleStyleChange}
              className="w-full rounded-md border border-bloodred/40 bg-black/60 px-4 py-2 text-sm text-gray-200 focus:border-bloodred focus:outline-none"
            >
              {STYLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-gray-500">
              Style influences downstream model selection once external providers are integrated.
            </p>
          </div>
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-500">Intensity</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={intensity}
              onChange={handleIntensityChange}
              className="w-full"
            />
            <p className="mt-2 text-xs text-gray-500">Controls how energetic the placeholder waveform should sound.</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-6">
          <SlAlert variant="danger" open>
            <strong slot="title">Render failed</strong>
            <span slot="message">{error}</span>
          </SlAlert>
        </div>
      )}

      {audioUrl && (
        <div className="mt-8 space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-gray-500">Latest audio preview</p>
          <audio controls className="w-full rounded-lg border border-bloodred/40 bg-black/60 p-2">
            <source src={audioUrl} />
            Your browser does not support the audio element.
          </audio>
          <a href={audioUrl} download className="text-xs text-bloodred underline">
            Download preview WAV
          </a>
        </div>
      )}

      <button
        type="button"
        className="metal-button mt-8 w-full rounded-md px-6 py-3 text-sm"
        onClick={handleRender}
        disabled={loading || (source === "last" && !lastMidiPath) || (source === "upload" && !uploadFile)}
      >
        {loading ? "Rendering..." : "Mix & Render to Audio"}
      </button>

      <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>
          {/* 中文注释：保持文案为英文，仅展示当前后端 Provider 名称，帮助用户识别是否为模拟渲染。 */}
          Audio Provider: {provider}
        </span>
        {provider.toLowerCase() === "placeholder" && (
          <span className="rounded border border-bloodred px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-bloodred">
            Simulation
          </span>
        )}
      </div>
    </section>
  );
};

export default MixPanel;
