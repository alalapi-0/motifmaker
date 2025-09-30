import React, { useCallback, useEffect, useRef, useState } from "react";
import * as Tone from "tone";
import { Midi } from "@tonejs/midi";
import { API_BASE } from "../api";

interface PlayerProps {
  midiPath: string | null;
}

const Player: React.FC<PlayerProps> = ({ midiPath }) => {
  const [loading, setLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const midiRef = useRef<Midi | null>(null);
  const partsRef = useRef<Tone.Part[]>([]);
  const synthsRef = useRef<Tone.PolySynth[]>([]);
  const rafRef = useRef<number>();
  const totalDurationRef = useRef<number>(0);

  const stopPlayback = useCallback(() => {
    Tone.Transport.stop();
    Tone.Transport.cancel();
    partsRef.current.forEach((part) => part.dispose());
    partsRef.current = [];
    synthsRef.current.forEach((synth) => synth.dispose());
    synthsRef.current = [];
    setIsPlaying(false);
    setProgress(0);
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
    }
  }, []);

  useEffect(() => {
    // midiPath 变化时停止播放并释放资源。
    stopPlayback();
    midiRef.current = null;
  }, [midiPath, stopPlayback]);

  useEffect(() => {
    // 组件卸载时清理 Tone 资源。
    return () => {
      stopPlayback();
    };
  }, [stopPlayback]);

  const updateProgress = useCallback(() => {
    if (!isPlaying || totalDurationRef.current === 0) {
      setProgress(0);
      return;
    }
    const ratio = Tone.Transport.seconds / totalDurationRef.current;
    setProgress(Math.min(1, ratio));
    rafRef.current = requestAnimationFrame(updateProgress);
  }, [isPlaying]);

  const ensureMidiLoaded = useCallback(async () => {
    if (!midiPath) {
      return;
    }
    if (midiRef.current) {
      return;
    }
    setLoading(true);
    try {
      const url = `${API_BASE}/download?path=${encodeURIComponent(midiPath)}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("无法加载 MIDI 文件");
      }
      const arrayBuffer = await response.arrayBuffer();
      midiRef.current = new Midi(arrayBuffer);
      totalDurationRef.current = midiRef.current.duration;
    } finally {
      setLoading(false);
    }
  }, [midiPath]);

  const startPlayback = useCallback(async () => {
    if (!midiPath) {
      return;
    }
    await ensureMidiLoaded();
    if (!midiRef.current) {
      return;
    }
    await Tone.start();
    stopPlayback();
    const midi = midiRef.current;
    midi.tracks.forEach((track) => {
      const synth = new Tone.PolySynth(Tone.Synth).toDestination();
      synthsRef.current.push(synth);
      const part = new Tone.Part((time, note) => {
        synth.triggerAttackRelease(note.name, note.duration, time);
      }, track.notes);
      part.start(0);
      partsRef.current.push(part);
    });
    Tone.Transport.seconds = 0;
    Tone.Transport.start();
    setIsPlaying(true);
    rafRef.current = requestAnimationFrame(updateProgress);
  }, [ensureMidiLoaded, midiPath, stopPlayback, updateProgress]);

  return (
    <div className="rounded-md border border-slate-700 p-4 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-semibold">在线播放</span>
        <div className="space-x-2">
          <button
            type="button"
            className="rounded-md bg-emerald-500 px-3 py-1 text-xs font-semibold text-slate-900 disabled:opacity-50"
            onClick={startPlayback}
            disabled={!midiPath || loading}
          >
            {loading ? "加载中..." : "播放"}
          </button>
          <button
            type="button"
            className="rounded-md bg-rose-500 px-3 py-1 text-xs font-semibold text-slate-900"
            onClick={stopPlayback}
          >
            停止
          </button>
        </div>
      </div>
      <div className="mt-3 h-2 w-full rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-cyan-500 transition-all"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>
      {!midiPath && (
        <p className="mt-2 text-xs text-slate-400">生成完成后可以在此处试听。</p>
      )}
    </div>
  );
};

export default Player;
