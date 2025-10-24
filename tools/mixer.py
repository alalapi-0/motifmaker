"""混音与效果控制模块，提供自动与手动混音的基础操作。"""

from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

from . import synth

# 输出目录与默认采样率设置，确保与合成模块保持一致
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
DEFAULT_SAMPLE_RATE = 22050


def _ensure_outputs_dir() -> None:
    """保证 outputs 目录存在，避免后续写文件失败。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """对参数进行范围限制，防止异常输入破坏混音稳定性。"""

    return max(minimum, min(maximum, float(value)))


def _pan_gains(pan: float) -> Tuple[float, float]:
    """根据 -1~1 的声像值计算左右声道增益（使用等功率曲线）。"""

    angle = (pan + 1.0) * (math.pi / 4.0)
    return math.cos(angle), math.sin(angle)


def _simple_lowpass(signal: np.ndarray, kernel_size: int = 9) -> np.ndarray:
    """使用均值卷积模拟低通滤波，保留整体 8-bit 颗粒感。"""

    if signal.size == 0:
        return signal
    kernel = np.ones(kernel_size, dtype=float) / float(kernel_size)
    return np.convolve(signal, kernel, mode="same")


def _apply_delay(signal: np.ndarray, delay_samples: int, decay: float) -> np.ndarray:
    """用简单的延迟叠加模拟混响尾音。"""

    if signal.size == 0 or delay_samples <= 0 or decay <= 0:
        return signal
    output = np.zeros(signal.size + delay_samples, dtype=float)
    output[: signal.size] += signal
    output[delay_samples:] += signal * decay
    return output


def apply_mixing(arrangement_dict: Dict[str, object], params: Dict[str, object], out_wav_path: Path) -> Dict[str, object]:
    """依据用户参数混合三轨音频并写出新的 8-bit 立体声 WAV。"""

    _ensure_outputs_dir()
    sanitized: Dict[str, object] = {}

    # 渲染原始轨道，得到主旋律(main)、伴奏(bg)、噪音(noise)
    tracks = synth.render_tracks(arrangement_dict, DEFAULT_SAMPLE_RATE)

    # 准备体积与声像设置，并确保落在规范范围内
    volumes = {
        "main": _clamp(params.get("main_volume", 0.85), 0.0, 1.0),
        "bg": _clamp(params.get("bg_volume", 0.6), 0.0, 1.0),
        "noise": _clamp(params.get("noise_volume", 0.4), 0.0, 1.0),
    }
    sanitized.update({
        "main_volume": volumes["main"],
        "bg_volume": volumes["bg"],
        "noise_volume": volumes["noise"],
    })

    # 声像参数采用字典形式，默认保持中间位置
    raw_panning = params.get("panning", {}) if isinstance(params.get("panning"), dict) else {}
    panning = {
        "main": _clamp(raw_panning.get("main", 0.0), -1.0, 1.0),
        "bg": _clamp(raw_panning.get("bg", 0.25), -1.0, 1.0),
        "noise": _clamp(raw_panning.get("noise", -0.25), -1.0, 1.0),
    }
    sanitized["panning"] = panning

    # 准备效果器参数：混响与简易 EQ
    reverb_amount = _clamp(params.get("reverb", 0.15), 0.0, 1.0)
    eq_low = _clamp(params.get("eq_low", 1.0), 0.0, 2.0)
    eq_high = _clamp(params.get("eq_high", 1.0), 0.0, 2.0)
    sanitized.update({"reverb": reverb_amount, "eq_low": eq_low, "eq_high": eq_high})

    # 确保所有轨道对齐长度后叠加，生成左右声道波形
    max_length = max((track.size for track in tracks.values()), default=0)
    left = np.zeros(max_length, dtype=float)
    right = np.zeros(max_length, dtype=float)

    for name, track in tracks.items():
        if track.size == 0:
            continue
        padded = np.zeros(max_length, dtype=float)
        padded[: track.size] = track
        gain_l, gain_r = _pan_gains(panning.get(name, 0.0))
        left += padded * volumes.get(name, 0.0) * gain_l
        right += padded * volumes.get(name, 0.0) * gain_r

    # 简单 EQ：低频使用均值滤波，高频为原信号减去低频部分
    left_low = _simple_lowpass(left)
    right_low = _simple_lowpass(right)
    left_high = left - left_low
    right_high = right - right_low
    left = left_low * eq_low + left_high * eq_high
    right = right_low * eq_low + right_high * eq_high

    # 应用简易混响，延迟约 150ms
    delay_samples = int(DEFAULT_SAMPLE_RATE * 0.15)
    if reverb_amount > 0:
        left = _apply_delay(left, delay_samples, reverb_amount)
        right = _apply_delay(right, delay_samples, reverb_amount)

    # 对齐立体声长度并裁剪到 -1~1，保持 8-bit 风格的动态范围
    final_length = max(left.size, right.size)
    left = np.pad(left, (0, final_length - left.size))
    right = np.pad(right, (0, final_length - right.size))
    stereo = np.vstack([left, right])
    stereo = np.clip(stereo, -1.0, 1.0)

    synth.save_uint8_wav(stereo, out_wav_path, DEFAULT_SAMPLE_RATE)
    return sanitized


def auto_mix(arrangement_dict: Dict[str, object]) -> Dict[str, object]:
    """分析轨道峰值并给出推荐的混音参数。"""

    tracks = synth.render_tracks(arrangement_dict, DEFAULT_SAMPLE_RATE)
    peaks = {name: float(np.max(np.abs(track))) if track.size else 0.0 for name, track in tracks.items()}
    reference = max(peaks.values(), default=1.0) or 1.0

    def _volume_for(name: str, base: float) -> float:
        peak = peaks.get(name, 0.0)
        if peak <= 1e-6:
            return 0.0
        return _clamp(base * (reference / peak), 0.0, 1.0)

    suggested = {
        "main_volume": _volume_for("main", 0.9),
        "bg_volume": _volume_for("bg", 0.6),
        "noise_volume": _volume_for("noise", 0.35),
        "panning": {"main": 0.0, "bg": 0.3, "noise": -0.25},
        "reverb": 0.18,
        "eq_low": 1.0,
        "eq_high": 1.05,
    }
    return suggested


def preview_mix(out_wav_path: Path, seconds: float = 5.0) -> Path:
    """根据最终混音生成短预览文件，便于 CLI 与 Web 快速试听。"""

    _ensure_outputs_dir()
    source = Path(out_wav_path)
    if not source.exists():
        raise FileNotFoundError(str(source))

    preview_path = OUTPUT_DIR / "preview_mix.wav"
    with wave.open(str(source), "rb") as reader:
        sample_rate = reader.getframerate()
        frames_needed = int(sample_rate * max(seconds, 0.5))
        frames = reader.readframes(frames_needed)
        nchannels = reader.getnchannels()
        sampwidth = reader.getsampwidth()

    with wave.open(str(preview_path), "wb") as writer:
        writer.setnchannels(nchannels)
        writer.setsampwidth(sampwidth)
        writer.setframerate(sample_rate)
        writer.writeframes(frames)

    return preview_path
