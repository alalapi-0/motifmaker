"""针对持久化数据库模块的行为测试。"""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path
from types import ModuleType
from typing import Tuple

import pytest


@pytest.fixture()
def temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Tuple[ModuleType, Path]:
    """为每个测试准备独立的临时数据库文件。"""

    db_path = tmp_path / "motifmaker.db"
    monkeypatch.setenv("MOTIFMAKER_DB_PATH", str(db_path))
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project_root))
    from tools import db as project_db  # 延迟导入以便覆盖环境变量

    reloaded = importlib.reload(project_db)
    reloaded.init_db()
    return reloaded, db_path


def test_init_db_creates_table(temp_db: Tuple[ModuleType, Path]) -> None:
    """验证 init_db 会创建 projects 表。"""

    project_db, db_path = temp_db
    assert db_path.exists(), "Database file should be created after init_db."
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        assert cursor.fetchone() is not None


def test_save_project_inserts_row(temp_db: Tuple[ModuleType, Path]) -> None:
    """验证 save_project 可正确插入记录。"""

    project_db, db_path = temp_db
    project_id = project_db.save_project(
        name="Test Project",
        motif_path="motif.json",
        arrangement_path="arrangement.json",
        mp3_path="track.mp3",
        bpm=120,
        scale="C_major",
        length=16,
    )
    assert isinstance(project_id, int)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute("SELECT COUNT(*) FROM projects")
        assert cursor.fetchone()[0] == 1


def test_list_projects_returns_correct_count(temp_db: Tuple[ModuleType, Path]) -> None:
    """验证 list_projects 返回的数量与写入一致。"""

    project_db, _ = temp_db
    project_db.save_project("First", None, None, "one.mp3", 100, "C_major", 8)
    project_db.save_project("Second", None, None, "two.mp3", 110, "A_minor", 12)
    projects = project_db.list_projects()
    assert len(projects) == 2


def test_load_project_returns_dict(temp_db: Tuple[ModuleType, Path]) -> None:
    """验证 load_project 返回字典数据。"""

    project_db, _ = temp_db
    project_id = project_db.save_project("Load Me", None, None, "load.mp3", 90, "C_major", 10)
    project = project_db.load_project(project_id)
    assert isinstance(project, dict)
    assert project["name"] == "Load Me"


def test_rename_project_updates_name(temp_db: Tuple[ModuleType, Path]) -> None:
    """验证 rename_project 可更新名称字段。"""

    project_db, _ = temp_db
    project_id = project_db.save_project("Old Name", None, None, "rename.mp3", 95, "A_minor", 14)
    project_db.rename_project(project_id, "New Name")
    project = project_db.load_project(project_id)
    assert project["name"] == "New Name"


def test_delete_project_removes_row_and_files(temp_db: Tuple[ModuleType, Path]) -> None:
    """验证 delete_project 会删除记录并尝试清理关联文件。"""

    project_db, db_path = temp_db
    dummy_dir = db_path.parent
    motif_file = dummy_dir / "motif.json"
    arrangement_file = dummy_dir / "arrangement.json"
    mp3_file = dummy_dir / "final.mp3"
    for file_path in (motif_file, arrangement_file, mp3_file):
        file_path.write_text("placeholder", encoding="utf-8")

    project_id = project_db.save_project(
        "To Delete",
        motif_file,
        arrangement_file,
        mp3_file,
        bpm=110,
        scale="C_major",
        length=18,
    )

    assert mp3_file.exists()
    project_db.delete_project(project_id)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute("SELECT COUNT(*) FROM projects")
        assert cursor.fetchone()[0] == 0
    assert not mp3_file.exists()
    assert not motif_file.exists()
    assert not arrangement_file.exists()
