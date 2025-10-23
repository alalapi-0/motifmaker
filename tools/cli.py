"""MotifMaker 简化版 8-bit CLI 入口。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import generator
from . import db as project_db
from .cleanup import cleanup_outputs
from .synth import play_audio, synthesize_8bit_wav, synthesize_preview, wav_to_mp3

# 统一输出目录，所有临时文件都放在这里
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


class SessionState(dict):
    """用于跟踪当前会话状态的简单字典子类。"""

    motif: Optional[list]
    melody: Optional[list]
    arrangement: Optional[dict]
    final_mp3: Optional[Path]


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


def _ensure_outputs_dir() -> None:
    """确保输出目录存在。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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

    while True:
        print(
            """
MotifMaker - 8bit Simplified CLI
1) Check environment
2) Generate motif
3) Generate melody & arrangement
4) Render 8-bit and export MP3
5) Cleanup / Reset (delete outputs)
6) Project Management
7) Exit
Select option [1-7]: """,
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
            handle_project_menu(state)
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select a number between 1 and 7.")


if __name__ == "__main__":
    main()

