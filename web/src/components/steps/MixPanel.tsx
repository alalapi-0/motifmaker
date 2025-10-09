import React, { useCallback, useEffect, useMemo, useState } from "react";
import { SlRadio, SlRadioGroup } from "@shoelace-style/shoelace/dist/react";
import type { SlChangeEvent } from "@shoelace-style/shoelace/dist/events/events";

import { AudioRenderResult, configPublic, renderAudio, resolveAssetUrl } from "../../api";
import FriendlyError, { FriendlyErrorState } from "../FriendlyError";

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
  const [error, setError] = useState<FriendlyErrorState | null>(null);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<string>("placeholder");

  useEffect(() => {
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
    if (lastMidiPath) {
      setSource("last");
    } else {
      setSource("upload");
    }
  }, [lastMidiPath]);

  const resolvedMidiUrl = useMemo(() => resolveAssetUrl(lastMidiUrl), [lastMidiUrl]);

  const handleSourceChange = useCallback((event: SlChangeEvent) => {
    const target = event.target as HTMLInputElement;
    const value = (target?.value ?? "") as SourceOption;
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
      const details = (err as Error).message;
      setError({ summary: "Audio render failed. Please try again.", details });
    } finally {
      setLoading(false);
    }
  }, [source, uploadFile, lastMidiPath, style, intensity, onAudioRendered]);

  return (
    <section className="metal-panel rounded-xl p-8 text-sm leading-relaxed text-gray-200">
      <header className="mb-6 flex flex-col gap-2">
        <h2 className="text-2xl font-semibold text-white">Mix &amp; Render</h2>
        <p className="text-sm text-gray-300">
          Convert your MIDI into an audio preview. This placeholder engine emits a sine wave but keeps the workflow intact.
        </p>
        <p className="text-xs uppercase tracking-[0.3em] text-bloodred">
          {audioUrl ? "Preview ready" : "Render audio to unlock the final step"}
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-5">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-300">Source</label>
            <SlRadioGroup value={source} onSlChange={handleSourceChange} className="space-y-2 text-sm">
              <SlRadio value="last" disabled={!canUseLast}>
                Use last generated MIDI
              </SlRadio>
              <SlRadio value="upload">Upload MIDI</SlRadio>
            </SlRadioGroup>
            {source === "last" && resolvedMidiUrl && (
              <p className="mt-2 text-xs text-gray-300">
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
                  className="block w-full text-xs text-gray-200 file:mr-4 file:rounded-md file:border-0 file:bg-bloodred/80 file:px-4 file:py-2 file:text-white"
                />
                <p className="mt-2 text-xs text-gray-300">
                  Upload a local MIDI file to render with the placeholder engine.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-5">
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-300">Style</label>
            <select
              value={style}
              onChange={handleStyleChange}
              className="w-full rounded-md border border-bloodred/40 bg-black/60 px-4 py-2 text-sm text-gray-100 focus-visible:border-bloodred focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-bloodred/60"
            >
              {STYLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-gray-300">
              Style influences downstream model selection once external providers are integrated.
            </p>
          </div>
          <div>
            <label className="mb-2 block text-xs uppercase tracking-[0.25em] text-gray-300">Intensity</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={intensity}
              onChange={handleIntensityChange}
              className="w-full"
            />
            <p className="mt-2 text-xs text-gray-300">Controls how energetic the placeholder waveform should sound.</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mt-6">
          <FriendlyError {...error} />
        </div>
      )}

      {audioUrl && (
        <div className="mt-8 space-y-2">
          <p className="text-xs uppercase tracking-[0.3em] text-gray-300">Latest audio preview</p>
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
        disabled={
          loading || (source === "last" && !lastMidiPath) || (source === "upload" && !uploadFile)
        }
      >
        {loading ? "Rendering..." : "Mix & Render to Audio"}
      </button>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-300">
        <span>
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
