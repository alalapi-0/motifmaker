"""/render/ 提供商切换与配额逻辑测试集。"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict, Tuple

import pytest
from fastapi.testclient import TestClient

# 中文注释：需要清理的模块列表，确保环境变量生效后重新加载配置。
_MODULES_TO_CLEAR = [
    "motifmaker.api",
    "motifmaker.audio_render",
    "motifmaker.config",
    "motifmaker.quota",
]


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    extra_env: Dict[str, str],
) -> Tuple[TestClient, Path]:
    """构造带定制环境变量的 TestClient，返回客户端与输出目录。"""

    output_dir = tmp_path / "outputs"
    projects_dir = tmp_path / "projects"
    output_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)

    base_env = {
        "OUTPUT_DIR": str(output_dir),
        "PROJECTS_DIR": str(projects_dir),
        "USAGE_DB_PATH": str(tmp_path / "usage.db"),
        "RATE_LIMIT_RPS": "100",
    }
    for key, value in {**base_env, **extra_env}.items():
        monkeypatch.setenv(key, str(value))

    for module in _MODULES_TO_CLEAR:
        sys.modules.pop(module, None)

    api = importlib.import_module("motifmaker.api")
    importlib.reload(api)
    return TestClient(api.app), output_dir


def _write_dummy_midi(path: Path) -> None:
    """生成一个最小的 MIDI 占位文件，满足路由存在性检查。"""

    path.write_bytes(b"MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xe0MTrk\x00\x00\x00\x00")


def test_placeholder_provider_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """场景 A：占位 Provider 可成功返回音频 URL。"""

    client, output_dir = _build_client(monkeypatch, tmp_path, {"AUDIO_PROVIDER": "placeholder"})
    midi_path = output_dir / "demo.mid"
    _write_dummy_midi(midi_path)

    response = client.post(
        "/render/",
        data={"midi_path": str(midi_path), "style": "cinematic", "intensity": "0.6"},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload.get("ok") is True
    assert payload["result"]["audio_url"].startswith("/outputs/")


def test_hf_provider_requires_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """场景 B：缺失 HF Token 时返回 E_CONFIG，不会触发外部请求。"""

    client, output_dir = _build_client(
        monkeypatch,
        tmp_path,
        {
            "AUDIO_PROVIDER": "hf",
            "HF_API_TOKEN": "",
        },
    )
    midi_path = output_dir / "hf.mid"
    _write_dummy_midi(midi_path)

    response = client.post(
        "/render/",
        data={"midi_path": str(midi_path), "style": "ambient", "intensity": "0.4"},
    )
    payload = response.json()
    assert response.status_code == 400
    assert payload.get("ok") is False
    assert payload["error"]["code"] == "E_CONFIG"


def test_replicate_provider_requires_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """场景 C：缺失 Replicate Token 时返回 E_CONFIG。"""

    client, output_dir = _build_client(
        monkeypatch,
        tmp_path,
        {
            "AUDIO_PROVIDER": "replicate",
            "REPLICATE_API_TOKEN": "",
        },
    )
    midi_path = output_dir / "rep.mid"
    _write_dummy_midi(midi_path)

    response = client.post(
        "/render/",
        data={"midi_path": str(midi_path), "style": "ambient", "intensity": "0.7"},
    )
    payload = response.json()
    assert response.status_code == 400
    assert payload.get("ok") is False
    assert payload["error"]["code"] == "E_CONFIG"


def test_daily_quota_limit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """场景 D：每日免费额度为 1，第二次调用应触发 429。"""

    client, output_dir = _build_client(
        monkeypatch,
        tmp_path,
        {
            "AUDIO_PROVIDER": "placeholder",
            "DAILY_FREE_QUOTA": "1",
        },
    )
    midi_path = output_dir / "quota.mid"
    _write_dummy_midi(midi_path)

    first = client.post(
        "/render/",
        data={"midi_path": str(midi_path), "style": "cinematic", "intensity": "0.5"},
    )
    assert first.status_code == 200

    second = client.post(
        "/render/",
        data={"midi_path": str(midi_path), "style": "cinematic", "intensity": "0.5"},
    )
    payload = second.json()
    assert second.status_code == 429
    assert payload.get("ok") is False
    assert payload["error"]["code"] == "E_RATE_LIMIT"
