"""生成模块，负责动机、旋律与编曲的核心逻辑。"""

from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 输出目录位置，所有运行时文件都放在这里，避免污染仓库
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def _ensure_outputs_dir() -> None:
    """确保输出目录存在。"""

    # 使用 exist_ok=True 避免重复创建时报错
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_environment() -> Dict[str, bool]:
    """检查 Python 版本、关键依赖与 ffmpeg 状态。"""

    # 准备环境状态字典，默认标记为 False
    status = {
        "python": False,
        "numpy": False,
        "pydub": False,
        "ffmpeg": False,
    }

    # 检查 Python 主版本是否满足 3.8 以上
    status["python"] = sys.version_info >= (3, 8)
    print(f"Python version ok: {status['python']}")

    # 动态导入依赖，捕捉 ImportError 显示缺失信息
    try:
        import numpy  # noqa: F401  # pylint: disable=unused-import

        status["numpy"] = True
    except ImportError:
        print("Missing dependency: numpy")

    try:
        import pydub  # noqa: F401  # pylint: disable=unused-import

        status["pydub"] = True
    except ImportError:
        print("Missing dependency: pydub")

    # 检查 ffmpeg 是否可用，提示用户安装位置
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        status["ffmpeg"] = True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("ffmpeg not found. Please install ffmpeg for MP3 export support.")

    return status


def generate_motif(seed: int | None = None, length_beats: int = 4, scale: str = "C_major") -> List[int]:
    """基于简单规则生成短动机并写入 JSON。"""

    # 如果传入随机种子则固定随机结果，方便复现
    if seed is not None:
        random.seed(seed)

    # 定义基础音阶，这里使用 MIDI 音高数字表示
    scales = {
        "C_major": [60, 62, 64, 65, 67, 69, 71, 72],
        "A_minor": [57, 59, 60, 62, 64, 65, 67, 69],
    }
    pool = scales.get(scale, scales["C_major"])

    # 生成长度等于节拍数的音高序列
    motif = [random.choice(pool) for _ in range(length_beats)]

    _ensure_outputs_dir()
    motif_path = OUTPUT_DIR / "motif.json"
    with motif_path.open("w", encoding="utf-8") as fh:
        json.dump({"scale": scale, "motif": motif}, fh, indent=2, ensure_ascii=False)

    print(f"Motif saved to {motif_path}")
    return motif


def expand_motif_to_melody(motif: List[int], repeats: int = 4, variation: float = 0.2) -> List[Tuple[int, float]]:
    """将动机扩展为旋律并引入少量变奏。"""

    # 旋律列表包含 (音高, 时值) 元组，时值以拍为单位
    melody: List[Tuple[int, float]] = []
    for _ in range(repeats):
        for note in motif:
            # 根据 variation 参数决定是否微调音高
            offset_choices = [-2, -1, 0, 1, 2]
            if random.random() < variation:
                note += random.choice(offset_choices)
            # 时值在 0.5 到 1 拍之间浮动
            duration = random.choice([0.5, 0.75, 1.0])
            melody.append((note, duration))

    print(f"Generated melody with {len(melody)} notes")
    return melody


def arrange_to_tracks(melody: List[Tuple[int, float]], bpm: int = 120) -> Dict[str, object]:
    """根据旋律生成简单的 8-bit 编曲结构并写入 JSON。"""

    # 主旋律轨道直接来自 melody，伴奏与鼓点通过规则生成
    accompaniment = []
    noise_track = []
    bass_interval = -12

    for idx, (pitch, duration) in enumerate(melody):
        # 伴奏音选择低八度并加入交替三度
        if idx % 2 == 0:
            accompaniment_pitch = pitch + bass_interval
        else:
            accompaniment_pitch = pitch + bass_interval - 5
        accompaniment.append({"pitch": accompaniment_pitch, "duration": duration, "wave": "square"})

        # 噪音鼓点按节拍填充
        noise_track.append({"type": "noise", "duration": max(0.25, duration / 2), "intensity": 0.6})

    arrangement = {
        "bpm": bpm,
        "melody": [{"pitch": p, "duration": d, "wave": "square"} for p, d in melody],
        "accompaniment": accompaniment,
        "noise": noise_track,
    }

    _ensure_outputs_dir()
    arrangement_path = OUTPUT_DIR / "arrangement.json"
    with arrangement_path.open("w", encoding="utf-8") as fh:
        json.dump(arrangement, fh, indent=2, ensure_ascii=False)

    print(f"Arrangement saved to {arrangement_path}")
    return arrangement

