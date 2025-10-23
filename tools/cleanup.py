"""提供输出目录清理工具，确保仓库保持干净。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

# 统一的输出目录路径
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def _iter_output_files() -> Iterable[Path]:
    """遍历 outputs 目录下的所有文件与子目录。"""

    if not OUTPUT_DIR.exists():
        return []
    return list(OUTPUT_DIR.iterdir())


def cleanup_outputs(auto_confirm: bool = False) -> int:
    """删除 outputs 目录下的临时文件，可选跳过确认。"""

    items = _iter_output_files()
    if not items:
        print("No runtime files to clean.")
        return 0

    print("Files scheduled for removal:")
    for path in items:
        print(f" - {path}")

    if not auto_confirm:
        answer = input("Type YES to confirm cleanup: ").strip()
        if answer != "YES":
            print("Cleanup cancelled.")
            return 0
    else:
        print("Auto confirmation enabled; proceeding with cleanup.")

    removed = 0
    for path in items:
        # 这里只删除运行时产物，不触及源码
        if path.is_file():
            path.unlink()
            removed += 1
        else:
            shutil.rmtree(path)
            removed += 1
    print(f"Removed {removed} item(s) from outputs directory.")
    return removed

