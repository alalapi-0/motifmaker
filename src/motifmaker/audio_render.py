"""
audio_render.py
说明：本模块提供“音频渲染”API 的占位实现。
- 支持上传 MIDI 或传入已存在的 midi_path
- 当前采用纯本地合成一个短正弦波 wav 作为“渲染占位”
- 未来可在 render_via_provider() 中接入 MusicGen/Mubert 等外部服务
"""

from __future__ import annotations

import time
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

from .config import OUTPUT_DIR
from .errors import MMError, ValidationError, RenderError
from .logging_setup import get_logger
from .utils import ensure_directory

# 中文注释：FastAPI 路由集中在此处，prefix 统一为 /render，方便前端调用。
router = APIRouter(prefix="/render", tags=["AudioRender"])
logger = get_logger(__name__)

# 中文注释：兼容旧的工具函数命名，避免重复实现。
ensure_dir = ensure_directory


def _safe_outputs_dir() -> Path:
    """中文注释：确保输出目录存在，且禁止目录穿越。"""

    out = ensure_dir(OUTPUT_DIR)
    return out


def _sine_wav(path: Path, seconds: float = 6.0, samplerate: int = 44100, freq: float = 440.0) -> float:
    """
    生成一段正弦波 wav（占位渲染），返回时长（秒）。
    中文注释：在没有接入真实 AI 的情况下，用该方法快速得到可播放的音频文件。
    """

    t = np.linspace(0, seconds, int(samplerate * seconds), endpoint=False)
    # 中文注释：加入淡入淡出避免音频瞬态造成爆音，幅度控制在 0.2 以内降低音量。
    fade = np.linspace(0, 1, len(t))
    waveform = 0.2 * np.sin(2 * np.pi * freq * t) * fade
    waveform_int16 = (waveform * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 中文注释：16-bit 采样宽度即可满足占位需求。
        wf.setframerate(samplerate)
        wf.writeframes(waveform_int16.tobytes())
    return seconds


def _derive_audio_name(midi_name: str) -> str:
    """中文注释：基于 midi 文件名 + 时间戳派生一个不冲突的 wav 名称。"""

    stem = Path(midi_name).stem or "track"
    ts = int(time.time())
    return f"{stem}_{ts}.wav"


def render_via_provider(midi_path: Path, style: str, intensity: float) -> Path:
    """
    中文注释：真实渲染入口（预留壳）。
    当前返回占位生成；未来可在此调用外部 API（如 MusicGen），并保存返回的音频。
    """

    out_dir = _safe_outputs_dir()
    out_path = out_dir / _derive_audio_name(midi_path.name)
    # 中文注释：根据强度调整频率，模拟不同渲染参数带来的变化。
    base_freq = 440.0
    freq = base_freq + max(0.0, min(intensity, 1.0)) * 100.0
    _sine_wav(out_path, seconds=6.0, freq=freq)
    return out_path


@router.post("/")
async def render_audio(
    midi_file: Optional[UploadFile] = File(default=None),
    midi_path: Optional[str] = Form(default=None),
    style: str = Form(default="cinematic"),
    intensity: float = Form(default=0.5),
):
    """
    中文说明：
    - 支持二选一输入：上传的 midi_file 或已有的 midi_path（outputs 内）
    - 使用占位合成生成 wav 音频，并返回可访问的 audio_url
    - 未来可将 render_via_provider 替换为真实 AI 渲染
    """

    try:
        out_dir = _safe_outputs_dir()
        chosen_midi_path: Optional[Path] = None

        if midi_file is not None:
            # 中文注释：将上传的 MIDI 存到 outputs，文件名加时间戳避免覆盖。
            original_name = midi_file.filename or "input.mid"
            suffix = Path(original_name).suffix or ".mid"
            temp_name = f"upload_{int(time.time())}{suffix}"
            tmp_midi = out_dir / temp_name
            content = await midi_file.read()
            if not content:
                raise ValidationError("uploaded midi file is empty", details={"reason": "midi_file is empty"})
            tmp_midi.write_bytes(content)
            chosen_midi_path = tmp_midi

        if midi_path and not chosen_midi_path:
            # 中文注释：校验传入的路径，确保位于 outputs/ 下方，避免目录穿越。
            base_dir = out_dir
            incoming = Path(midi_path)
            try:
                if incoming.is_absolute():
                    try:
                        relative = incoming.relative_to(base_dir)
                    except ValueError:
                        incoming_str = str(incoming)
                        if incoming_str.startswith("/outputs/"):
                            trimmed = Path(incoming_str.lstrip("/"))
                            if trimmed.parts and trimmed.parts[0] == base_dir.name:
                                relative = Path(*trimmed.parts[1:]) if len(trimmed.parts) > 1 else Path(trimmed.name)
                            else:
                                relative = Path(trimmed.name)
                        else:
                            raise ValidationError("midi_path must be inside outputs/", details={"path": midi_path})
                else:
                    parts = incoming.parts
                    if parts and parts[0] == base_dir.name:
                        relative = Path(*parts[1:]) if len(parts) > 1 else Path(incoming.name)
                    else:
                        relative = incoming
                resolved = (base_dir / relative).resolve()
            except ValueError as exc:  # noqa: PERF203
                raise ValidationError("midi_path must be inside outputs/", details={"path": midi_path}) from exc
            if base_dir not in resolved.parents and resolved != base_dir:
                raise ValidationError("midi_path must be inside outputs/", details={"path": midi_path})
            if not resolved.exists():
                raise ValidationError("midi_path not found", details={"path": midi_path})
            if not resolved.is_file():
                raise ValidationError("midi_path must be a file", details={"path": midi_path})
            chosen_midi_path = resolved

        if not chosen_midi_path:
            raise ValidationError("either midi_file or midi_path is required")

        # 中文注释：调用占位渲染函数，未来只需替换该调用即可接入真实服务。
        try:
            out_audio = render_via_provider(
                chosen_midi_path,
                style=style,
                intensity=float(intensity),
            )
        except Exception as exc:  # 中文注释：捕获底层异常并转换为业务错误，便于统一响应。
            logger.exception("render provider failure")
            raise RenderError("placeholder render failed") from exc

        audio_url = f"/outputs/{out_audio.name}"

        return JSONResponse(
            {
                "ok": True,
                "result": {
                    "audio_url": audio_url,
                    "duration_sec": 6.0,
                    "renderer": "placeholder-sine",
                    "style": style,
                    "intensity": float(intensity),
                },
            }
        )

    except MMError as err:
        # 中文注释：统一记录业务异常，方便观察错误码与上下文。
        logger.error("render error: %s", err)
        return JSONResponse(
            {"ok": False, "error": {"code": err.code, "message": err.message, "details": err.details}},
            status_code=err.http_status,
        )
    except Exception as exc:  # noqa: BLE001
        # 中文注释：兜底异常，防止堆栈泄露给客户端，同时记录日志排查。
        logger.exception("render internal error")
        return JSONResponse(
            {
                "ok": False,
                "error": {"code": "E_RENDER", "message": "internal rendering error"},
            },
            status_code=500,
        )

