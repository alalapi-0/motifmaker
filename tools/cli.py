"""MotifMaker 简化版 8-bit CLI 入口。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import album as album_tools
from . import generator
from . import db as project_db
from . import mixer
from .cleanup import cleanup_outputs
from .synth import play_audio, synthesize_8bit_wav, synthesize_preview, wav_to_mp3

# 统一输出目录，所有临时文件都放在这里
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
MIX_OUTPUT_PATH = OUTPUT_DIR / "mixed_latest.wav"


class SessionState(dict):
    """用于跟踪当前会话状态的简单字典子类。"""

    motif: Optional[list]
    melody: Optional[list]
    arrangement: Optional[dict]
    final_mp3: Optional[Path]
    mix_params: Optional[dict]
    mix_output: Optional[Path]
    mix_preview: Optional[Path]


class AlbumSession(dict):
    """专辑批量生成菜单的会话状态。"""

    plan: Optional[dict]
    results: Optional[list]
    zip_path: Optional[Path]
    auto_mix: bool


def _compute_length_beats(arrangement: Optional[dict]) -> Optional[int]:
    """根据编曲数据估算总时长（以拍为单位）。"""

    if not arrangement:
        return None
    melody = arrangement.get("melody")
    if not isinstance(melody, list):
        return None
    total = 0.0
    for note in melody:
        duration = note.get("duration") if isinstance(note, dict) else None
        if isinstance(duration, (int, float)):
            total += float(duration)
    if total <= 0:
        return None
    return int(round(total))


def _safe_int(value: object) -> Optional[int]:
    """安全地尝试将值转换为整数。"""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _prompt_int(prompt: str, default: int, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    """交互式询问整数输入，自动套用默认值与范围限制。"""

    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            value = default
        else:
            try:
                value = int(raw)
            except ValueError:
                print("Please enter a valid integer.")
                continue
        if minimum is not None and value < minimum:
            print(f"Value must be >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Value must be <= {maximum}.")
            continue
        return value


def _prompt_optional_int(prompt: str) -> Optional[int]:
    """读取可选的整数输入，留空则返回 None。"""

    raw = input(f"{prompt} (leave blank for none): ").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print("Invalid integer, ignoring input.")
        return None


def _ensure_outputs_dir() -> None:
    """确保输出目录存在。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_arrangement(state: SessionState) -> Optional[dict]:
    """必要时从磁盘加载编曲数据，供混音与渲染使用。"""

    arrangement = state.get("arrangement")
    if isinstance(arrangement, dict):
        return arrangement
    arrangement_path = state.get("arrangement_path")
    if arrangement_path and Path(arrangement_path).exists():
        try:
            with Path(arrangement_path).open("r", encoding="utf-8") as fh:
                arrangement = json.load(fh)
            state["arrangement"] = arrangement
            return arrangement
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _perform_mix(state: SessionState, params: dict) -> bool:
    """根据传入参数执行混音并自动生成预览。"""

    arrangement = _load_arrangement(state)
    if not arrangement:
        print("Arrangement missing. Please generate melody first.")
        return False

    _ensure_outputs_dir()
    try:
        result = mixer.apply_mixing(arrangement, params, MIX_OUTPUT_PATH)
    except Exception as exc:  # noqa: BLE001
        print(f"Mixing failed: {exc}")
        return False

    preview_path = None
    try:
        preview_path = mixer.preview_mix(MIX_OUTPUT_PATH)
    except Exception as exc:  # noqa: BLE001
        print(f"Unable to create preview: {exc}")
    else:
        try:
            play_audio(preview_path)
        except Exception as exc:  # noqa: BLE001
            print(f"Unable to play preview: {exc}")

    state["mix_params"] = result
    state["mix_output"] = MIX_OUTPUT_PATH
    if preview_path:
        state["mix_preview"] = preview_path
    print(f"Mix rendered to {MIX_OUTPUT_PATH}")
    return True


