"""SQLite 工具模块，负责 MotifMaker 项目的持久化存储。"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Generator, Iterable, List, Optional

# 数据目录默认放在仓库的 data/ 路径下，保持与音频输出分离
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
# 默认数据库文件位置，可通过环境变量覆盖，便于测试替换
DEFAULT_DB_PATH = DATA_DIR / "motifmaker.db"


def _get_db_path() -> Path:
    """返回当前有效的数据库路径，支持通过环境变量覆盖。"""

    env_path = os.getenv("MOTIFMAKER_DB_PATH")
    if env_path:
        override_path = Path(env_path)
        override_path.parent.mkdir(parents=True, exist_ok=True)
        return override_path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_PATH


@contextmanager
def _get_connection() -> Generator[sqlite3.Connection, None, None]:
    """上下文管理器：打开 SQLite 连接并自动设置 row_factory。"""

    db_path = _get_db_path()
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, object]:
    """将 sqlite3.Row 转换为普通字典，便于序列化与打印。"""

    return {key: row[key] for key in row.keys()}


def init_db() -> None:
    """Initialize database schema and ensure the projects table exists.\n初始化数据库结构，确保 projects 表已经就绪。"""

    with _get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                motif_path TEXT,
                arrangement_path TEXT,
                mp3_path TEXT,
                bpm INTEGER,
                scale TEXT,
                length INTEGER
            );
            """
        )
        connection.commit()


def save_project(
    name: str,
    motif_path: Optional[os.PathLike[str] | str],
    arrangement_path: Optional[os.PathLike[str] | str],
    mp3_path: Optional[os.PathLike[str] | str],
    bpm: Optional[int],
    scale: Optional[str],
    length: Optional[int],
) -> int:
    """Save a new project entry and return its ID.\n保存新的项目记录并返回对应的主键 ID。"""

    created_at = datetime.now(UTC).isoformat()
    motif_value = str(motif_path) if motif_path else None
    arrangement_value = str(arrangement_path) if arrangement_path else None
    mp3_value = str(mp3_path) if mp3_path else None

    with _get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO projects (
                name, created_at, motif_path, arrangement_path, mp3_path, bpm, scale, length
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, created_at, motif_value, arrangement_value, mp3_value, bpm, scale, length),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_projects() -> List[Dict[str, object]]:
    """Return all saved projects ordered by creation time descending.\n按创建时间倒序返回所有项目记录。"""

    with _get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT id, name, created_at, motif_path, arrangement_path, mp3_path, bpm, scale, length
            FROM projects
            ORDER BY datetime(created_at) DESC, id DESC
            """
        )
        rows = cursor.fetchall()
        return [_row_to_dict(row) for row in rows]


def load_project(project_id: int) -> Dict[str, object]:
    """Fetch a single project entry by ID.\n根据主键 ID 读取单个项目记录。"""

    with _get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT id, name, created_at, motif_path, arrangement_path, mp3_path, bpm, scale, length
            FROM projects
            WHERE id = ?
            """,
            (project_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Project with id {project_id} not found")
        return _row_to_dict(row)


def delete_project(project_id: int) -> None:
    """Remove a project and delete related files if they still exist.\n删除指定项目并清理关联文件（若文件仍存在）。"""

    project = load_project(project_id)
    file_fields: Iterable[str] = ("motif_path", "arrangement_path", "mp3_path")
    for field in file_fields:
        path_value = project.get(field)
        if not path_value:
            continue
        candidate = Path(path_value)
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                # 若文件已被占用或无权限，忽略错误以免打断删除流程
                pass

    with _get_connection() as connection:
        connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        connection.commit()


def rename_project(project_id: int, new_name: str) -> None:
    """Rename an existing project entry.\n更新既有项目的名称信息。"""

    with _get_connection() as connection:
        cursor = connection.execute(
            "UPDATE projects SET name = ? WHERE id = ?",
            (new_name, project_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Project with id {project_id} not found")
