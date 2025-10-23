"""MotifMaker 简化版 8-bit CLI 入口。"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import generator
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
    print(f"Final MP3 ready at {mp3_path}")
    return True


def handle_cleanup(state: SessionState, auto_confirm: bool = False) -> None:
    """清理 outputs 目录并重置状态。"""

    cleanup_outputs(auto_confirm=auto_confirm)
    state.clear()


def run_all(keep_wav: bool) -> None:
    """执行从检查到清理的自动化流程。"""

    state = SessionState()
    handle_check_environment()
    if not handle_generate_motif(state):
        return
    if not handle_generate_melody_and_arrangement(state):
        return
    handle_render_and_export(state, keep_wav=keep_wav)
    print("Running cleanup as part of --run-all")
    handle_cleanup(state, auto_confirm=True)


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

    while True:
        print(
            """
MotifMaker - 8bit Simplified CLI
1) Check environment
2) Generate motif
3) Generate melody & arrangement
4) Render 8-bit and export MP3
5) Cleanup / Reset (delete outputs)
6) Exit
Select option [1-6]: """,
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
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please select a number between 1 and 6.")


if __name__ == "__main__":
    main()

