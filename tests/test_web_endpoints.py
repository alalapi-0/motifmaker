"""使用 FastAPI TestClient 验证 Web 端关键接口。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tools import cleanup, generator, synth
from webapp import main as web_main


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    """为每个测试创建独立的 outputs 目录并注入模拟渲染函数。"""

    out_dir = tmp_path / "outputs"
    out_dir.mkdir()

    # 将 CLI 与 Web 模块中的输出目录都指向临时位置，防止污染仓库
    for module in (generator, synth, cleanup, web_main):
        monkeypatch.setattr(module, "OUTPUT_DIR", out_dir)

    # 替换环境检查，避免依赖真实的 ffmpeg 或第三方包
    monkeypatch.setattr(
        generator,
        "check_environment",
        lambda: {"python": True, "numpy": True, "pydub": True, "ffmpeg": True},
    )

    # 替换音频渲染函数，仅写入占位文件即可
    def fake_preview(data, out_path: Path, sample_rate: int = 22050, bpm: int = 120) -> Path:
        out_path.write_bytes(b"preview")
        return out_path

    def fake_render(arrangement, out_path: Path, sample_rate: int = 22050, bit_depth: int = 8) -> Path:
        out_path.write_bytes(b"wav")
        return out_path

    def fake_mp3(wav_path: Path, mp3_path: Path, keep_wav: bool = False) -> Path:
        mp3_path.write_bytes(b"mp3")
        if not keep_wav and wav_path.exists():
            wav_path.unlink()
        return mp3_path

    monkeypatch.setattr(synth, "synthesize_preview", fake_preview)
    monkeypatch.setattr(synth, "synthesize_8bit_wav", fake_render)
    monkeypatch.setattr(synth, "wav_to_mp3", fake_mp3)

    # FastAPI 应用内部使用的模块同样引用到相同的 synth 实例
    monkeypatch.setattr(web_main, "OUTPUT_DIR", out_dir)

    client = TestClient(web_main.app)
    web_main.app.state.test_output_dir = out_dir
    return client


def test_check_env_ok(client: TestClient) -> None:
    """验证环境检查接口返回 200 且包含 python 字段。"""

    response = client.get("/check_env")
    assert response.status_code == 200
    payload = response.json()
    assert payload["python"] is True


def test_generate_motif_returns_preview(client: TestClient) -> None:
    """验证动机生成接口返回 motif 列表与预览链接。"""

    response = client.post("/generate_motif")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("motif"), list)
    assert payload.get("preview_url", "").startswith("/preview?file=")


def test_generate_melody_returns_arrangement(client: TestClient) -> None:
    """先生成动机，再调用旋律接口，并检查编曲字段。"""

    client.post("/generate_motif")
    response = client.post("/generate_melody")
    assert response.status_code == 200
    payload = response.json()
    arrangement = payload.get("arrangement", {})
    assert "melody" in arrangement
    assert "accompaniment" in arrangement


def test_cleanup_returns_deleted_files(client: TestClient) -> None:
    """提前写入文件并调用清理接口，确认删除列表正确。"""

    out_dir: Path = web_main.app.state.test_output_dir
    dummy = out_dir / "temp.txt"
    dummy.write_text("demo")

    response = client.delete("/cleanup")
    assert response.status_code == 200
    payload = response.json()
    assert "temp.txt" in payload.get("deleted_files", [])
    assert payload.get("status") == "ok"
    assert list(out_dir.iterdir()) == []
