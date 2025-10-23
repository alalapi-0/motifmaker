"""针对简化版 CLI 的基础功能测试。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cleanup import cleanup_outputs
from tools.generator import (
    arrange_to_tracks,
    check_environment,
    expand_motif_to_melody,
    generate_motif,
)
from tools.synth import synthesize_preview


def test_check_environment_keys():
    """验证环境检查至少返回关键字段。"""

    status = check_environment()
    assert "python" in status and status["python"] is True
    assert "numpy" in status
    assert "pydub" in status
    assert "ffmpeg" in status


def test_generate_motif_length(tmp_path):
    """动机长度应与默认节拍数一致。"""

    motif = generate_motif(seed=123)
    assert len(motif) == 4


def test_expand_motif_to_melody_not_empty():
    """旋律生成后应包含若干音符。"""

    motif = [60, 62, 64, 65]
    melody = expand_motif_to_melody(motif, repeats=2)
    assert melody
    assert all(len(item) == 2 for item in melody)


def test_arrangement_structure(tmp_path):
    """编曲应当包含主旋律、伴奏与噪音轨道。"""

    melody = [(60, 0.5), (62, 0.5)]
    arrangement = arrange_to_tracks(melody, bpm=100)
    assert "melody" in arrangement
    assert "accompaniment" in arrangement
    assert "noise" in arrangement


def test_synthesize_preview_creates_file(tmp_path):
    """预览合成应生成短时的 WAV 文件并便于清理。"""

    motif = [60, 62, 64, 67]
    preview_path = Path("outputs/test_preview.wav")
    synthesize_preview(motif, preview_path)
    assert preview_path.exists()
    preview_path.unlink()


def teardown_module(module):  # noqa: D401
    """在测试结束时清理 outputs 避免残留音频文件。"""

    # CI 环境通常无法播放音频，因此测试不调用播放逻辑，仅验证文件生成。
    # 这里强制清理 outputs，确保不会向仓库提交任何二进制音频文件。
    cleanup_outputs(auto_confirm=True)

