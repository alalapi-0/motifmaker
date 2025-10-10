"""配额存储抽象：为每日免费额度提供可替换的后端实现。"""

from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Dict, Optional, Tuple


class BaseQuotaStorage(ABC):
    """每日配额存储抽象基类。"""

    @abstractmethod
    def incr_and_check(self, day: str, subject: str, limit: int) -> Tuple[bool, int]:
        """自增指定主体的当日计数并返回是否仍在额度内。"""

    @abstractmethod
    def get(self, day: str, subject: str) -> int:
        """查询指定主体当日已使用次数。"""

    @abstractmethod
    def reset(self, day: str, subject: str) -> None:
        """重置主体当日计数，通常用于测试或后台人工干预。"""


class InMemoryQuotaStorage(BaseQuotaStorage):
    """基于内存字典的配额实现，仅适合单进程开发调试。"""

    def __init__(self) -> None:
        self._counts: Dict[Tuple[str, str], int] = {}
        self._lock = threading.Lock()

    def incr_and_check(self, day: str, subject: str, limit: int) -> Tuple[bool, int]:
        """中文注释：使用线程锁保证同一进程多协程同时写入时的数据一致性。"""

        key = (day, subject)
        with self._lock:
            current = self._counts.get(key, 0) + 1
            self._counts[key] = current
        if limit <= 0:
            return True, current
        return current <= limit, current

    def get(self, day: str, subject: str) -> int:
        key = (day, subject)
        with self._lock:
            return self._counts.get(key, 0)

    def reset(self, day: str, subject: str) -> None:
        key = (day, subject)
        with self._lock:
            self._counts.pop(key, None)


class SQLiteQuotaStorage(BaseQuotaStorage):
    """基于 SQLite 的配额实现，适合单机或容器内持久化使用。"""

    def __init__(self, path: str) -> None:
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # 中文注释：check_same_thread=False 允许在不同线程复用连接，配合线程锁保证安全。
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                day TEXT NOT NULL,
                subject TEXT NOT NULL,
                count INTEGER NOT NULL,
                PRIMARY KEY (day, subject)
            )
            """
        )
        self._conn.commit()
        self._lock = threading.Lock()

    def incr_and_check(self, day: str, subject: str, limit: int) -> Tuple[bool, int]:
        """中文注释：SQLite 自增需要串行化写入，使用线程锁包裹事务。"""

        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO usage(day, subject, count) VALUES (?, ?, 0)",
                (day, subject),
            )
            self._conn.execute(
                "UPDATE usage SET count = count + 1 WHERE day = ? AND subject = ?",
                (day, subject),
            )
            cur = self._conn.execute(
                "SELECT count FROM usage WHERE day = ? AND subject = ?",
                (day, subject),
            )
            row = cur.fetchone()
            current = int(row[0]) if row else 0
            self._conn.commit()
        if limit <= 0:
            return True, current
        return current <= limit, current

    def get(self, day: str, subject: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "SELECT count FROM usage WHERE day = ? AND subject = ?",
                (day, subject),
            )
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def reset(self, day: str, subject: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM usage WHERE day = ? AND subject = ?",
                (day, subject),
            )
            self._conn.commit()


def create_quota_storage(backend: str, db_path: str) -> BaseQuotaStorage:
    """根据配置创建对应的配额存储实例。"""

    lowered = backend.lower().strip()
    if lowered == "memory":
        return InMemoryQuotaStorage()
    if lowered == "sqlite":
        return SQLiteQuotaStorage(db_path)
    if lowered == "redis":
        raise NotImplementedError("redis quota backend is not implemented yet")
    raise ValueError(f"unknown quota backend: {backend}")


def init_usage_db(path: str) -> SQLiteQuotaStorage:
    """向后兼容的初始化函数，旧代码可继续调用以确保 SQLite 表结构存在。"""

    return SQLiteQuotaStorage(path)


def today_str(tz: Optional[str] = "UTC") -> str:
    """返回指定时区的今日日期字符串（YYYY-MM-DD）。"""

    if tz and tz.upper() != "UTC":
        try:
            zone = ZoneInfo(tz)
        except Exception:  # pragma: no cover - 容错逻辑
            return datetime.now().astimezone().strftime("%Y-%m-%d")
        return datetime.now(zone).strftime("%Y-%m-%d")
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


__all__ = [
    "BaseQuotaStorage",
    "InMemoryQuotaStorage",
    "SQLiteQuotaStorage",
    "create_quota_storage",
    "init_usage_db",
    "today_str",
]
