"""针对混音模块的基础单元测试，验证流程而非音色品质。"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import mixer


@pytest.fixture
def sample_arrangement() -> dict:
    """构造稳定的三轨编曲数据，避免依赖随机生成。"""

    return {
        "bpm": 120,
        "melody": [
            {"pitch": 64, "duration": 0.5, "wave": "square"},
            {"pitch": 67, "duration": 0.5, "wave": "square"},
        ],
        "accompaniment": [
            {"pitch": 52, "duration": 0.5, "wave": "square"},
            {"pitch": 55, "duration": 0.5, "wave": "square"},
        ],
        "noise": [
            {"type": "noise", "duration": 0.25, "intensity": 0.5},
            {"type": "noise", "duration": 0.25, "intensity": 0.5},
        ],
    }


def test_auto_mix_returns_parameters(sample_arrangement: dict) -> None:
    """自动混音应该返回包含主要字段的参数字典。"""

    params = mixer.auto_mix(sample_arrangement)
    assert isinstance(params, dict)
    assert "main_volume" in params
    assert "panning" in params


def test_apply_mixing_creates_wav(tmp_path: Path, sample_arrangement: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """应用混音后应生成非空的 WAV 文件与预览。"""

    monkeypatch.setattr(mixer, "OUTPUT_DIR", tmp_path)
    out_path = tmp_path / "mix.wav"
    params = {
        "main_volume": 0.8,
        "bg_volume": 0.5,
        "noise_volume": 0.3,
        "panning": {"main": 0.0, "bg": 0.2, "noise": -0.2},
        "reverb": 0.1,
        "eq_low": 1.0,
        "eq_high": 1.0,
    }

    result = mixer.apply_mixing(sample_arrangement, params, out_path)
    assert isinstance(result, dict)
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    preview_path = mixer.preview_mix(out_path)
    assert preview_path.exists()
    assert preview_path.stat().st_size > 0
    # 中文注释：测试仅确保文件生成成功，不对音频内容做主观评价。


def test_apply_mixing_clamps_parameters(tmp_path: Path, sample_arrangement: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """当传入越界参数时，混音结果应被限制在安全范围内。"""

    monkeypatch.setattr(mixer, "OUTPUT_DIR", tmp_path)
    out_path = tmp_path / "mix_extreme.wav"
    params = {
        "main_volume": -1.0,
        "bg_volume": 2.0,
        "noise_volume": 5.0,
        "panning": {"main": -2.0, "bg": 2.0, "noise": 0.0},
        "reverb": 1.5,
        "eq_low": -3.0,
        "eq_high": 3.0,
    }

    sanitized = mixer.apply_mixing(sample_arrangement, params, out_path)
    assert 0.0 <= sanitized["bg_volume"] <= 1.0
    assert sanitized["main_volume"] == 0.0
    assert -1.0 <= sanitized["panning"]["main"] <= 1.0
    assert sanitized["reverb"] <= 1.0
    assert 0.0 <= sanitized["eq_low"] <= 2.0
