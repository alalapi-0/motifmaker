"""合成模块，提供 8-bit 风格音频的渲染与播放功能。"""

from __future__ import annotations

import math
import wave
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

# 所有运行时生成的文件都放置在 outputs 目录中
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def _ensure_outputs_dir() -> None:
    """保证输出目录存在，避免写文件失败。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _note_to_frequency(midi_note: int) -> float:
    """将 MIDI 音高转换为频率。"""

    # 采用标准 A4=440Hz 的换算公式
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def _float_to_uint8(waveform: np.ndarray) -> np.ndarray:
    """把 -1~1 的浮点波形映射到 0~255 的无符号 8-bit 数据。"""

    # 先限制范围，再平移并缩放到 8bit，偏移 128 避免出现负值
    clipped = np.clip(waveform, -1.0, 1.0)
    return ((clipped + 1.0) * 127.5).astype(np.uint8)


def _render_square_sequence(notes: Iterable[Dict[str, float]], bpm: int, sample_rate: int, amplitude: float) -> np.ndarray:
    """根据音符序列渲染方波序列。"""

    seconds_per_beat = 60.0 / bpm
    segments: List[np.ndarray] = []
    for note in notes:
        duration_beats = float(note.get("duration", 0.5))
        duration_seconds = max(duration_beats * seconds_per_beat, 0.01)
        freq = _note_to_frequency(int(note.get("pitch", 60)))
        t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), False)
        wave_data = np.sign(np.sin(2 * math.pi * freq * t)) * amplitude
        segments.append(wave_data)
    if not segments:
        return np.zeros(0, dtype=float)
    return np.concatenate(segments)


def _render_noise_sequence(noise_events: Iterable[Dict[str, float]], bpm: int, sample_rate: int) -> np.ndarray:
    """根据噪音事件生成随机噪声轨道。"""

    seconds_per_beat = 60.0 / bpm
    rng = np.random.default_rng()
    segments: List[np.ndarray] = []
    for event in noise_events:
        duration_beats = float(event.get("duration", 0.25))
        duration_seconds = max(duration_beats * seconds_per_beat, 0.01)
        intensity = float(event.get("intensity", 0.5))
        samples = int(sample_rate * duration_seconds)
        wave_data = rng.uniform(-1.0, 1.0, samples) * intensity
        segments.append(wave_data)
    if not segments:
        return np.zeros(0, dtype=float)
    return np.concatenate(segments)


def _mix_tracks(tracks: Sequence[np.ndarray]) -> np.ndarray:
    """将多个轨道叠加成最终波形。"""

    if not tracks:
        return np.zeros(0, dtype=float)
    max_length = max(track.shape[0] for track in tracks)
    if max_length == 0:
        return np.zeros(0, dtype=float)

    mixed = np.zeros(max_length, dtype=float)
    for track in tracks:
        if track.shape[0] == max_length:
            mixed += track
        else:
            padded = np.zeros(max_length, dtype=float)
            padded[: track.shape[0]] = track
            mixed += padded
    # 限制叠加后幅度，避免削波
    mixed = np.clip(mixed, -1.0, 1.0)
    return mixed


def _write_uint8_wav(waveform: np.ndarray, out_wav: Path, sample_rate: int) -> None:
    """以 8-bit PCM 格式写入 WAV 文件。"""

    uint8_wave = _float_to_uint8(waveform)
    with wave.open(str(out_wav), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(1)  # 8-bit PCM 每个样本 1 字节
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(uint8_wave.tobytes())


def _build_arrangement_wave(arrangement: Dict[str, object], sample_rate: int, limit_seconds: float | None = None) -> np.ndarray:
    """根据编曲结构生成混合波形，可选限制长度用于预览。"""

    bpm = int(arrangement.get("bpm", 120))
    melody_wave = _render_square_sequence(arrangement.get("melody", []), bpm, sample_rate, amplitude=0.7)
    accompaniment_wave = _render_square_sequence(arrangement.get("accompaniment", []), bpm, sample_rate, amplitude=0.4)
    noise_wave = _render_noise_sequence(arrangement.get("noise", []), bpm, sample_rate)

    mixed = _mix_tracks([melody_wave, accompaniment_wave, noise_wave])
    if limit_seconds is not None and limit_seconds > 0:
        max_samples = int(sample_rate * limit_seconds)
        mixed = mixed[:max_samples]
    return mixed


def synthesize_preview(motif_or_melody, out_wav: Path, sample_rate: int = 22050, bpm: int = 120) -> Path:
    """渲染动机或旋律的短预览音频。"""

    _ensure_outputs_dir()
    # 根据输入类型准备统一的编曲结构
    if isinstance(motif_or_melody, dict):
        arrangement = dict(motif_or_melody)
    else:
        if isinstance(motif_or_melody, list) and motif_or_melody and isinstance(motif_or_melody[0], tuple):
            melody_pairs = [(int(pitch), float(duration)) for pitch, duration in motif_or_melody]
        else:
            melody_pairs = [(int(pitch), 0.5) for pitch in motif_or_melody]
        arrangement = {
            "bpm": bpm,
            "melody": [{"pitch": pitch, "duration": duration, "wave": "square"} for pitch, duration in melody_pairs],
            "accompaniment": [],
            "noise": [],
        }

    waveform = _build_arrangement_wave(arrangement, sample_rate, limit_seconds=5.0)
    if waveform.size == 0:
        waveform = np.zeros(int(sample_rate * 3), dtype=float)

    _write_uint8_wav(waveform, out_wav, sample_rate)
    print(f"Preview rendered to {out_wav}")
    return out_wav


def synthesize_8bit_wav(arrangement: Dict[str, object], out_wav_path: Path, sample_rate: int = 22050, bit_depth: int = 8) -> Path:
    """将完整编曲渲染为 8-bit WAV 文件。"""

    if bit_depth != 8:
        raise ValueError("Only 8-bit rendering is supported in this simplified synth")

    _ensure_outputs_dir()
    waveform = _build_arrangement_wave(arrangement, sample_rate)
    if waveform.size == 0:
        raise ValueError("Arrangement is empty; nothing to render")

    _write_uint8_wav(waveform, out_wav_path, sample_rate)
    print(f"Rendered arrangement to {out_wav_path}")
    return out_wav_path


def wav_to_mp3(wav_path: Path, mp3_path: Path, keep_wav: bool = False) -> Path:
    """使用 pydub 将 WAV 转换为 MP3，可选保留中间 WAV。"""

    from pydub import AudioSegment  # 延迟导入，避免不必要依赖

    audio = AudioSegment.from_wav(wav_path)
    audio.export(mp3_path, format="mp3")
    print(f"Exported MP3 to {mp3_path}")
    if not keep_wav and wav_path.exists():
        wav_path.unlink()
        print(f"Removed intermediate WAV {wav_path}")
    return mp3_path


def play_audio(file_path: Path) -> None:
    """使用 simpleaudio 播放 WAV 预览音频。"""

    try:
        import simpleaudio as sa
    except ImportError:
        print("Audio playback unavailable: simpleaudio missing.")
        return

    try:
        wave_obj = sa.WaveObject.from_wave_file(str(file_path))
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to play audio: {exc}")

