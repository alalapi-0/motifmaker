import React, { useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { useI18n } from "../hooks/useI18n";

export interface PianoRollNote {
  pitch: number;
  start: number;
  duration: number;
  velocity?: number;
}

export interface PianoRollProps {
  notes: PianoRollNote[];
  duration: number;
  currentTime: number;
  scale: number;
  onScaleChange: (value: number) => void;
  onSeek?: (time: number) => void;
  onSelectNote?: (note: PianoRollNote | null) => void;
  selectedNote?: PianoRollNote | null;
  loopRegion?: { start: number; end: number } | null;
  onLoopRegionChange?: (range: { start: number; end: number } | null) => void;
}

const MIN_SCALE = 40;
const MAX_SCALE = 240;
const ROW_HEIGHT = 14;

const isSameNote = (a: PianoRollNote | null, b: PianoRollNote | null) => {
  if (!a || !b) return false;
  return a.pitch === b.pitch && Math.abs(a.start - b.start) < 1e-6 && Math.abs(a.duration - b.duration) < 1e-6;
};

const PianoRoll: React.FC<PianoRollProps> = ({
  notes,
  duration,
  currentTime,
  scale,
  onScaleChange,
  onSeek,
  onSelectNote,
  selectedNote,
  loopRegion,
  onLoopRegionChange,
}) => {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [hover, setHover] = useState<{ note: PianoRollNote; x: number; y: number } | null>(null);
  const draggingRef = useRef(false);
  const dragStartRef = useRef<{ x: number; y: number; scrollLeft: number; scrollTop: number } | null>(null);
  const pointerMovedRef = useRef(false);
  const selectionDraftRef = useRef<{ startTime: number; startClientX: number } | null>(null);
  const [internalSelectedNote, setInternalSelectedNote] = useState<PianoRollNote | null>(null);
  const [selection, setSelection] = useState<{ start: number; end: number } | null>(null);
  const [selectionDraft, setSelectionDraft] = useState<{ start: number; end: number } | null>(null);
  const [internalLoop, setInternalLoop] = useState<{ start: number; end: number } | null>(null);

  const effectiveSelectedNote = selectedNote ?? internalSelectedNote;
  const effectiveLoop = loopRegion ?? internalLoop;

  const updateSelected = (note: PianoRollNote | null) => {
    onSelectNote?.(note);
    if (selectedNote === undefined) {
      setInternalSelectedNote(note);
    }
  };

  const updateLoop = (range: { start: number; end: number } | null) => {
    onLoopRegionChange?.(range);
    if (loopRegion === undefined) {
      setInternalLoop(range);
    }
  };

  const pitchRange = useMemo(() => {
    if (!notes.length) {
      return { min: 60, max: 72 };
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
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.fillStyle = getComputedStyle(wrapper).getPropertyValue("--piano-bg") || "#0f172a";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "rgba(148, 163, 184, 0.18)";
    ctx.lineWidth = 1;
    for (let i = 0; i <= pitchCount; i++) {
      const y = i * ROW_HEIGHT;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    for (let x = 0; x <= duration * scale; x += scale) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    notes.forEach((note) => {
      const x = note.start * scale;
      const noteWidth = Math.max(note.duration * scale, 2);
      const y = (pitchRange.max - note.pitch) * ROW_HEIGHT;
      const isPrimary = note.velocity ? note.velocity > 0.8 : false;
      const isSelected = isSameNote(note, effectiveSelectedNote);
      ctx.fillStyle = isSelected
        ? "rgba(229, 9, 20, 0.85)"
        : isPrimary
        ? "rgba(59, 130, 246, 0.9)"
        : "rgba(14, 165, 233, 0.85)";
      ctx.fillRect(x, y + 1, noteWidth, ROW_HEIGHT - 2);
      if (isSelected) {
        ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
        ctx.lineWidth = 1.4;
        ctx.strokeRect(x, y + 1, noteWidth, ROW_HEIGHT - 2);
      }
    });

    if (effectiveLoop) {
      const loopX = effectiveLoop.start * scale;
      const loopWidth = Math.max((effectiveLoop.end - effectiveLoop.start) * scale, 2);
      ctx.fillStyle = "rgba(229, 9, 20, 0.08)";
      ctx.fillRect(loopX, 0, loopWidth, height);
      ctx.strokeStyle = "rgba(229, 9, 20, 0.6)";
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(loopX, 0, loopWidth, height);
      ctx.setLineDash([]);
    }

    const activeSelection = selectionDraft ?? selection;
    if (activeSelection) {
      const selectX = Math.min(activeSelection.start, activeSelection.end) * scale;
      const selectWidth = Math.max(Math.abs(activeSelection.end - activeSelection.start) * scale, 2);
      ctx.fillStyle = "rgba(59, 130, 246, 0.12)";
      ctx.fillRect(selectX, 0, selectWidth, height);
      ctx.strokeStyle = "rgba(59, 130, 246, 0.7)";
      ctx.setLineDash([4, 3]);
      ctx.strokeRect(selectX, 0, selectWidth, height);
      ctx.setLineDash([]);
    }

    const cursorX = currentTime * scale;
    ctx.strokeStyle = "rgba(248, 113, 113, 0.9)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cursorX, 0);
    ctx.lineTo(cursorX, height);
    ctx.stroke();
  }, [currentTime, duration, notes, pixelDimensions, pitchRange.max, pitchRange.min, scale, effectiveSelectedNote, selection, selectionDraft, effectiveLoop]);

  const handlePointerDown: React.PointerEventHandler<HTMLDivElement> = (event) => {
    if (!wrapperRef.current) return;
    pointerMovedRef.current = false;
    if (event.shiftKey) {
      const rect = wrapperRef.current.getBoundingClientRect();
      const offsetX = event.clientX - rect.left + wrapperRef.current.scrollLeft;
      const time = Math.max(0, Math.min(duration, offsetX / scale));
      selectionDraftRef.current = { startTime: time, startClientX: event.clientX };
      setSelectionDraft({ start: time, end: time });
      wrapperRef.current.setPointerCapture(event.pointerId);
      return;
    }

    draggingRef.current = true;
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
    if (selectionDraftRef.current) {
      pointerMovedRef.current = true;
      const rect = wrapperRef.current.getBoundingClientRect();
      const offsetX = event.clientX - rect.left + wrapperRef.current.scrollLeft;
      const time = Math.max(0, Math.min(duration, offsetX / scale));
      setSelectionDraft({ start: selectionDraftRef.current.startTime, end: time });
      return;
    }
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
    if (selectionDraftRef.current) {
      const rect = wrapperRef.current.getBoundingClientRect();
      const offsetX = event.clientX - rect.left + wrapperRef.current.scrollLeft;
      const time = Math.max(0, Math.min(duration, offsetX / scale));
      const start = selectionDraftRef.current.startTime;
      const range = { start: Math.min(start, time), end: Math.max(start, time) };
      selectionDraftRef.current = null;
      setSelectionDraft(null);
      if (Math.abs(range.end - range.start) > 0.05) {
        setSelection(range);
      } else {
        setSelection(null);
      }
      pointerMovedRef.current = false;
      return;
    }

    if (draggingRef.current && dragStartRef.current) {
      draggingRef.current = false;
      if (!pointerMovedRef.current && onSeek) {
        const rect = wrapperRef.current.getBoundingClientRect();
        const offsetX = event.clientX - rect.left + wrapperRef.current.scrollLeft;
        const time = Math.max(0, Math.min(duration, offsetX / scale));
        onSeek(time);
      }
    } else if (!pointerMovedRef.current) {
      if (hover?.note) {
        const alreadySelected = isSameNote(hover.note, effectiveSelectedNote);
        updateSelected(alreadySelected ? null : hover.note);
      } else {
        updateSelected(null);
      }
    }
    pointerMovedRef.current = false;
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
      (note) => pitch === note.pitch && time >= note.start && time <= note.start + note.duration
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

  const handleZoomToSelection = () => {
    if (!selection || !wrapperRef.current) return;
    const selectionDuration = Math.max(0.1, selection.end - selection.start);
    const availableWidth = wrapperRef.current.clientWidth || 640;
    const nextScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, availableWidth / selectionDuration));
    onScaleChange(nextScale);
    wrapperRef.current.scrollLeft = selection.start * nextScale;
  };

  const handleLoopFromSelection = () => {
    if (!selection) return;
    updateLoop(selection);
  };

  const handleClearSelection = () => {
    setSelection(null);
    setSelectionDraft(null);
  };

  return (
    <section className="metal-panel rounded-xl p-6 text-sm text-gray-200">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">{t("piano.title")}</h3>
          <p className="text-xs text-gray-300">{t("piano.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-gray-300" htmlFor="piano-roll-scale">
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
            className="h-2 w-36 cursor-ew-resize appearance-none rounded-full bg-gray-700"
            onChange={(event) => onScaleChange(Number(event.target.value))}
          />
        </div>
      </div>
      <p className="mt-2 text-[11px] text-gray-300">{t("piano.limitations")}</p>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-gray-300">
        <button type="button" className="metal-button rounded px-3 py-1 text-[11px]" onClick={handleZoomToSelection} disabled={!selection}>
          Zoom to selection
        </button>
        <button type="button" className="metal-button rounded px-3 py-1 text-[11px]" onClick={handleLoopFromSelection} disabled={!selection}>
          Loop selection
        </button>
        <button type="button" className="metal-button rounded px-3 py-1 text-[11px]" onClick={handleClearSelection} disabled={!selection && !selectionDraft}>
          Clear selection
        </button>
        {selection && (
          <span>
            {t("piano.hoverDuration")}: {(selection.end - selection.start).toFixed(2)}s
          </span>
        )}
        {effectiveSelectedNote && (
          <span>
            Selected note · Pitch {effectiveSelectedNote.pitch} · Start {effectiveSelectedNote.start.toFixed(2)}s
          </span>
        )}
      </div>

      {!notes.length ? (
        <div className="mt-4 rounded border border-dashed border-gray-700/60 p-6 text-center text-xs text-gray-400">
          {t("piano.noData")}
        </div>
      ) : (
        <div
          ref={wrapperRef}
          className={clsx(
            "relative mt-4 max-h-96 overflow-auto rounded-md border border-gray-700/70 bg-black/80",
            "[--piano-bg:rgba(9,12,16,0.96)]"
          )}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          role="application"
          aria-label={t("piano.clickToSeek")}
        >
          <canvas ref={canvasRef} onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave} />
          {hover && (
            <div
              className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded bg-black/90 px-2 py-1 text-[11px] text-gray-100 shadow-lg"
              style={{
                left: hover.x - (wrapperRef.current?.getBoundingClientRect().left ?? 0),
                top: hover.y - (wrapperRef.current?.getBoundingClientRect().top ?? 0),
              }}
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
