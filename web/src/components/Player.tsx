import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Midi } from "@tonejs/midi";
import * as Tone from "tone";
import { useI18n } from "../hooks/useI18n";

export interface PlayerProps {
  midiUrl: string | null;
  onProgress?: (time: number) => void;
  onDuration?: (duration: number) => void;
  externalSeek?: number | null;
  onError?: (message: string) => void;
  onSeekApplied?: () => void;
  loopRegion?: { start: number; end: number } | null;
  onLoopRegionChange?: (range: { start: number; end: number } | null) => void;
}

interface ScheduledNote {
  time: number;
  name: string;
  duration: number;
  velocity: number;
}

const Player: React.FC<PlayerProps> = ({
  midiUrl,
  onProgress,
  onDuration,
  externalSeek,
  onError,
  onSeekApplied,
  loopRegion,
  onLoopRegionChange,
}) => {
  const { t } = useI18n();
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [loopEnabled, setLoopEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [internalLoop, setInternalLoop] = useState<{ start: number; end: number } | null>(null);
  const partRef = useRef<Tone.Part | null>(null);
  const synthRef = useRef<Tone.PolySynth | null>(null);
  const rafRef = useRef<number>();
  const abortRef = useRef<AbortController | null>(null);

  const effectiveLoop = loopRegion ?? internalLoop;

  const updateLoopRegion = useCallback(
    (next: { start: number; end: number } | null) => {
      if (onLoopRegionChange) {
        onLoopRegionChange(next);
      }
      if (loopRegion == null) {
        setInternalLoop(next);
      }
    },
    [loopRegion, onLoopRegionChange]
  );

  const disposePlayback = () => {
    partRef.current?.dispose();
    partRef.current = null;
    synthRef.current?.dispose();
    synthRef.current = null;
    Tone.Transport.stop();
    Tone.Transport.cancel();
    setIsPlaying(false);
    setCurrentTime(0);
  };

  useEffect(() => {
    if (!midiUrl) {
      disposePlayback();
      setDuration(0);
      setError(null);
      setInternalLoop(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    disposePlayback();
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    (async () => {
      try {
        const response = await fetch(midiUrl, { signal: controller.signal });
        const buffer = await response.arrayBuffer();
        const midi = new Midi(buffer);
        if (controller.signal.aborted) return;

        const events: ScheduledNote[] = [];
        midi.tracks.forEach((track) => {
          track.notes.forEach((note) => {
            events.push({
              time: note.time,
              name: note.name,
              duration: note.duration,
              velocity: note.velocity,
            });
          });
        });
        events.sort((a, b) => a.time - b.time);

        const synth = new Tone.PolySynth(Tone.Synth, {
          volume: -8,
        }).toDestination();
        synthRef.current = synth;

        const part = new Tone.Part((time, value: ScheduledNote) => {
          synth.triggerAttackRelease(value.name, value.duration, time, value.velocity);
        }, events);
        part.loop = false;
        part.start(0);
        partRef.current = part;

        const midiDuration = midi.duration;
        setDuration(midiDuration);
        onDuration?.(midiDuration);
        setCurrentTime(0);
        updateLoopRegion(null);
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          return;
        }
        const message = t("player.error");
        setError(message);
        onError?.((err as Error).message);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      controller.abort();
      disposePlayback();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [midiUrl]);

  useEffect(() => {
    if (!isPlaying) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = undefined;
      }
      return;
    }

    const tick = () => {
      const time = Tone.Transport.seconds;
      setCurrentTime(time);
      onProgress?.(time);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = undefined;
      }
    };
  }, [isPlaying, onProgress]);

  useEffect(() => {
    if (externalSeek == null || Number.isNaN(externalSeek)) return;
    if (!partRef.current) return;
    const target = Math.max(0, Math.min(duration, externalSeek));
    Tone.Transport.pause();
    Tone.Transport.seconds = target;
    setCurrentTime(target);
    onProgress?.(target);
    if (isPlaying) {
      Tone.Transport.start("+0", target);
    }
    onSeekApplied?.();
  }, [externalSeek, duration, isPlaying, onProgress, onSeekApplied]);

  useEffect(() => {
    if (!loopEnabled) {
      Tone.Transport.loop = false;
      Tone.Transport.loopStart = 0;
      Tone.Transport.loopEnd = duration;
      return;
    }
    const bounds = effectiveLoop ?? { start: 0, end: duration };
    const start = Math.max(0, Math.min(duration, bounds.start));
    const end = Math.max(start + 0.1, Math.min(duration, bounds.end));
    Tone.Transport.loop = true;
    Tone.Transport.loopStart = start;
    Tone.Transport.loopEnd = end;
  }, [loopEnabled, effectiveLoop, duration]);

  const handlePlay = useCallback(
    async (startTime?: number) => {
      if (!partRef.current) return;
      if (Tone.context.state !== "running") {
        await Tone.start();
      }
      const offset = startTime ?? Tone.Transport.seconds;
      Tone.Transport.start("+0", offset);
      setIsPlaying(true);
    },
    []
  );

  const handlePause = useCallback(() => {
    Tone.Transport.pause();
    setIsPlaying(false);
  }, []);

  const handleSeek = (value: number) => {
    const target = Math.max(0, Math.min(duration, value));
    Tone.Transport.pause();
    Tone.Transport.seconds = target;
    setCurrentTime(target);
    onProgress?.(target);
    if (isPlaying) {
      Tone.Transport.start("+0", target);
    }
  };

  const formatSeconds = useCallback((value: number) => {
    const minutes = Math.floor(value / 60);
    const seconds = Math.floor(value % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  }, []);

  const progress = useMemo(() => (duration > 0 ? Math.min(currentTime / duration, 1) : 0), [currentTime, duration]);

  const handleSetLoopStart = () => {
    const end = effectiveLoop?.end ?? duration;
    const start = Math.max(0, Math.min(currentTime, end - 0.1));
    updateLoopRegion({ start, end });
  };

  const handleSetLoopEnd = () => {
    const start = effectiveLoop?.start ?? 0;
    const end = Math.max(start + 0.1, Math.min(duration, currentTime));
    updateLoopRegion({ start, end });
  };

  const handleClearLoop = () => {
    updateLoopRegion(null);
    setLoopEnabled(false);
  };

  return (
    <section className="metal-panel rounded-xl p-6 text-sm text-gray-200">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-white">{t("player.title")}</h3>
        <span className="text-xs text-gray-300">{t("player.subtitle")}</span>
      </header>
      {!midiUrl ? (
        <div className="mt-4 rounded border border-dashed border-gray-700/60 p-6 text-center text-xs text-gray-400">
          {t("player.noMidi")}
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            {isPlaying ? (
              <button type="button" className="metal-button rounded-md px-4 py-2 text-xs" onClick={handlePause} disabled={isLoading}>
                {t("player.pause")}
              </button>
            ) : (
              <button
                type="button"
                className="metal-button rounded-md px-4 py-2 text-xs"
                disabled={isLoading}
                onClick={() => handlePlay(0)}
              >
                {t("player.play")}
              </button>
            )}
            <div className="flex-1">
              <input
                type="range"
                min={0}
                max={duration || 0}
                step={0.01}
                value={duration ? currentTime : 0}
                className="h-2 w-full cursor-pointer rounded-full bg-gray-700"
                aria-label={t("player.seekLabel")}
                onChange={(event) => handleSeek(Number(event.target.value))}
              />
              <div className="mt-1 flex justify-between text-[11px] text-gray-300">
                <span>
                  {t("player.elapsed")}: {formatSeconds(currentTime)}
                </span>
                <span>
                  {t("player.duration")}: {formatSeconds(duration)}
                </span>
              </div>
            </div>
            <label className="flex items-center gap-2 text-xs text-gray-200">
              <input
                type="checkbox"
                className="accent-bloodred"
                checked={loopEnabled}
                onChange={(event) => setLoopEnabled(event.target.checked)}
                disabled={!effectiveLoop}
              />
              {loopEnabled ? "Loop on" : "Loop off"}
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-300">
            <span>
              Loop start: {formatSeconds(effectiveLoop?.start ?? 0)} · Loop end: {formatSeconds(effectiveLoop?.end ?? duration)}
            </span>
            <button type="button" className="metal-button rounded px-3 py-1 text-[11px]" onClick={handleSetLoopStart} disabled={!midiUrl}>
              Set A from cursor
            </button>
            <button type="button" className="metal-button rounded px-3 py-1 text-[11px]" onClick={handleSetLoopEnd} disabled={!midiUrl}>
              Set B from cursor
            </button>
            <button type="button" className="metal-button rounded px-3 py-1 text-[11px]" onClick={handleClearLoop} disabled={!effectiveLoop}>
              Clear loop
            </button>
          </div>

          {isLoading && <p className="text-xs text-gray-300">{t("player.loading")}</p>}
          {error && (
            <div className="rounded border border-bloodred/40 bg-black/50 p-3 text-xs text-gray-100">
              <span className="font-semibold text-white">{error}</span>
            </div>
          )}
          <p className="text-[11px] text-gray-300">{t("player.muteHint")}</p>
        </div>
      )}
    </section>
  );
};

export default Player;
