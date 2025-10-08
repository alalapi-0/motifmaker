"""每日配额统计模块：使用 SQLite 在单机环境记录调用次数。

中文注释：该实现面向开发/测试场景，依赖本地 SQLite 文件存储每日用量。
生产环境应使用集中式缓存/数据库（如 Redis、PostgreSQL）并结合鉴权体系，
以避免多实例部署时统计不一致的问题。"""

from __future__ import annotations

import sqlite3
import threading
from datetime import date
from pathlib import Path
from typing import Optional, Tuple

# 中文注释：全局变量存储数据库路径与互斥锁，避免并发写入竞态。
_DB_PATH: Optional[str] = None
_DB_LOCK = threading.Lock()


def init_usage_db(path: str) -> None:
    """初始化用量数据库，确保表结构存在。

    中文注释：
    - path 默认为 ``var/usage.db``，已在 .gitignore 忽略，避免误提交；
    - 若目录不存在会自动创建，确保在 CI/容器环境下运行无额外步骤；
    - 仅在进程启动时调用一次即可，多次调用会复用同一路径。
    """

    global _DB_PATH
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                day TEXT NOT NULL,
                key TEXT NOT NULL,
                count INTEGER NOT NULL,
                PRIMARY KEY (day, key)
            )
            """
        )
        conn.commit()
    _DB_PATH = str(db_path)


def today_key(email_or_ip: str) -> Tuple[str, str]:
    """生成当日配额统计使用的 (day, key) 元组。

    中文注释：
    - day 使用 ISO8601 格式（YYYY-MM-DD），方便跨语言对接；
    - key 直接使用 email 或 IP，实际部署时建议配合用户鉴权信息。
    """

    return date.today().isoformat(), email_or_ip


def incr_and_check(day: str, key: str, limit: int) -> bool:
    """对指定键自增一次用量，并返回是否仍在免费额度内。

    中文注释：
    - limit <= 0 表示不限次数，直接返回 True；
    - 采用悲观锁（线程锁 + 同步写入）简化并发控制，适用于开发单进程场景；
    - 若超过额度返回 False，由调用方决定是否抛出 429。
    """

    if limit <= 0:
        return True
    if not _DB_PATH:
        raise RuntimeError("usage db not initialized")

    with _DB_LOCK:
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO usage(day, key, count) VALUES (?, ?, 0)",
                (day, key),
            )
            conn.execute(
                "UPDATE usage SET count = count + 1 WHERE day = ? AND key = ?",
                (day, key),
            )
            cur = conn.execute(
                "SELECT count FROM usage WHERE day = ? AND key = ?",
                (day, key),
            )
            row = cur.fetchone()
            current = int(row[0]) if row else 0
            conn.commit()
    return current <= limit


__all__ = ["init_usage_db", "today_key", "incr_and_check"]
