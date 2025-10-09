"""Motifmaker layered music generation package."""

from __future__ import annotations

from .config import RENDER_MAX_CONCURRENCY
from .task_manager import TaskManager

__all__ = ["__version__", "task_manager"]

__version__: str = "0.1.0"

# 中文注释：TaskManager 作为全局单例，便于 API/渲染模块共享任务队列。
# 该实现基于内存信号量，仅适合单进程部署；未来如需扩展到多实例，可在
# 此处替换为连接 Redis/消息队列的实现。
task_manager = TaskManager(max_concurrency=RENDER_MAX_CONCURRENCY)
