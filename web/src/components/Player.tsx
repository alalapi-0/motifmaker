import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Midi } from "@tonejs/midi";
import * as Tone from "tone";
import { useI18n } from "../hooks/useI18n";

export interface PlayerProps {
  midiUrl: string | null; // 可播放的 MIDI 文件地址，若为空则显示占位提示。
  onProgress?: (time: number) => void; // 播放进度回调，驱动 Piano-Roll 光标。
  onDuration?: (duration: number) => void; // 当解析出时长后通知上层。
  externalSeek?: number | null; // 来自 Piano-Roll 的定位请求。
  onError?: (message: string) => void; // 解析失败时上报错误。
  onSeekApplied?: () => void; // Player 完成外部 seek 后通知上层清理状态。
}

interface ScheduledNote {
  time: number; // 音符触发时间（秒）。
  name: string; // 音高名称，例如 C4。
  duration: number; // 持续时长（秒）。
  velocity: number; // 力度（0-1）。
}

const Player: React.FC<PlayerProps> = ({ midiUrl, onProgress, onDuration, externalSeek, onError, onSeekApplied }) => {
  const { t } = useI18n();
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [loop, setLoop] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const partRef = useRef<Tone.Part | null>(null);
  const synthRef = useRef<Tone.PolySynth | null>(null);
  const rafRef = useRef<number>();
  const abortRef = useRef<AbortController | null>(null);

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
    Tone.Transport.loop = loop;
    Tone.Transport.loopEnd = duration;
  }, [duration, loop]);

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
    Tone.Transport.seconds = target; // Tone.Transport 的 seconds 表示从播放开始的绝对秒数。
    setCurrentTime(target);
    onProgress?.(target);
    if (isPlaying) {
      Tone.Transport.start("+0", target); // 第二个参数为 offset，实现快速定位。
    }
    onSeekApplied?.();
  }, [externalSeek, duration, isPlaying, onProgress, onSeekApplied]);

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
    Tone.Transport.seconds = target; // Tone.Transport.seconds 与 UI 的秒数一致，可直接写入。
    setCurrentTime(target);
    onProgress?.(target);
    if (isPlaying) {
      Tone.Transport.start("+0", target); // 第二个参数 offset 指定从哪一秒开始继续播放。
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

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm text-sm text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{t("player.title")}</h3>
        <span className="text-xs text-slate-500 dark:text-slate-400">{t("player.subtitle")}</span>
      </header>
      {!midiUrl ? (
        <div className="rounded border border-dashed border-slate-300 p-4 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
          {t("player.noMidi")}
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            {isPlaying ? (
              <sl-button size="small" variant="default" onClick={handlePause} disabled={isLoading}>
                {t("player.pause")}
              </sl-button>
            ) : (
              <sl-button
                size="small"
                variant="primary"
                disabled={isLoading}
                onClick={() => handlePlay(0)}
              >
                {t("player.play")}
              </sl-button>
            )}
            <div className="flex-1">
              <input
                type="range"
                min={0}
                max={duration || 0}
                step={0.01}
                value={duration ? currentTime : 0}
                className="h-2 w-full cursor-pointer rounded-full bg-slate-200 dark:bg-slate-700"
                aria-label={t("player.seekLabel")}
                onChange={(event) => handleSeek(Number(event.target.value))}
              />
              <div className="mt-1 flex justify-between text-[11px] text-slate-500 dark:text-slate-400">
                <span>
                  {t("player.elapsed")}: {formatSeconds(currentTime)}
                </span>
                <span>
                  {t("player.duration")}: {formatSeconds(duration)}
                </span>
              </div>
            </div>
            <label className="flex items-center gap-1 text-xs text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                checked={loop}
                onChange={(event) => setLoop(event.target.checked)}
              />
              {loop ? t("player.loopActive") : t("player.loop")}
            </label>
          </div>
          {isLoading && <p className="text-xs text-slate-500 dark:text-slate-400">{t("player.loading")}</p>}
          {error && (
            <sl-alert variant="danger" open>
              <span slot="icon">⚠️</span>
              {error}
            </sl-alert>
          )}
          <p className="text-[11px] text-slate-500 dark:text-slate-400">{t("player.muteHint")}</p>
        </div>
      )}
    </section>
  );
};

export default Player;
