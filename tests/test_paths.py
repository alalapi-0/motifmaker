"""路径安全相关的端到端测试，确保 /render 与 /download 均能正确防御目录穿越。"""

from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

import motifmaker.api as api
import motifmaker.audio_render as audio_render
import motifmaker.config as config


def _reload_app() -> TestClient:
    """中文注释：根据最新环境变量重新加载配置与应用，返回新的 TestClient。

    - ``importlib.reload`` 会强制模块重新执行，确保读取到 monkeypatch 注入的
      ``OUTPUT_DIR`` 等环境变量；
    - 同时重载 ``audio_render`` 和 ``api`` 模块，保证内部缓存的常量（如输出目录）
      与配置保持一致，避免测试之间互相污染。
    """

    global config, audio_render, api
    config = importlib.reload(config)
    audio_render = importlib.reload(audio_render)
    api = importlib.reload(api)
    return TestClient(api.app)


def _touch_in(dirpath: str | Path, name: str) -> Path:
    """中文注释：在指定目录下创建空文件并返回解析后的绝对路径。"""

    directory = Path(dirpath)
    target = directory / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"")
    return target.resolve()


def test_download_allows_only_outputs_and_projects(tmp_path, monkeypatch):
    """场景：合法的 outputs 与 projects 内文件可以下载；其他目录应被拒绝。"""

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("PROJECTS_DIR", str(tmp_path / "projects"))
    with _reload_app() as client:
        good_out = _touch_in(config.OUTPUT_DIR, "a.mid")
        good_proj = _touch_in(config.PROJECTS_DIR, "b.json")
        bad_like = _touch_in(tmp_path / "outputs_backup", "oops.mid")

        resp_out = client.get(f"/download?path={good_out}")
        assert resp_out.status_code == 200

        resp_proj = client.get(f"/download?path={good_proj}")
        assert resp_proj.status_code == 200

        resp_bad = client.get(f"/download?path={bad_like}")
        assert resp_bad.status_code in (400, 403)
        body = resp_bad.json()
        assert body.get("ok") is False
        assert body["error"]["code"] in ("E_VALIDATION", "E_FORBIDDEN")


def test_render_accepts_relative_and_absolute_paths(tmp_path, monkeypatch):
    """场景：输出目录为相对路径时，/render 应接受相对与绝对 midi_path。"""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OUTPUT_DIR", "outputs")
    monkeypatch.setenv("PROJECTS_DIR", "projects")
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    midi_file = outputs_dir / "rel.mid"
    midi_file.write_bytes(b"dummy")

    with _reload_app() as client:
        resp_rel = client.post(
            "/render/",
            data={
                "midi_path": "outputs/rel.mid",
                "style": "cinematic",
                "intensity": "0.5",
            },
        )
        assert resp_rel.status_code == 200
        assert resp_rel.json().get("ok") is True

        resp_abs = client.post(
            "/render/",
            data={
                "midi_path": str(midi_file.resolve()),
                "style": "cinematic",
                "intensity": "0.5",
            },
        )
        assert resp_abs.status_code == 200
        assert resp_abs.json().get("ok") is True


def test_render_rejects_path_traversal(tmp_path, monkeypatch):
    """场景：/render 必须拒绝 outputs 目录外的路径。"""

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("PROJECTS_DIR", str(tmp_path / "projects"))
    outside = tmp_path / "evil.mid"
    outside.write_bytes(b"dummy")

    with _reload_app() as client:
        resp = client.post(
            "/render/",
            data={
                "midi_path": str(outside.resolve()),
                "style": "cinematic",
                "intensity": "0.5",
            },
        )
        assert resp.status_code in (400, 403, 422)
        body = resp.json()
        assert body.get("ok") is False
        assert body["error"]["code"] in ("E_VALIDATION", "E_FORBIDDEN")
