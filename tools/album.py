"""专辑批量生成功能，负责规划、生成与打包整个 8-bit 专辑。"""
from __future__ import annotations

import json
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4
import zipfile

from . import generator, mixer, synth

# 所有运行时产物统一放在 outputs 目录下，避免污染仓库
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "outputs"


def _ensure_root() -> None:
    """确保专辑输出的根目录存在。"""

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def _sanitize_title_for_filename(title: str) -> str:
    """将专辑标题转成安全的文件名，仅保留字母数字与常见符号。"""

    safe = [ch for ch in title if ch.isalnum() or ch in {"_", "-"}]
    sanitized = "".join(safe).strip("-_")
    return sanitized or "album"


def estimate_duration(bpm: int, bars: int, beats_per_bar: int = 4) -> float:
    """根据 BPM 与小节数估算秒级时长，用于前端预估。"""

    total_beats = max(bars, 1) * max(beats_per_bar, 1)
    if bpm <= 0:
        bpm = 120
    return float(total_beats) * 60.0 / float(bpm)


def plan_album(
    title: str,
    num_tracks: int,
    base_bpm: int,
    bars_per_track: int,
    base_seed: Optional[int] = None,
    scale: str = "C_major",
) -> Dict[str, object]:
    """按照用户输入规划整张专辑的元数据，不立即生成音频。"""

    if num_tracks <= 0:
        raise ValueError("Album must contain at least one track")

    # 若未指定随机种子则生成一个，保证整张专辑可复现
    if base_seed is None:
        base_seed = random.randint(0, 2**31 - 1)

    # 建立独立的随机数发生器，避免污染全局随机状态
    rng = random.Random(base_seed)

    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    _ensure_root()
    # 若目录已存在则追加短 UUID，确保不会冲突
    album_dir = OUTPUT_ROOT / f"album_{timestamp}"
    if album_dir.exists():
        album_dir = OUTPUT_ROOT / f"album_{timestamp}_{uuid4().hex[:6]}"
    album_dir.mkdir(parents=True, exist_ok=True)

    tracks: List[Dict[str, object]] = []
    for index in range(1, num_tracks + 1):
        # 使用派生随机数保证每首歌的种子稳定且略有差异
        seed = rng.randint(0, 2**31 - 1)
        bpm_variation = rng.choice([-3, 0, 3])
        bpm_value = max(60, min(200, base_bpm + bpm_variation))
        track_title = f"Track {index:02d}"
        tracks.append(
            {
                "index": index,
                "title": track_title,
                "seed": seed,
                "bpm": bpm_value,
                "bars": bars_per_track,
                "scale": scale,
                "estimated_duration": estimate_duration(bpm_value, bars_per_track),
            }
        )

    plan: Dict[str, object] = {
        "id": uuid4().hex,
        "title": title,
        "created_at": created_at,
        "num_tracks": num_tracks,
        "base_seed": base_seed,
        "base_bpm": base_bpm,
        "bars_per_track": bars_per_track,
        "scale": scale,
        "output_dir": str(album_dir),
        "tracks": tracks,
    }
    return plan


def _calc_duration_from_arrangement(arrangement: Dict[str, object], bpm: int) -> float:
    """根据编曲结构的旋律信息计算真实播放时长。"""

    melody = arrangement.get("melody") if isinstance(arrangement, dict) else None
    total_beats = 0.0
    if isinstance(melody, list):
        for note in melody:
            if isinstance(note, dict):
                duration = note.get("duration")
                if isinstance(duration, (int, float)):
                    total_beats += float(duration)
    if total_beats <= 0:
        return estimate_duration(bpm, int(arrangement.get("bars", 4)))
    return total_beats * 60.0 / float(max(bpm, 1))


