"""异步任务管理器：用于在内存中调度渲染任务并控制并发度。

该模块提供一个轻量版的 TaskManager，仅依赖 asyncio 的原生能力，实现
任务排队、状态跟踪与取消。由于它使用进程内字典存储任务快照，因此只
适合单进程的开发/测试环境；在生产环境部署多实例或需要持久化时，应
替换为 Redis 等外部任务队列。所有关键步骤都写有中文注释，说明实现
细节与局限。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, Optional
from uuid import uuid4

from .errors import MMError, error_response


@dataclass
class TaskSnapshot:
    """任务状态快照结构，用于在 API 中返回任务当前信息。"""

    id: str
    created_at: datetime
    updated_at: datetime
    status: str = "queued"
    params: Dict[str, object] = field(default_factory=dict)
    result: Optional[object] = None
    error: Optional[object] = None
    logs: list[str] = field(default_factory=list)
    progress: int = 0


class TaskManager:
    """内存版异步任务管理器。

    中文设计说明：
    - 通过 ``asyncio.Semaphore`` 控制最大并发，避免一次性向外部 Provider
      发起过多请求；
    - 使用 ``asyncio.create_task`` 在事件循环中调度后台任务，确保 FastAPI
      的请求线程不会被阻塞；
    - 状态信息存储在进程内 ``dict``，因此仅适合单进程部署；如需多实例
      或持久化必须改造为集中式存储（如 Redis 队列）。
    """

    def __init__(self, max_concurrency: int = 2) -> None:
        # 中文注释：并发信号量设置为至少 1，防止传入非法配置导致完全不可用。
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        # 中文注释：任务快照存储任务状态，任务句柄用于取消/监控。
        self._snapshots: dict[str, TaskSnapshot] = {}
        self._handles: dict[str, asyncio.Task[object]] = {}

    def create_task(
        self,
        coro_factory: Callable[[str], Awaitable[object]],
        *,
        params: Optional[Dict[str, object]] = None,
    ) -> str:
        """创建后台任务并立即返回任务 ID。

        参数 ``coro_factory`` 会在内部包裹为携带任务 ID 的异步函数，方便
        任务执行过程中回写进度。任务创建后立即排队，调用方无需等待。
        """

        task_id = uuid4().hex
        now = datetime.now(timezone.utc)
        snapshot = TaskSnapshot(
            id=task_id,
            created_at=now,
            updated_at=now,
            status="queued",
            params=dict(params or {}),
        )
        self._snapshots[task_id] = snapshot

        async def runner_wrapper() -> None:
            await self._runner(task_id, lambda: coro_factory(task_id))

        # 中文注释：直接在当前事件循环中调度任务，确保无需额外线程。
        loop = asyncio.get_running_loop()
        handle = loop.create_task(runner_wrapper())
        self._handles[task_id] = handle
        return task_id

    async def _runner(
        self, task_id: str, coro_factory: Callable[[], Awaitable[object]]
    ) -> None:
        """实际执行后台任务并维护状态生命周期。"""

        await self._semaphore.acquire()
        try:
            self._set_status(task_id, "running")
            try:
                result = await coro_factory()
            except asyncio.CancelledError:
                # 中文注释：取消操作属于正常流程，记录状态后继续抛出让上游知晓。
                self._update_snapshot(task_id, status="cancelled")
                raise
            except Exception as exc:  # noqa: BLE001
                # 中文注释：捕获任意异常并记录统一结构；对 MMError 保留错误码。
                if isinstance(exc, MMError):
                    payload = error_response(exc)["error"]
                    payload["http_status"] = exc.http_status
                else:
                    payload = {"message": str(exc), "type": exc.__class__.__name__}
                self._update_snapshot(
                    task_id,
                    status="failed",
                    error=payload,
                    progress=100,
                )
            else:
                self._update_snapshot(task_id, status="done", result=result, progress=100)
        finally:
            # 中文注释：无论成功/失败都释放信号量，防止并发度被锁死。
            self._semaphore.release()

    def _set_status(self, task_id: str, status: str) -> None:
        self._update_snapshot(task_id, status=status)

    def _update_snapshot(self, task_id: str, **changes: object) -> None:
        snapshot = self._snapshots.get(task_id)
        if not snapshot:
            return
        for key, value in changes.items():
            if hasattr(snapshot, key):
                setattr(snapshot, key, value)  # type: ignore[arg-type]
        snapshot.updated_at = datetime.now(timezone.utc)

    def get(self, task_id: str) -> Optional[TaskSnapshot]:
        """返回任务的当前快照副本，供 API 查询。"""

        snapshot = self._snapshots.get(task_id)
        if not snapshot:
            return None
        # 中文注释：返回浅拷贝，避免外部无意间修改内部状态。
        copied = TaskSnapshot(
            id=snapshot.id,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
            status=snapshot.status,
            params=dict(snapshot.params),
            result=snapshot.result,
            error=snapshot.error,
            logs=list(snapshot.logs),
            progress=snapshot.progress,
        )
        return copied

    def cancel(self, task_id: str) -> bool:
        """尝试取消任务，若任务已结束则返回 False。"""

        handle = self._handles.get(task_id)
        if not handle:
            return False
        if handle.done():
            return False
        handle.cancel()
        return True

    def update_progress(self, task_id: str, progress: int) -> None:
        """更新任务进度，自动裁剪为 0~100。"""

        clipped = max(0, min(100, int(progress)))
        self._update_snapshot(task_id, progress=clipped)

    async def wait(self, task_id: str) -> Optional[TaskSnapshot]:
        """等待指定任务完成并返回最终快照。"""

        handle = self._handles.get(task_id)
        if not handle:
            return self.get(task_id)
        try:
            await handle
        except asyncio.CancelledError:
            # 中文注释：取消会在 ``get`` 中看到状态，此处无需额外处理。
            pass
        return self.get(task_id)


__all__ = ["TaskManager", "TaskSnapshot"]
