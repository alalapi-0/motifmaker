import React, { useEffect, useRef, useState } from "react";
import { Midi } from "@tonejs/midi";
import * as Tone from "tone";

/**
 * Player 组件：利用 Tone.js 播放后端生成的 MIDI，用于在浏览器中快速预听。
 * 设计重点：
 * 1. 解析 @tonejs/midi 返回的多轨数据，合成到一个简单的 PolySynth 上播放；
 * 2. 避免浏览器自动播放限制，必须由用户点击播放按钮才能启动音频上下文；
 * 3. 通过 Tone.Transport 与 requestAnimationFrame 更新进度条，确保时间同步。
 */
export interface PlayerProps {
  midiUrl: string | null; // 可播放的 MIDI 文件地址，若为空则显示占位提示。
}

interface ScheduledNote {
  time: number; // 音符触发时间（秒）
  name: string; // 音高名称，例如 C4
  duration: number; // 持续时长（秒）
  velocity: number; // 力度（0-1）
}

const Player: React.FC<PlayerProps> = ({ midiUrl }) => {
  const [isLoading, setIsLoading] = useState(false); // 是否正在解析 MIDI。
  const [isPlaying, setIsPlaying] = useState(false); // 播放状态，用于切换按钮。
  const [duration, setDuration] = useState(0); // 当前 MIDI 的总时长（秒）。
  const [currentTime, setCurrentTime] = useState(0); // 播放进度（秒）。
  const partRef = useRef<Tone.Part | null>(null); // Tone.Part 用于调度音符。
  const synthRef = useRef<Tone.PolySynth | null>(null); // PolySynth 合成器实例。
  const rafRef = useRef<number>(); // requestAnimationFrame 句柄，便于停止进度刷新。

  // 清理函数：停止播放并释放 Tone 资源。
  const disposePlayback = () => {
    partRef.current?.dispose();
    partRef.current = null;
    synthRef.current?.dispose();
    synthRef.current = null;
    Tone.Transport.stop();
    Tone.Transport.cancel(0);
    setIsPlaying(false);
    setCurrentTime(0);
  };

  useEffect(() => {
    // 当 midiUrl 变化时，重新加载并解析 MIDI。
    if (!midiUrl) {
      disposePlayback();
      setDuration(0);
      return;
    }

    let isCancelled = false; // 防止异步过程中组件卸载。
    setIsLoading(true);
    disposePlayback();

    (async () => {
      try {
        const response = await fetch(midiUrl);
        const buffer = await response.arrayBuffer();
        const midi = new Midi(buffer);

        if (isCancelled) return;

        // 将所有轨道的音符合并为一个数组，按时间排序用于 Tone.Part 调度。
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
          volume: -8, // 将音量适当降低，避免合成音过响。
        }).toDestination();
        synthRef.current = synth;

        const part = new Tone.Part((time, value: ScheduledNote) => {
          // Tone.Part 回调在 Transport 时钟上执行，确保多轨同步。
          synth.triggerAttackRelease(value.name, value.duration, time, value.velocity);
        }, events);
        part.loop = false; // 仅播放一次。
        part.stop(midi.duration);
        partRef.current = part;
        setDuration(midi.duration);
        setCurrentTime(0);
      } catch (error) {
        console.error("MIDI 解析失败", error);
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      isCancelled = true;
      disposePlayback();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [midiUrl]);

  // 更新进度条：每帧读取 Tone.Transport.seconds。
  useEffect(() => {
    if (!isPlaying) {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = undefined;
      }
      return;
    }

    const update = () => {
      setCurrentTime(Tone.Transport.seconds);
      rafRef.current = requestAnimationFrame(update);
    };
    rafRef.current = requestAnimationFrame(update);

    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = undefined;
      }
    };
  }, [isPlaying]);

  const handlePlay = async () => {
    if (!partRef.current) return;
    if (Tone.context.state !== "running") {
      // 浏览器自动播放策略：必须通过用户交互启动音频上下文。
      await Tone.start();
    }
    Tone.Transport.stop();
    Tone.Transport.position = 0;
    partRef.current?.start(0);
    Tone.Transport.start();
    setIsPlaying(true);
  };

  const handlePause = () => {
    Tone.Transport.pause();
    setIsPlaying(false);
  };

  const formatSeconds = (value: number) => {
    const minutes = Math.floor(value / 60);
    const seconds = Math.floor(value % 60)
      .toString()
      .padStart(2, "0");
    return `${minutes}:${seconds}`;
  };

  const progress = duration > 0 ? Math.min(currentTime / duration, 1) : 0;

  return (
    <section className="space-y-3 text-sm text-slate-200">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">在线播放预览</h3>
        <span className="text-xs text-slate-400">
          浏览器回放仅为粗略预听，实际编曲以 DAW 渲染为准。
        </span>
      </header>
      {!midiUrl ? (
        <div className="rounded-md border border-dashed border-slate-700 p-4 text-center text-xs text-slate-400">
          暂无可播放的 MIDI，请先进行一次生成。
        </div>
      ) : (
        <div className="space-y-3 rounded-md border border-slate-700 bg-slate-900/40 p-4">
          <div className="flex items-center gap-3">
            {isPlaying ? (
              <sl-button size="small" variant="danger" onClick={handlePause} disabled={isLoading}>
                暂停
              </sl-button>
            ) : (
              <sl-button size="small" variant="primary" onClick={handlePlay} disabled={isLoading}>
                播放
              </sl-button>
            )}
            <div className="flex-1">
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-cyan-500"
                  style={{ width: `${progress * 100}%` }}
                ></div>
              </div>
              <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                <span>当前：{formatSeconds(currentTime)}</span>
                <span>总长：{formatSeconds(duration)}</span>
              </div>
            </div>
          </div>
          {isLoading && (
            <p className="text-xs text-slate-400">正在解析 MIDI，请稍候...</p>
          )}
        </div>
      )}
    </section>
  );
};

export default Player;