def generate_track(track_spec: Dict[str, object], out_dir: Path, apply_auto_mix: bool = True) -> Dict[str, object]:
    """根据轨道配置生成单首曲目，完成 WAV→MP3 转换并返回元数据。"""

    out_dir.mkdir(parents=True, exist_ok=True)
    index = int(track_spec.get("index", 1))
    seed = int(track_spec.get("seed", 0))
    bpm = int(track_spec.get("bpm", 120))
    bars = int(track_spec.get("bars", 16))
    scale = str(track_spec.get("scale", "C_major"))
    title = str(track_spec.get("title", f"Track {index:02d}"))

    # 生成动机→旋律→编曲，全部使用派生随机种子确保可重现
    motif = generator.generate_motif(seed=seed, length_beats=4, scale=scale)
    repeats = max(bars, 1)
    melody = generator.expand_motif_to_melody(motif, repeats=repeats, variation=0.25)
    arrangement = generator.arrange_to_tracks(melody, bpm=bpm)
    arrangement["bars"] = bars

    wav_path = out_dir / f"track_{index:02d}.wav"
    mp3_path = out_dir / f"track_{index:02d}.mp3"

    mix_params: Optional[Dict[str, object]] = None
    if apply_auto_mix:
        # 自动混音可以提升聆听体验，同时返回参数供 manifest 记录
        mix_params = mixer.auto_mix(arrangement)
        mixer.apply_mixing(arrangement, mix_params, wav_path)
    else:
        synth.synthesize_8bit_wav(arrangement, wav_path)

    synth.wav_to_mp3(wav_path, mp3_path, keep_wav=False)

    duration_sec = _calc_duration_from_arrangement(arrangement, bpm)

    result = {
        "index": index,
        "title": title,
        "seed": seed,
        "bpm": bpm,
        "bars": bars,
        "scale": scale,
        "mp3_path": str(mp3_path),
        "duration_sec": duration_sec,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if mix_params is not None:
        result["mix_params"] = mix_params
    return result


def export_album_zip(
    album_plan: Dict[str, object],
    generated_tracks: List[Dict[str, object]],
    out_dir: Path,
) -> Path:
    """将专辑所有文件打包为 ZIP，并写出 manifest 与 tracklist。"""

    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "album": {
            "id": album_plan.get("id"),
            "title": album_plan.get("title"),
            "created_at": album_plan.get("created_at"),
            "num_tracks": album_plan.get("num_tracks"),
            "base_seed": album_plan.get("base_seed"),
            "base_bpm": album_plan.get("base_bpm"),
            "bars_per_track": album_plan.get("bars_per_track"),
            "scale": album_plan.get("scale"),
        },
        "tracks": [],
    }

    tracklist_lines: List[str] = []
    for track in generated_tracks:
        mp3_path = Path(track.get("mp3_path", ""))
        if mp3_path.exists():
            try:
                relative_mp3 = mp3_path.relative_to(out_dir)
            except ValueError:
                relative_mp3 = mp3_path.name
        else:
            relative_mp3 = mp3_path.name

        track_entry = dict(track)
        track_entry["mp3_path"] = str(relative_mp3)
        manifest["tracks"].append(track_entry)

        line = f"{track.get('index', 0):02d} - {track.get('title', 'Untitled')} ({track.get('bpm', 0)} BPM, {track.get('bars', 0)} bars)"
        tracklist_lines.append(line)

    manifest_path = out_dir / "manifest.json"
    tracklist_path = out_dir / "TRACKLIST.txt"

    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    with tracklist_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(tracklist_lines))

    zip_name = f"{_sanitize_title_for_filename(str(album_plan.get('title', 'album')))}.zip"
    zip_path = out_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in out_dir.iterdir():
            if file_path == zip_path:
                continue
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.name)

    return zip_path


@dataclass
class AlbumTask:
    """内存态专辑任务对象，用于 Web 与 CLI 统一管理进度。"""

    id: str
    plan: Dict[str, object]
    apply_auto_mix: bool
    status: str = "queued"
    progress: int = 0
    message: str = ""
    results: List[Dict[str, object]] = field(default_factory=list)
    zip_path: Optional[Path] = None
    current_track: Optional[Dict[str, object]] = None
    cancel_requested: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def _album_dir(self) -> Path:
        """从计划中解析当前专辑的输出目录。"""

        out_dir_value = self.plan.get("output_dir")
        if out_dir_value:
            return Path(out_dir_value)
        raise ValueError("Album plan missing output_dir")

    def run(self) -> None:
        """顺序执行批量生成逻辑，并实时更新状态。"""

        with self.lock:
            self.status = "running"
            self.progress = 5

        try:
            out_dir = self._album_dir()
            tracks = list(self.plan.get("tracks", []))
            total = max(len(tracks), 1)

            for idx, track_spec in enumerate(tracks, start=1):
                with self.lock:
                    if self.cancel_requested:
                        self.status = "cancelled"
                        self.message = "Task cancelled by user"
                        return
                    self.current_track = {
                        "index": track_spec.get("index"),
                        "title": track_spec.get("title"),
                    }

                result = generate_track(track_spec, out_dir, apply_auto_mix=self.apply_auto_mix)

                with self.lock:
                    self.results.append(result)
                    progress = 5 + int(90 * idx / total)
                    self.progress = min(progress, 95)

            zip_path = export_album_zip(self.plan, self.results, out_dir)
            with self.lock:
                self.zip_path = zip_path
                self.progress = 100
                self.status = "done"
                self.current_track = None
        except Exception as exc:  # noqa: BLE001
            with self.lock:
                self.status = "failed"
                self.message = str(exc)

    def request_cancel(self) -> None:
        """标记任务为取消状态，生成循环会在下一首开始前停止。"""

        with self.lock:
            self.cancel_requested = True

    def snapshot(self) -> Dict[str, object]:
        """生成线程安全的状态快照，供 API 返回。"""

        with self.lock:
            zip_url = None
            if self.zip_path and self.zip_path.exists():
                try:
                    relative = self.zip_path.relative_to(OUTPUT_ROOT)
                    zip_url = f"/outputs/{relative.as_posix()}"
                except ValueError:
                    zip_url = None

            results_payload = []
            for item in self.results:
                mp3_url = None
                mp3_path = Path(item.get("mp3_path", ""))
                if mp3_path.exists():
                    try:
                        relative = mp3_path.relative_to(OUTPUT_ROOT)
                        mp3_url = f"/outputs/{relative.as_posix()}"
                    except ValueError:
                        mp3_url = None
                payload = dict(item)
                payload["mp3_url"] = mp3_url
                results_payload.append(payload)

            return {
                "id": self.id,
                "status": self.status,
                "progress": self.progress,
                "message": self.message,
                "current": dict(self.current_track) if self.current_track else None,
                "results": results_payload,
                "zip_url": zip_url,
            }
