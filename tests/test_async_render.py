import asyncio
import base64
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from motifmaker.api import app
from motifmaker.task_manager import TaskManager

import motifmaker
from motifmaker import audio_render
from motifmaker.errors import RenderTimeout


@pytest.fixture(scope="session")
def anyio_backend():
    """强制 anyio 使用 asyncio 后端，避免测试依赖 trio。"""

    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_task_manager(monkeypatch):
    """中文注释：每个测试重置内存任务管理器，避免不同用例互相污染。"""

    manager = TaskManager(max_concurrency=5)
    monkeypatch.setattr(motifmaker, "task_manager", manager, raising=False)
    monkeypatch.setattr(audio_render, "task_manager", manager, raising=False)
    from motifmaker.config import PRO_USER_EMAILS

    PRO_USER_EMAILS.add("test@async.dev")
    audio_render.PRO_USER_EMAILS = PRO_USER_EMAILS
    monkeypatch.setattr(audio_render, "DAILY_FREE_QUOTA", 1000, raising=False)
    return manager


@pytest.fixture
async def async_client():
    """中文注释：使用 httpx.AsyncClient 驱动 FastAPI 应用，方便执行并发测试。"""

    async with httpx.AsyncClient(
        app=app,
        base_url="http://testserver",
        headers={"X-User-Email": "test@async.dev"},
    ) as client:
        yield client


async def _wait_for_task(client: httpx.AsyncClient, task_id: str, *, timeout: float = 30.0):
    """中文注释：轮询任务状态直到进入终态或超时，用于测试后台任务流程。"""

    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        resp = await client.get(f"/tasks/{task_id}")
        payload = resp.json()["result"]
        status = payload["status"]
        if status in {"done", "failed", "cancelled"}:
            return payload
        await asyncio.sleep(0.1)
    raise AssertionError("task did not complete in time")


@pytest.mark.anyio("asyncio")
async def test_render_task_is_non_blocking(async_client, anyio_backend):
    if anyio_backend != "asyncio":
        pytest.skip("only asyncio backend is supported in tests")
    """中文注释：同时创建多个任务，确认响应耗时保持在 200ms 内，证明事件循环未被阻塞。"""

    durations_ms: list[float] = []

    async def create_request(index: int) -> str:
        start = time.perf_counter()
        resp = await async_client.post(
            "/render/",
            files={"midi_file": (f"test_{index}.mid", b"MThd", "audio/midi")},
            data={"style": "cinematic", "intensity": "0.5"},
        )
        durations_ms.append((time.perf_counter() - start) * 1000)
        assert resp.status_code == 202
        return resp.json()["result"]["task_id"]

    task_ids = await asyncio.gather(*(create_request(i) for i in range(6)))
    durations_ms.sort()
    p95_index = max(0, int(len(durations_ms) * 0.95) - 1)
    assert durations_ms[p95_index] < 200, f"expected P95 <200ms, got {durations_ms[p95_index]:.2f}"

    results = await asyncio.gather(*(_wait_for_task(async_client, task_id) for task_id in task_ids))
    for snapshot in results:
        assert snapshot["status"] == "done"
        assert snapshot["result"]["audio_url"].startswith("/outputs/")


@pytest.mark.anyio("asyncio")
async def test_render_retry_and_timeout_paths(async_client, monkeypatch, anyio_backend):
    if anyio_backend != "asyncio":
        pytest.skip("only asyncio backend is supported in tests")
    """中文注释：验证重试逻辑与超时失败路径。"""

    attempts: dict[str, int] = {"count": 0}

    async def flaky_send() -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            response = httpx.Response(status_code=500, request=httpx.Request("POST", "https://fake"))
            raise httpx.HTTPStatusError("boom", request=response.request, response=response)
        content = base64.b64encode(b"RIFF").decode()
        return httpx.Response(
            status_code=200,
            headers={"content-type": "application/json"},
            json={"audio": f"data:audio/wav;base64,{content}"},
        )

    response = await audio_render.request_with_retry_async(flaky_send, retries=5, timeout=5)
    assert isinstance(response, httpx.Response)
    assert attempts["count"] == 3

    async def always_timeout() -> httpx.Response:  # pragma: no cover - helper
        raise httpx.TimeoutException("timeout")

    with pytest.raises(RenderTimeout):
        await audio_render.request_with_retry_async(always_timeout, retries=1, timeout=1)

    async def timeout_job(midi_path: Path, style: str, intensity: float, *, progress_callback=None):
        raise RenderTimeout("render provider timed out")

    monkeypatch.setattr(audio_render, "render_via_provider_async", timeout_job, raising=False)

    resp = await async_client.post(
        "/render/",
        files={"midi_file": ("timeout.mid", b"MThd", "audio/midi")},
    )
    task_id_timeout = resp.json()["result"]["task_id"]
    timeout_snapshot = await _wait_for_task(async_client, task_id_timeout)
    assert timeout_snapshot["status"] == "failed"
    assert timeout_snapshot["error"]["code"] == "E_RENDER_TIMEOUT"


@pytest.mark.anyio("asyncio")
async def test_cancel_task_flow(async_client, monkeypatch, anyio_backend):
    if anyio_backend != "asyncio":
        pytest.skip("only asyncio backend is supported in tests")
    """中文注释：任务创建后立即取消，允许任务在极短时间内完成或进入取消态。"""

    async def slow_render(
        midi_path: Path,
        style: str,
        intensity: float,
        *,
        progress_callback=None,
    ):
        out_dir = audio_render._safe_outputs_dir()
        dummy_path = out_dir / f"cancel_{uuid4().hex}.wav"
        if progress_callback:
            progress_callback(15)
        await asyncio.sleep(0.4)
        await asyncio.to_thread(dummy_path.write_bytes, b"RIFF")
        if progress_callback:
            progress_callback(90)
        return dummy_path, 0.5

    monkeypatch.setattr(audio_render, "render_via_provider_async", slow_render, raising=False)

    resp = await async_client.post(
        "/render/",
        files={"midi_file": ("cancel.mid", b"MThd", "audio/midi")},
    )
    task_id = resp.json()["result"]["task_id"]

    cancel_resp = await async_client.delete(f"/tasks/{task_id}")
    assert cancel_resp.status_code == 200

    snapshot = await _wait_for_task(async_client, task_id)
    assert snapshot["status"] in {"cancelled", "done"}
    if snapshot["status"] == "cancelled":
        assert snapshot["result"] is None
    else:
        assert snapshot["result"]["audio_url"].startswith("/outputs/")
