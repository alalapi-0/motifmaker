"""针对专辑批量生成模块的基本单元测试，确保核心流程可用。"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import album


def _cleanup_plan_dir(plan: dict) -> None:
    """测试结束后删除 plan 默认创建的 outputs 目录，避免遗留文件。"""

    output_dir = plan.get("output_dir")
    if output_dir:
        candidate = Path(output_dir)
        if candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)


def test_plan_album_creates_tracks() -> None:
    """规划专辑时应该返回指定数量的曲目条目。"""

    plan = album.plan_album(title="Test Album", num_tracks=2, base_bpm=120, bars_per_track=8, base_seed=42)
    try:
        assert plan["num_tracks"] == 2
        assert len(plan["tracks"]) == 2
        assert plan["tracks"][0]["index"] == 1
    finally:
        _cleanup_plan_dir(plan)


def test_generate_track_creates_mp3(tmp_path, monkeypatch) -> None:
    """生成单曲时应写出 MP3 文件，测试中使用假转换器以避免真实编码。"""

    plan = album.plan_album(title="Single Track", num_tracks=1, base_bpm=100, bars_per_track=4, base_seed=77)
    original_dir = Path(plan["output_dir"])
    album_dir = tmp_path / "album"
    album_dir.mkdir()
    plan["output_dir"] = str(album_dir)

    def fake_wav_to_mp3(wav_path: Path, mp3_path: Path, keep_wav: bool = False) -> Path:
        """替代真实 mp3 转换，直接写入少量占位字节。"""

        mp3_path.write_bytes(b"FAKE")
        if not keep_wav and wav_path.exists():
            wav_path.unlink()
        return mp3_path

    monkeypatch.setattr(album.synth, "wav_to_mp3", fake_wav_to_mp3)

    track_spec = plan["tracks"][0]
    result = album.generate_track(track_spec, album_dir, apply_auto_mix=False)
    mp3_path = Path(result["mp3_path"])
    try:
        assert mp3_path.exists()
    finally:
        if mp3_path.exists():
            mp3_path.unlink()
        _cleanup_plan_dir({"output_dir": str(album_dir)})
        _cleanup_plan_dir({"output_dir": str(original_dir)})


def test_export_album_zip(tmp_path) -> None:
    """打包函数应包含 manifest 与 tracklist，并保持相对路径。"""

    plan = album.plan_album(title="Zip Test", num_tracks=1, base_bpm=90, bars_per_track=4, base_seed=15)
    original_dir = Path(plan["output_dir"])
    album_dir = tmp_path / "zip"
    album_dir.mkdir()
    plan["output_dir"] = str(album_dir)

    track_spec = plan["tracks"][0]
    mp3_path = album_dir / "track_01.mp3"
    mp3_path.write_bytes(b"FAKE")
    track_result = {
        "index": track_spec["index"],
        "title": track_spec["title"],
        "seed": track_spec["seed"],
        "bpm": track_spec["bpm"],
        "bars": track_spec["bars"],
        "scale": track_spec["scale"],
        "mp3_path": str(mp3_path),
        "duration_sec": 1.23,
        "created_at": plan["created_at"],
    }

    zip_path = album.export_album_zip(plan, [track_result], album_dir)
    try:
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = set(archive.namelist())
            assert "manifest.json" in names
            assert "TRACKLIST.txt" in names
            manifest_data = json.loads(archive.read("manifest.json"))
            assert manifest_data["tracks"][0]["mp3_path"] == "track_01.mp3"
    finally:
        if zip_path.exists():
            zip_path.unlink()
        if mp3_path.exists():
            mp3_path.unlink()
        _cleanup_plan_dir({"output_dir": str(album_dir)})
        _cleanup_plan_dir({"output_dir": str(original_dir)})
