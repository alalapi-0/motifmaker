import React, { useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "../hooks/useI18n";

/**
 * 已知限制：
 * 1. 当音符数量非常多时（>2000），Canvas 绘制会产生性能压力，建议降低时间缩放倍率或仅显示部分轨道；
 * 2. 当前仅根据音高与时值绘制矩形，不展示音量/力度等高级信息；
 * 3. 若前端从 .mid 解析数据，不同浏览器的 ArrayBuffer 解码速度略有差异，应在日志中提示潜在延迟。
 */
export interface PianoRollNote {
  pitch: number; // MIDI 音高编号，例如 60 表示 C4。
  start: number; // 起始时间（秒）。
  duration: number; // 持续时间（秒）。
  velocity?: number; // 力度，当前仅用于 hover 提示。
}

export interface PianoRollProps {
  notes: PianoRollNote[];
  duration: number; // 曲目总时长，用于绘制时间轴与光标。
  currentTime: number; // 播放器传入的当前时间，驱动光标移动。
  scale: number; // 每秒对应的像素数，用于缩放。
  onScaleChange: (value: number) => void; // 调整缩放倍率时通知上层持久化。
  onSeek?: (time: number) => void; // 用户点击时间轴时触发播放器定位。
}

const MIN_SCALE = 40; // 每秒最少 40 像素，避免过度压缩导致难以辨认。
const MAX_SCALE = 240; // 每秒最多 240 像素，兼顾细节与性能。
const ROW_HEIGHT = 14; // 单个音高行高。

const PianoRoll: React.FC<PianoRollProps> = ({
  notes,
  duration,
  currentTime,
  scale,
  onScaleChange,
  onSeek,
}) => {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hover, setHover] = useState<{ note: PianoRollNote; x: number; y: number } | null>(null);
  const draggingRef = useRef(false); // 记录当前是否处于拖拽平移状态。
  const dragStartRef = useRef<{ x: number; y: number; scrollLeft: number; scrollTop: number } | null>(null);
  const pointerMovedRef = useRef(false); // 用于判定点击是否发生拖拽，从而决定是否触发 onSeek。

  const pitchRange = useMemo(() => {
    if (!notes.length) {
      return { min: 60, max: 72 }; // 默认显示 C4-C5 区间，避免画布空白。
    }
    const pitches = notes.map((note) => note.pitch);
    return {
      min: Math.min(...pitches),
      max: Math.max(...pitches),
    };
  }, [notes]);

  const pixelDimensions = useMemo(() => {
    const pitchCount = pitchRange.max - pitchRange.min + 1;
    const width = Math.max(duration * scale + 100, wrapperRef.current?.clientWidth ?? 640);
    const height = Math.max(pitchCount * ROW_HEIGHT, 200);
    return { width, height, pitchCount };
  }, [duration, pitchRange.max, pitchRange.min, scale]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrapper = wrapperRef.current;
    if (!canvas || !wrapper) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const { width, height, pitchCount } = pixelDimensions;
    const dpr = window.devicePixelRatio || 1; // 根据设备像素比提升清晰度。
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // 背景填充：根据主题使用不同色值，提升层次感。
    ctx.fillStyle = getComputedStyle(wrapper).getPropertyValue("--piano-bg");
    if (!ctx.fillStyle) {
      ctx.fillStyle = "#0f172a";
    }
    ctx.fillRect(0, 0, width, height);

    // 绘制水平网格线（每个音高一条），方便识别音程关系。
    ctx.strokeStyle = "rgba(148, 163, 184, 0.2)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= pitchCount; i++) {
      const y = i * ROW_HEIGHT;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // 绘制时间网格线：每秒一条，帮助定位节奏。
    ctx.strokeStyle = "rgba(56, 189, 248, 0.15)";
    for (let x = 0; x <= duration * scale; x += scale) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // 绘制音符块。
    notes.forEach((note) => {
      const x = note.start * scale;
      const noteWidth = Math.max(note.duration * scale, 2); // 宽度至少 2 像素避免丢失。
      const y = (pitchRange.max - note.pitch) * ROW_HEIGHT;
      const isPrimary = note.velocity ? note.velocity > 0.8 : false;
      ctx.fillStyle = isPrimary ? "rgba(59, 130, 246, 0.9)" : "rgba(14, 165, 233, 0.85)";
      ctx.fillRect(x, y + 1, noteWidth, ROW_HEIGHT - 2);
    });

    // 绘制播放光标。
    const cursorX = currentTime * scale;
    ctx.strokeStyle = "rgba(248, 113, 113, 0.9)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cursorX, 0);
    ctx.lineTo(cursorX, height);
    ctx.stroke();
  }, [currentTime, duration, notes, pixelDimensions, pitchRange.max, pitchRange.min, scale]);

  const handlePointerDown: React.PointerEventHandler<HTMLDivElement> = (event) => {
    if (!wrapperRef.current) return;
    draggingRef.current = true;
    pointerMovedRef.current = false;
    dragStartRef.current = {
      x: event.clientX,
      y: event.clientY,
      scrollLeft: wrapperRef.current.scrollLeft,
      scrollTop: wrapperRef.current.scrollTop,
    };
    wrapperRef.current.setPointerCapture(event.pointerId);
  };

  const handlePointerMove: React.PointerEventHandler<HTMLDivElement> = (event) => {
    if (!wrapperRef.current) return;
    if (draggingRef.current && dragStartRef.current) {
      pointerMovedRef.current = true;
      const deltaX = event.clientX - dragStartRef.current.x;
      const deltaY = event.clientY - dragStartRef.current.y;
      wrapperRef.current.scrollLeft = dragStartRef.current.scrollLeft - deltaX;
      wrapperRef.current.scrollTop = dragStartRef.current.scrollTop - deltaY;
    }
  };

  const handlePointerUp: React.PointerEventHandler<HTMLDivElement> = (event) => {
    if (!wrapperRef.current) return;
    wrapperRef.current.releasePointerCapture(event.pointerId);
    draggingRef.current = false;
    if (!pointerMovedRef.current && onSeek) {
      const rect = wrapperRef.current.getBoundingClientRect();
      const offsetX = event.clientX - rect.left + wrapperRef.current.scrollLeft;
      const time = Math.max(0, Math.min(duration, offsetX / scale));
      onSeek(time);
    }
  };

  const handleMouseMove: React.MouseEventHandler<HTMLCanvasElement> = (event) => {
    if (!wrapperRef.current) return;
    const rect = wrapperRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left + wrapperRef.current.scrollLeft;
    const y = event.clientY - rect.top + wrapperRef.current.scrollTop;
    const pitchIndex = Math.floor(y / ROW_HEIGHT);
    const pitch = pitchRange.max - pitchIndex;
    const time = x / scale;

    const hovered = notes.find(
      (note) =>
        pitch === note.pitch &&
        time >= note.start &&
        time <= note.start + note.duration
    );
    if (hovered) {
      setHover({ note: hovered, x: event.clientX, y: event.clientY });
    } else {
      setHover(null);
    }
  };

  const handleMouseLeave: React.MouseEventHandler<HTMLCanvasElement> = () => {
    setHover(null);
  };

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{t("piano.title")}</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">{t("piano.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 dark:text-slate-400" htmlFor="piano-roll-scale">
            {t("piano.zoom")}
          </label>
          <input
            id="piano-roll-scale"
            type="range"
            min={MIN_SCALE}
            max={MAX_SCALE}
            step={10}
            value={scale}
            aria-valuemin={MIN_SCALE}
            aria-valuemax={MAX_SCALE}
            aria-label={t("piano.zoom")}
            className="h-2 w-36 cursor-ew-resize appearance-none rounded-full bg-slate-200 dark:bg-slate-700"
            onChange={(event) => onScaleChange(Number(event.target.value))}
          />
        </div>
      </div>
      <p className="text-[11px] text-slate-500 dark:text-slate-400">{t("piano.limitations")}</p>
      {!notes.length ? (
        <div className="rounded border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
          {t("piano.noData")}
        </div>
      ) : (
        <div
          ref={wrapperRef}
          className={clsx(
            "relative max-h-96 overflow-auto rounded-md border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-950",
            "[--piano-bg:theme(colors.slate.950)] dark:[--piano-bg:theme(colors.slate.900)]"
          )}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          role="application"
          aria-label={t("piano.clickToSeek")}
        >
          <canvas
            ref={canvasRef}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          />
          {hover && (
            <div
              className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded bg-slate-900 px-2 py-1 text-[11px] text-white shadow-lg dark:bg-slate-700"
              style={{ left: hover.x - (wrapperRef.current?.getBoundingClientRect().left ?? 0), top: hover.y - (wrapperRef.current?.getBoundingClientRect().top ?? 0) }}
            >
              <div>{t("piano.hoverPitch")}: {hover.note.pitch}</div>
              <div>{t("piano.hoverDuration")}: {hover.note.duration.toFixed(2)}s</div>
              <div>{t("piano.hoverStart")}: {hover.note.start.toFixed(2)}s</div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default PianoRoll;