def handle_album_plan(album_state: AlbumSession) -> None:
    """专辑菜单第一步：规划批量生成任务。"""

    title = input("Album title (leave blank for timestamp): ").strip()
    if not title:
        title = datetime.now().strftime("Album %Y-%m-%d %H:%M:%S")

    num_tracks = _prompt_int("Number of tracks", default=4, minimum=1, maximum=20)
    base_bpm = _prompt_int("Base BPM", default=120, minimum=60, maximum=200)
    bars = _prompt_int("Bars per track", default=16, minimum=4, maximum=64)
    base_seed = _prompt_optional_int("Base seed")
    scale = input("Scale (e.g. C_major / A_minor) [C_major]: ").strip() or "C_major"
    auto_mix_answer = input("Apply auto mix per track? (y/n) [y]: ").strip().lower() or "y"
    auto_mix = auto_mix_answer.startswith("y")

    try:
        plan = album_tools.plan_album(
            title=title,
            num_tracks=num_tracks,
            base_bpm=base_bpm,
            bars_per_track=bars,
            base_seed=base_seed,
            scale=scale,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to plan album: {exc}")
        return

    album_state.clear()
    album_state["plan"] = plan
    album_state["results"] = []
    album_state["zip_path"] = None
    album_state["auto_mix"] = auto_mix

    output_dir = plan.get("output_dir")
    print("Album planned successfully!")
    print(f"Title       : {plan.get('title')}")
    print(f"Tracks      : {plan.get('num_tracks')}")
    print(f"Base BPM    : {plan.get('base_bpm')}")
    print(f"Bars / track: {plan.get('bars_per_track')}")
    if output_dir:
        print(f"Output dir  : {output_dir}")
    print("Track previews:")
    for track in plan.get("tracks", []):
        estimate = track.get("estimated_duration")
        if isinstance(estimate, (int, float)):
            duration_hint = f"~{estimate:.1f}s"
        else:
            duration_hint = "duration unknown"
        print(
            f"  #{track.get('index'):02d} {track.get('title')} - Seed {track.get('seed')} - "
            f"{track.get('bpm')} BPM - {duration_hint}"
        )
    print("Use 'Start generation' after confirming the plan.")


def handle_album_generation(album_state: AlbumSession) -> None:
    """执行批量曲目生成，并在控制台打印进度条。"""

    plan = album_state.get("plan")
    if not plan:
        print("Please plan an album first.")
        return

    tracks = plan.get("tracks", [])
    if not tracks:
        print("Album plan contains no tracks.")
        return

    out_dir = Path(plan.get("output_dir", OUTPUT_DIR))
    auto_mix = bool(album_state.get("auto_mix", True))
    total = len(tracks)
    results = []

    print(f"Generating album '{plan.get('title')}' with {total} tracks...")
    for idx, track_spec in enumerate(tracks, start=1):
        title = track_spec.get("title", f"Track {idx:02d}")
        print(f"[{idx}/{total}] Rendering {title}...")
        try:
            result = album_tools.generate_track(track_spec, out_dir, apply_auto_mix=auto_mix)
        except Exception as exc:  # noqa: BLE001
            print(f"Generation failed on track {idx}: {exc}")
            break
        results.append(result)
        progress = int(idx / total * 100)
        bar = "#" * (progress // 5)
        print(f"  Progress: [{bar:<20}] {progress:3d}%")
    else:
        try:
            zip_path = album_tools.export_album_zip(plan, results, out_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to export ZIP: {exc}")
            return

        album_state["results"] = results
        album_state["zip_path"] = zip_path
        print(f"Album export complete! ZIP located at: {zip_path}")
        print("You can review the manifest.json and TRACKLIST.txt inside the folder.")
        print("Remember: binary outputs stay in outputs/ and are not committed to Git.")
        return

    print("Album generation aborted due to errors. Partial files may exist under outputs/.")


def handle_album_status(album_state: AlbumSession) -> None:
    """打印当前规划、生成与打包状态摘要。"""

    plan = album_state.get("plan")
    if not plan:
        print("No album plan available yet.")
        return

    print(f"Album title : {plan.get('title')}")
    print(f"Output dir  : {plan.get('output_dir')}")
    results = album_state.get("results") or []
    if not results:
        print("Tracks generated: 0")
    else:
        print(f"Tracks generated: {len(results)}/{plan.get('num_tracks')}")
        for track in results:
            print(
                f"  #{track.get('index'):02d} {track.get('title')} - "
                f"{track.get('duration_sec', 0):.1f}s - {track.get('bpm')} BPM"
            )
    zip_path = album_state.get("zip_path")
    if zip_path:
        print(f"ZIP ready at: {zip_path}")
    else:
        print("ZIP not exported yet. Run generation first.")


def handle_album_download(album_state: AlbumSession) -> None:
    """展示 ZIP 文件路径，方便用户复制下载。"""

    zip_path = album_state.get("zip_path")
    if not zip_path:
        print("Album ZIP not available yet.")
        return
    print(f"Album archive stored at: {zip_path}")
    print("Open the path manually or share the ZIP as needed.")


def handle_album_menu(album_state: AlbumSession) -> None:
    """专辑批量生成子菜单循环。"""

    while True:
        print(
            """
Album / Batch Export
1) Plan album
2) Start generation
3) Show status
4) Show ZIP path
5) Back to main menu
Select option [1-5]: """,
            end="",
        )
        choice = input().strip()
        if choice == "1":
            handle_album_plan(album_state)
        elif choice == "2":
            handle_album_generation(album_state)
        elif choice == "3":
            handle_album_status(album_state)
        elif choice == "4":
            handle_album_download(album_state)
        elif choice == "5":
            break
        else:
            print("Invalid option. Please select a number between 1 and 5.")


def _interactive_preview(result, preview_name: str, prompt: str) -> Optional[str]:
    """统一的预览-询问流程。"""

    _ensure_outputs_dir()
    preview_path = OUTPUT_DIR / preview_name
    synthesize_preview(result, preview_path)
    play_audio(preview_path)
    if preview_path.exists():
        preview_path.unlink()
    return input(prompt).strip().lower()


def handle_check_environment() -> None:
    """执行环境检查并打印结果。"""

    status = generator.check_environment()
    print("Environment summary:")
    for key, value in status.items():
        print(f" - {key}: {'ok' if value else 'missing'}")


def handle_generate_motif(state: SessionState) -> bool:
    """负责动机生成的交互循环。"""

    while True:
        motif = generator.generate_motif()
        answer = _interactive_preview(
            motif,
            "preview_motif.wav",
            "Do you like this motif? (y = accept / r = regenerate / q = cancel): ",
        )
        if answer == "y":
            state["motif"] = motif
            motif_path = OUTPUT_DIR / "motif.json"
            if motif_path.exists():
                state["motif_path"] = motif_path
                try:
                    with motif_path.open("r", encoding="utf-8") as fh:
                        motif_meta = json.load(fh)
                    state["scale"] = motif_meta.get("scale")
                except (OSError, json.JSONDecodeError):
                    state["scale"] = None
            print("Motif accepted. Proceed to melody stage.")
            return True
        if answer == "r":
            print("Regenerating motif...")
            continue
        print("Motif generation cancelled.")
        return False


def handle_generate_melody_and_arrangement(state: SessionState) -> bool:
    """生成旋律与编曲，允许多次试听。"""

    motif = state.get("motif")
    if not motif:
        print("Please generate a motif first.")
        return False

    melody = None
    while True:
        melody = generator.expand_motif_to_melody(motif)
        answer = _interactive_preview(
            melody,
            "preview_melody.wav",
            "Do you like this melody? (y = accept / r = regenerate / q = cancel): ",
        )
        if answer == "y":
            print("Melody accepted. Building arrangement...")
            break
        if answer == "r":
            print("Regenerating melody...")
            continue
        print("Melody stage cancelled.")
        return False

    while True:
        arrangement = generator.arrange_to_tracks(melody)
        answer = _interactive_preview(
            arrangement,
            "preview_arrangement.wav",
            "Do you like this arrangement? (y = accept / r = regenerate / q = cancel): ",
        )
        if answer == "y":
            state["melody"] = melody
            state["arrangement"] = arrangement
            arrangement_path = OUTPUT_DIR / "arrangement.json"
            if arrangement_path.exists():
                state["arrangement_path"] = arrangement_path
            state["bpm"] = arrangement.get("bpm")
            state["length_beats"] = _compute_length_beats(arrangement)
            print("Arrangement accepted. Ready to render.")
            return True
        if answer == "r":
            print("Regenerating arrangement...")
            continue
            print("Arrangement stage cancelled.")
            return False


def handle_auto_mix(state: SessionState) -> None:
    """执行自动混音并立即生成预览。"""

    arrangement = _load_arrangement(state)
    if not arrangement:
        print("Please generate melody and arrangement first.")
        return

    print("Calculating auto mix suggestions...")
    params = mixer.auto_mix(arrangement)
    if _perform_mix(state, params):
        print("Auto mix applied. Preview played if audio backend is available.")


def handle_manual_mix(state: SessionState) -> None:
    """询问各项参数后执行手动混音。"""

    arrangement = _load_arrangement(state)
    if not arrangement:
        print("Please generate melody and arrangement first.")
        return

    defaults = state.get("mix_params")
    if not isinstance(defaults, dict):
        defaults = mixer.auto_mix(arrangement)

    def _prompt_value(label: str, current: float) -> float:
        prompt = f"{label} [{current:.2f}]: "
        user_input = input(prompt).strip()
        if not user_input:
            return current
        try:
            return float(user_input)
        except ValueError:
            print("Invalid number. Keeping previous value.")
            return current

    params = {
        "main_volume": _prompt_value("Main volume (0-1)", defaults.get("main_volume", 0.85)),
        "bg_volume": _prompt_value("Background volume (0-1)", defaults.get("bg_volume", 0.6)),
        "noise_volume": _prompt_value("Noise volume (0-1)", defaults.get("noise_volume", 0.35)),
        "panning": {
            "main": _prompt_value("Main panning (-1 left / 1 right)", defaults.get("panning", {}).get("main", 0.0)),
            "bg": _prompt_value("Background panning", defaults.get("panning", {}).get("bg", 0.3)),
            "noise": _prompt_value("Noise panning", defaults.get("panning", {}).get("noise", -0.25)),
        },
        "reverb": _prompt_value("Reverb amount (0-1)", defaults.get("reverb", 0.18)),
        "eq_low": _prompt_value("EQ Low (0-2)", defaults.get("eq_low", 1.0)),
        "eq_high": _prompt_value("EQ High (0-2)", defaults.get("eq_high", 1.05)),
    }

    if _perform_mix(state, params):
        print("Manual mix applied. You can run Preview Mix again if needed.")


def handle_preview_mix(state: SessionState) -> None:
    """重新生成并播放最新混音的 5 秒预览。"""

    mix_path = state.get("mix_output")
    if not mix_path:
        print("No mix available yet. Please run Auto Mix or Manual Mix first.")
        return

    try:
        preview_path = mixer.preview_mix(Path(mix_path))
        state["mix_preview"] = preview_path
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to generate preview: {exc}")
        return

    try:
        play_audio(preview_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Unable to play preview: {exc}")


def handle_mix_menu(state: SessionState) -> None:
    """混音控制子菜单，允许自动或手动调整参数。"""

    while True:
        print(
            """
Mix & Effect Control
1) Auto Mix
2) Manual Mix
3) Preview Mix
4) Back
Select option [1-4]: """,
            end="",
        )
        choice = input().strip()
        if choice == "1":
            handle_auto_mix(state)
        elif choice == "2":
            handle_manual_mix(state)
        elif choice == "3":
            handle_preview_mix(state)
        elif choice == "4":
            break
        else:
            print("Invalid option. Please select a number between 1 and 4.")


def handle_render_and_export(state: SessionState, keep_wav: bool) -> bool:
    """渲染最终音频并导出 MP3。"""

    arrangement = state.get("arrangement")
    if not arrangement:
        print("Please generate melody and arrangement first.")
        return False

    _ensure_outputs_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_path = OUTPUT_DIR / f"final_{timestamp}.wav"
    mp3_path = OUTPUT_DIR / f"final_{timestamp}.mp3"

    try:
        synthesize_8bit_wav(arrangement, wav_path)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to render WAV: {exc}")
        return False

    try:
        wav_to_mp3(wav_path, mp3_path, keep_wav=keep_wav)
    except Exception as exc:  # noqa: BLE001
        print(f"MP3 export failed: {exc}. WAV file remains at {wav_path}")
        state["final_mp3"] = wav_path
        return False

    state["final_mp3"] = mp3_path
    state["mp3_path"] = mp3_path
    if keep_wav:
        state["wav_path"] = wav_path
    print(f"Final MP3 ready at {mp3_path}")
    return True


def handle_cleanup(state: SessionState, auto_confirm: bool = False) -> None:
    """清理 outputs 目录并重置状态。"""

    cleanup_outputs(auto_confirm=auto_confirm)
    state.clear()


def handle_list_projects() -> None:
    """列出数据库中已保存的所有项目。"""

    project_db.init_db()
    projects = project_db.list_projects()
    if not projects:
        print("No saved projects found.")
        return
    print("Saved projects:")
    for item in projects:
        print(
            " - #{id}: {name} | created_at={created_at} | length={length} | bpm={bpm}".format(
                id=item.get("id"),
                name=item.get("name"),
                created_at=item.get("created_at"),
                length=item.get("length"),
                bpm=item.get("bpm"),
            )
        )


def _prepare_project_payload(state: SessionState) -> dict:
    """整理当前状态中的项目数据，返回写库所需的字段。"""

    arrangement = state.get("arrangement")
    arrangement_path = state.get("arrangement_path")
    if arrangement is None and arrangement_path and Path(arrangement_path).exists():
        try:
            with Path(arrangement_path).open("r", encoding="utf-8") as fh:
                arrangement = json.load(fh)
            state["arrangement"] = arrangement
        except (OSError, json.JSONDecodeError):
            arrangement = None

    length_beats = state.get("length_beats")
    if length_beats is None:
        length_beats = _compute_length_beats(arrangement)
        if length_beats is not None:
            state["length_beats"] = length_beats

    bpm = state.get("bpm")
    if bpm is None and isinstance(arrangement, dict):
        bpm = arrangement.get("bpm")
        state["bpm"] = bpm

    motif_path = state.get("motif_path")
    if motif_path:
        motif_path = Path(motif_path)
    arrangement_path_obj = Path(arrangement_path) if arrangement_path else None

    scale = state.get("scale")
    if scale is None and motif_path and motif_path.exists():
        try:
            with motif_path.open("r", encoding="utf-8") as fh:
                motif_meta = json.load(fh)
            scale = motif_meta.get("scale")
            state["scale"] = scale
        except (OSError, json.JSONDecodeError):
            scale = None

    mp3_path = state.get("mp3_path")
    if mp3_path:
        mp3_path = Path(mp3_path)

    return {
        "motif_path": motif_path,
        "arrangement_path": arrangement_path_obj,
        "mp3_path": mp3_path,
        "bpm": _safe_int(bpm),
        "scale": scale,
        "length": _safe_int(length_beats),
    }


def handle_save_project(state: SessionState) -> None:
    """保存当前会话的项目数据到 SQLite。"""

    project_db.init_db()
    mp3_path = state.get("mp3_path")
    if not mp3_path:
        print("No final MP3 available. Please render a project before saving.")
        return

    name = input("Enter project name (leave blank for timestamp): ").strip()
    if not name:
        name = datetime.now().strftime("Project %Y-%m-%d %H:%M:%S")

    payload = _prepare_project_payload(state)

    try:
        project_id = project_db.save_project(
            name=name,
            motif_path=payload["motif_path"],
            arrangement_path=payload["arrangement_path"],
            mp3_path=payload["mp3_path"],
            bpm=payload["bpm"],
            scale=payload["scale"],
            length=payload["length"],
        )
        print(f"Project saved with id #{project_id}.")
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to save project: {exc}")


def handle_load_project(state: SessionState) -> None:
    """加载指定项目并更新当前会话状态，同时播放 MP3。"""

    project_db.init_db()
    project_id = input("Enter project id to load: ").strip()
    if not project_id.isdigit():
        print("Invalid project id. Please enter a numeric value.")
        return

    try:
        project = project_db.load_project(int(project_id))
    except ValueError as exc:
        print(str(exc))
        return

    state.clear()
    state["loaded_project"] = project

    motif_path = project.get("motif_path")
    if motif_path and Path(motif_path).exists():
        state["motif_path"] = Path(motif_path)
        try:
            with Path(motif_path).open("r", encoding="utf-8") as fh:
                motif_meta = json.load(fh)
            state["motif"] = motif_meta.get("motif")
            state["scale"] = motif_meta.get("scale")
        except (OSError, json.JSONDecodeError):
            pass

    arrangement_path = project.get("arrangement_path")
    if arrangement_path and Path(arrangement_path).exists():
        state["arrangement_path"] = Path(arrangement_path)
        try:
            with Path(arrangement_path).open("r", encoding="utf-8") as fh:
                arrangement = json.load(fh)
            state["arrangement"] = arrangement
            state["bpm"] = arrangement.get("bpm")
            state["length_beats"] = _compute_length_beats(arrangement)
        except (OSError, json.JSONDecodeError):
            pass

    mp3_path = project.get("mp3_path")
    if mp3_path:
        candidate = Path(mp3_path)
        state["mp3_path"] = candidate
        state["final_mp3"] = candidate
        if candidate.exists():
            print(f"Playing project MP3 from {candidate}")
            try:
                play_audio(candidate)
            except Exception as exc:  # noqa: BLE001
                print(f"Unable to play audio: {exc}")
        else:
            print("MP3 file referenced by project is missing.")

    print(
        "Loaded project #{id} '{name}'.".format(
            id=project.get("id"),
            name=project.get("name"),
        )
    )


def handle_delete_project() -> None:
    """删除指定项目，并移除数据库中的记录。"""

    project_db.init_db()
    project_id = input("Enter project id to delete: ").strip()
    if not project_id.isdigit():
        print("Invalid project id. Please enter a numeric value.")
        return

    try:
        project_db.delete_project(int(project_id))
        print(f"Project #{project_id} deleted.")
    except ValueError as exc:
        print(str(exc))


def handle_project_menu(state: SessionState) -> None:
    """项目管理子菜单，循环处理用户输入。"""

    while True:
        print(
            """
Project Management
1) List Projects
2) Load Project
3) Save Current Project
4) Delete Project
5) Back to Main Menu
Select option [1-5]: """,
            end="",
        )
        choice = input().strip()
        if choice == "1":
            handle_list_projects()
        elif choice == "2":
            handle_load_project(state)
        elif choice == "3":
            handle_save_project(state)
        elif choice == "4":
            handle_delete_project()
        elif choice == "5":
            break
        else:
            print("Invalid option. Please select a number between 1 and 5.")


def run_all(keep_wav: bool) -> None:
    """执行从检查到清理的自动化流程。"""

    state = SessionState()
    handle_check_environment()
    if not handle_generate_motif(state):
        return
    if not handle_generate_melody_and_arrangement(state):
        return
    if not handle_render_and_export(state, keep_wav=keep_wav):
        return

    project_db.init_db()
    payload = _prepare_project_payload(state)
    if payload["mp3_path"] is None:
        print("Auto-save skipped because no MP3 path was found.")
        return

    auto_name = datetime.now().strftime("Auto Project %Y-%m-%d %H:%M:%S")
    try:
        project_id = project_db.save_project(
            name=auto_name,
            motif_path=payload["motif_path"],
            arrangement_path=payload["arrangement_path"],
            mp3_path=payload["mp3_path"],
            bpm=payload["bpm"],
            scale=payload["scale"],
            length=payload["length"],
        )
        print(f"Auto-saved project #{project_id} as '{auto_name}'.")
    except Exception as exc:  # noqa: BLE001
        print(f"Auto-save failed: {exc}")
    else:
        print("Outputs kept so the saved project can be revisited later.")


def main() -> None:
    """CLI 主函数，负责解析参数并运行菜单逻辑。"""

    parser = argparse.ArgumentParser(description="MotifMaker 8-bit Simplified CLI")
    parser.add_argument("--run-all", action="store_true", help="Run the complete pipeline automatically")
    parser.add_argument("--keep-wav", action="store_true", help="Keep intermediate WAV files after MP3 export")
    args = parser.parse_args()

    if args.run_all:
        run_all(args.keep_wav)
        return

    state: SessionState = SessionState()
    project_db.init_db()

    album_state: AlbumSession = AlbumSession()

    while True:
        print(
            """
MotifMaker - 8bit Simplified CLI
1) Check environment
2) Generate motif
3) Generate melody & arrangement
4) Render 8-bit and export MP3
5) Cleanup / Reset (delete outputs)
6) Mix & Effect Control
7) Album / Batch Export
8) Project Management
9) Exit
Select option [1-9]: """,
            end="",
        )
        choice = input().strip()

        if choice == "1":
            handle_check_environment()
        elif choice == "2":
            handle_generate_motif(state)
        elif choice == "3":
            handle_generate_melody_and_arrangement(state)
        elif choice == "4":
            handle_render_and_export(state, keep_wav=args.keep_wav)
        elif choice == "5":
            handle_cleanup(state)
        elif choice == "6":
            handle_mix_menu(state)
        elif choice == "7":
            handle_album_menu(album_state)
        elif choice == "8":
            handle_project_menu(state)
        elif choice == "9":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select a number between 1 and 9.")


if __name__ == "__main__":
    main()

