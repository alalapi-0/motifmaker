"""音频渲染 API 的占位实现测试用例。"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def render_client(tmp_path, monkeypatch) -> Tuple[TestClient, Path]:
    """构造使用临时输出目录的 FastAPI TestClient。"""

    outputs_dir = tmp_path / "outputs"
    monkeypatch.setenv("OUTPUT_DIR", str(outputs_dir))
    monkeypatch.setenv("USAGE_DB_PATH", str(tmp_path / "usage.db"))
    monkeypatch.setenv("ENV", "dev")

    # 中文注释：重新加载配置与路由模块，确保使用新的输出目录。
    config_module = importlib.import_module("motifmaker.config")
    importlib.reload(config_module)
    audio_render_module = importlib.import_module("motifmaker.audio_render")
    importlib.reload(audio_render_module)

    # 中文注释：重建任务管理器，避免与其它测试互相影响。
    from motifmaker.task_manager import TaskManager
    import motifmaker

    manager = TaskManager(max_concurrency=4)
    motifmaker.task_manager = manager
    audio_render_module.task_manager = manager

    from motifmaker.quota import init_usage_db

    init_usage_db(str(tmp_path / "usage.db"))

    app = FastAPI()
    app.include_router(audio_render_module.router)
    app.include_router(audio_render_module.tasks_router)

    return TestClient(app), Path(config_module.OUTPUT_DIR)


def test_render_with_existing_midi_path(render_client):
    """仅传递 midi_path 时应返回音频 URL 并生成占位 wav。"""

    client, output_dir = render_client
    output_dir.mkdir(parents=True, exist_ok=True)
    midi_path = output_dir / "demo.mid"
    midi_path.write_bytes(b"MThd")

    response = client.post(
        "/render/?sync=1",
        data={"midi_path": f"/outputs/{midi_path.name}", "sync": "1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    audio_url = payload["result"]["audio_url"]
    assert audio_url.endswith(".wav")
    audio_file = output_dir / Path(audio_url).name
    assert audio_file.exists()


def test_render_with_uploaded_file(render_client):
    """上传 midi_file 时同样应生成音频并返回 URL。"""

    client, output_dir = render_client
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {"midi_file": ("upload.mid", b"MThd", "audio/midi")}
    response = client.post(
        "/render/?sync=1",
        files=files,
        data={"style": "cinematic", "intensity": "0.7", "sync": "1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    audio_url = payload["result"]["audio_url"]
    audio_file = output_dir / Path(audio_url).name
    assert audio_file.exists()


def test_render_validation_failure(render_client):
    """若既未上传文件也未提供路径，则返回校验错误。"""

    client, _ = render_client
    response = client.post("/render/")
    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "E_VALIDATION"
