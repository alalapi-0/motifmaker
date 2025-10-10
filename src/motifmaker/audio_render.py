"""音频渲染逻辑与 API 路由：提供异步任务化的渲染能力。

中文注释说明：
- 默认通过内存任务队列异步执行渲染，避免阻塞 FastAPI 事件循环；
- 对外暴露 /render/ 与 /tasks/ 路由，前端需轮询任务状态获取音频结果；
- 支持开发模式下的同步调试，生产环境默认走异步流程。"""

from __future__ import annotations

import asyncio
import base64
import json
import time
import wave
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

import httpx
import numpy as np
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from . import task_manager
from .config import (
    APP_ENV,
    AUDIO_PROVIDER,
    DAILY_FREE_QUOTA,
    HF_API_TOKEN,
    HF_MODEL,
    OUTPUT_DIR,
    QUOTA_BACKEND,
    REPLICATE_API_TOKEN,
    REPLICATE_MODEL,
    RENDER_MAX_SECONDS,
    RENDER_TIMEOUT_SEC,
    USAGE_DB_PATH,
)
from .auth import is_pro_token, require_token
from .errors import ConfigError, MMError, RenderError, RenderTimeout, ValidationError, error_response
from .logging_setup import get_logger
from .quota import BaseQuotaStorage, create_quota_storage, today_str
from .ratelimit import rate_limiter
from .task_manager import TaskSnapshot
from .utils import ensure_directory

# 中文注释：保持原有的 /render 路由前缀，新增任务查询路由。
router = APIRouter(prefix="/render", tags=["AudioRender"])
tasks_router = APIRouter(prefix="/tasks", tags=["RenderTasks"])
logger = get_logger(__name__)

ensure_dir = ensure_directory


_quota_storage: BaseQuotaStorage | None = None


def set_quota_storage(storage: BaseQuotaStorage) -> None:
    """显式注入配额存储实例，方便应用启动时统一创建。"""

    global _quota_storage
    _quota_storage = storage


def _get_quota_storage() -> BaseQuotaStorage:
    """延迟创建配额存储，确保测试或脚本运行时也能正常计数。"""

    global _quota_storage
    if _quota_storage is None:
        _quota_storage = create_quota_storage(QUOTA_BACKEND, USAGE_DB_PATH)
    return _quota_storage


def _safe_outputs_dir() -> Path:
    """中文注释：确保输出目录存在并返回其解析后的绝对路径。"""

    out = ensure_dir(OUTPUT_DIR)
    return Path(out).resolve()


def _resolve_under(base: Path, candidate: Path) -> Path:
    """中文注释：统一的安全路径解析工具，确保 ``candidate`` 位于 ``base`` 下。"""

    resolved_base = base.resolve()
    relative_candidate = candidate
    if candidate.is_absolute():
        combined = candidate.resolve()
        parts = combined.parts
        if len(parts) > 1 and parts[1] == resolved_base.name:
            trimmed = Path(*parts[2:]) if len(parts) > 2 else Path(".")
            combined = (resolved_base / trimmed).resolve()
        try:
            combined.relative_to(resolved_base)
        except ValueError as exc:  # noqa: PERF203
            raise ValidationError(
                "midi_path must be inside outputs/",
                details={"path": str(candidate)},
            ) from exc
        return combined

    if not candidate.is_absolute():
        parts = candidate.parts
        if parts and parts[0] == resolved_base.name:
            relative_candidate = Path(*parts[1:]) if len(parts) > 1 else Path(".")
        else:
            relative_candidate = candidate
        combined = (resolved_base / relative_candidate).resolve()
        try:
            combined.relative_to(resolved_base)
        except ValueError as exc:  # noqa: PERF203
            raise ValidationError(
                "midi_path must be inside outputs/",
                details={"path": str(candidate)},
            ) from exc
        return combined

    return candidate.resolve()


def _extension_from_content_type(content_type: str) -> str:
    """根据 Content-Type 推断文件扩展名，缺省为 ``.wav``。"""

    content_type = content_type.lower()
    if "wav" in content_type:
        return ".wav"
    if "mpeg" in content_type or "mp3" in content_type:
        return ".mp3"
    if "flac" in content_type:
        return ".flac"
    if "ogg" in content_type:
        return ".ogg"
    return ".wav"


def _decode_base64_audio(payload: str) -> Tuple[bytes, str]:
    """解码 base64 音频字符串并返回二进制数据与扩展名。"""

    if payload.startswith("data:"):
        header, _, body = payload.partition(",")
        if "base64" not in header:
            raise RenderError("unsupported data URI format", details={"header": header})
        mime = header.split(";")[0].replace("data:", "", 1)
        return base64.b64decode(body), _extension_from_content_type(mime)
    return base64.b64decode(payload), ".wav"


async def request_with_retry_async(
    send_async: Callable[[], Awaitable[httpx.Response]],
    *,
    retries: int = 2,
    backoff: float = 1.6,
    timeout: float = RENDER_TIMEOUT_SEC,
) -> httpx.Response:
    """使用异步客户端实现指数退避的请求重试。"""

    attempts = 0
    delay = 1.0
    deadline = time.monotonic() + max(1.0, float(timeout))
    last_exc: Optional[Exception] = None

    while attempts <= retries:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RenderTimeout("render provider timed out")
        try:
            response = await send_async()
            return response
        except RenderTimeout:
            raise
        except httpx.TimeoutException as exc:
            raise RenderTimeout("render provider timed out") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429 or 500 <= status < 600:
                last_exc = exc
            else:
                raise RenderError(
                    f"provider responded with status {status}",
                    details={"status": status},
                ) from exc
        except Exception as exc:  # noqa: BLE001
            last_exc = exc

        attempts += 1
        if attempts > retries:
            break

        sleep_time = min(delay, max(0.0, deadline - time.monotonic()))
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        delay *= backoff

    if isinstance(last_exc, RenderError):
        raise last_exc
    if last_exc is not None:
        raise RenderError("provider request failed", details={"reason": str(last_exc)}) from last_exc
    raise RenderError("provider request failed")


async def _download_audio_async(url: str, timeout: float) -> Tuple[bytes, str]:
    """异步下载远程音频 URL，返回二进制数据与扩展名。"""

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def send() -> httpx.Response:
            response = await client.get(url)
            response.raise_for_status()
            return response

        response = await request_with_retry_async(send, timeout=timeout)
        content_type = response.headers.get("content-type", "audio/wav")
        suffix = _extension_from_content_type(content_type)
        return response.content, suffix


def _compose_prompt(style: str, intensity: float) -> str:
    """中文注释：根据风格与强度拼接文本提示，供模型生成音乐参考。"""

    clipped = max(0.0, min(intensity, 1.0))
    return f"{style} soundtrack, intensity={clipped:.2f}, 120bpm, 4/4"


def _sine_wav(
    path: Path,
    seconds: float = 6.0,
    samplerate: int = 44100,
    freq: float = 440.0,
) -> float:
    """中文注释：生成一段指定参数的正弦波音频，用于占位返回。"""

    t = np.linspace(0, seconds, int(samplerate * seconds), endpoint=False)
    fade = np.linspace(0, 1, len(t))
    waveform = 0.2 * np.sin(2 * np.pi * freq * t) * fade
    waveform_int16 = (waveform * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(waveform_int16.tobytes())
    return seconds


def _derive_audio_name(midi_name: str, suffix: str = ".wav") -> str:
    stem = Path(midi_name).stem or "track"
    ts = int(time.time())
    return f"{stem}_{ts}{suffix}"


async def _render_placeholder_async(
    midi_path: Path,
    style: str,
    intensity: float,
    progress: Callable[[int], None],
) -> Tuple[Path, float]:
    """中文注释：本地占位渲染，使用线程池避免阻塞主事件循环。"""

    progress(20)
    out_dir = _safe_outputs_dir()
    seconds = float(min(RENDER_MAX_SECONDS, 3))
    out_path = out_dir / _derive_audio_name(midi_path.name, ".wav")
    base_freq = 440.0
    freq = base_freq + max(0.0, min(intensity, 1.0)) * 100.0
    duration = await asyncio.to_thread(_sine_wav, out_path, seconds=seconds, freq=freq)
    progress(90)
    return out_path, duration


async def _render_hf_async(
    midi_path: Path,
    style: str,
    intensity: float,
    timeout: float,
    progress: Callable[[int], None],
) -> Tuple[Path, float]:
    """中文注释：异步调用 Hugging Face 推理接口并轮询结果。"""

    progress(15)
    prompt = _compose_prompt(style, intensity)
    url = HF_MODEL if HF_MODEL.startswith("http") else f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Accept": "application/json",
    }
    out_dir = _safe_outputs_dir()

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def send() -> httpx.Response:
            response = await client.post(url, headers=headers, json={"inputs": prompt})
            if response.status_code == 202:
                raise httpx.HTTPStatusError("model loading", request=response.request, response=response)
            response.raise_for_status()
            return response

        response = await request_with_retry_async(send, timeout=timeout)

    content_type = response.headers.get("content-type", "application/json")
    suffix = ".wav"
    audio_bytes: Optional[bytes] = None

    if content_type.startswith("audio"):
        suffix = _extension_from_content_type(content_type)
        audio_bytes = response.content
    else:
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise RenderError("unexpected hugging face response", details={"content_type": content_type}) from exc

        if isinstance(payload, dict):
            candidate = payload.get("audio") or payload.get("generated_audio") or payload.get("output")
            if isinstance(candidate, list) and candidate:
                candidate = candidate[0]
            if isinstance(candidate, str):
                if candidate.startswith("http"):
                    audio_bytes, suffix = await _download_audio_async(candidate, timeout)
                else:
                    audio_bytes, suffix = _decode_base64_audio(candidate)
        if audio_bytes is None:
            raise RenderError("hugging face response missing audio", details={"payload": payload})

    out_path = out_dir / _derive_audio_name(midi_path.name, suffix)
    await asyncio.to_thread(out_path.write_bytes, audio_bytes)
    progress(95)
    return out_path, float(RENDER_MAX_SECONDS)


async def _render_replicate_async(
    midi_path: Path,
    style: str,
    intensity: float,
    timeout: float,
    progress: Callable[[int], None],
) -> Tuple[Path, float]:
    """中文注释：使用 Replicate 异步预测 API 生成音频并跟踪进度。"""

    prompt = _compose_prompt(style, intensity)
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": REPLICATE_MODEL,
        "input": {
            "prompt": prompt,
            "duration": RENDER_MAX_SECONDS,
        },
    }
    out_dir = _safe_outputs_dir()
    start = time.monotonic()

    async with httpx.AsyncClient(timeout=timeout) as client:
        async def create_prediction() -> httpx.Response:
            response = await client.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
            response.raise_for_status()
            return response

        creation = await request_with_retry_async(create_prediction, timeout=timeout)
        data = creation.json()
        prediction_id = data.get("id")
        if not prediction_id:
            raise RenderError("replicate response missing id", details={"response": data})

        status = data.get("status")
        if status == "failed":
            raise RenderError("replicate prediction failed", details={"response": data})

        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        poll_delay = 2.0
        current_progress = 20
        progress(current_progress)

        while True:
            if time.monotonic() - start > timeout:
                raise RenderTimeout("replicate polling timed out")

            async def poll() -> httpx.Response:
                response = await client.get(poll_url, headers=headers)
                response.raise_for_status()
                return response

            poll_resp = await request_with_retry_async(poll, timeout=timeout)
            payload = poll_resp.json()
            status = payload.get("status")
            if status == "succeeded":
                outputs = payload.get("output") or []
                audio_url = outputs[-1] if isinstance(outputs, list) and outputs else None
                if not audio_url or not isinstance(audio_url, str):
                    raise RenderError("replicate response missing audio url", details={"payload": payload})
                audio_bytes, suffix = await _download_audio_async(audio_url, timeout)
                out_path = out_dir / _derive_audio_name(midi_path.name, suffix)
                await asyncio.to_thread(out_path.write_bytes, audio_bytes)
                progress(95)
                return out_path, float(RENDER_MAX_SECONDS)
            if status == "failed":
                raise RenderError("replicate prediction failed", details={"payload": payload})
            await asyncio.sleep(poll_delay)
            current_progress = min(90, current_progress + 5)
            progress(current_progress)


async def render_via_provider_async(
    midi_path: Path,
    style: str,
    intensity: float,
    *,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Tuple[Path, float]:
    """中文注释：统一的 Provider 分发入口，并在关键节点回写进度。"""

    progress = progress_callback or (lambda _p: None)
    progress(10)
    provider = AUDIO_PROVIDER.lower()
    if provider == "placeholder":
        return await _render_placeholder_async(midi_path, style, intensity, progress)
    if provider == "hf":
        if not HF_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "hf"})
        return await _render_hf_async(midi_path, style, intensity, RENDER_TIMEOUT_SEC, progress)
    if provider == "replicate":
        if not REPLICATE_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "replicate"})
        return await _render_replicate_async(midi_path, style, intensity, RENDER_TIMEOUT_SEC, progress)
    raise ConfigError("unknown audio provider", details={"provider": AUDIO_PROVIDER})


def _normalize_bool(value: Any) -> bool:
    """中文注释：兼容各种布尔表示（数字、字符串）统一转换为 bool。"""

    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


async def _prepare_midi_file(
    midi_file: Optional[UploadFile],
    midi_path: Optional[str],
) -> Path:
    """中文注释：处理上传或已有 MIDI 路径并返回标准化后的文件路径。"""

    out_dir = _safe_outputs_dir()
    chosen_midi_path: Optional[Path] = None

    if midi_file is not None:
        original_name = midi_file.filename or "input.mid"
        suffix = Path(original_name).suffix or ".mid"
        temp_name = f"upload_{int(time.time())}{suffix}"
        tmp_midi = out_dir / temp_name
        content = await midi_file.read()
        if not content:
            raise ValidationError(
                "uploaded midi file is empty",
                details={"reason": "midi_file is empty"},
            )
        await asyncio.to_thread(tmp_midi.write_bytes, content)
        chosen_midi_path = tmp_midi

    if midi_path and not chosen_midi_path:
        resolved = _resolve_under(out_dir, Path(midi_path))
        if not resolved.exists():
            raise ValidationError("midi_path not found", details={"path": midi_path})
        if not resolved.is_file():
            raise ValidationError("midi_path must be a file", details={"path": midi_path})
        chosen_midi_path = resolved

    if not chosen_midi_path:
        raise ValidationError("either midi_file or midi_path is required")
    return chosen_midi_path


@router.post("/")
async def render_audio(
    request: Request,
    midi_file: Optional[UploadFile] = File(default=None),
    midi_path: Optional[str] = Form(default=None),
    style: Optional[str] = Form(default="cinematic"),
    intensity: Optional[float] = Form(default=0.5),
    sync_form: Optional[str] = Form(default=None),
    _: None = Depends(rate_limiter),
    token: str = Depends(require_token),
):
    """中文注释：创建渲染任务，默认异步排队；开发环境可通过 sync 参数调试同步模式。"""

    try:
        provider = AUDIO_PROVIDER.lower()
        if provider == "hf" and not HF_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "hf"})
        if provider == "replicate" and not REPLICATE_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "replicate"})

        sync_requested = _normalize_bool(request.query_params.get("sync"))
        if not sync_requested and sync_form is not None:
            sync_requested = _normalize_bool(sync_form)

        json_payload: Dict[str, Any] = {}
        if request.headers.get("content-type", "").startswith("application/json"):
            json_payload = await request.json()
            if "sync" in json_payload:
                sync_requested = _normalize_bool(json_payload.get("sync"))
            midi_path = midi_path or json_payload.get("midi_path")
            style = style or json_payload.get("style", "cinematic")
            intensity = intensity if intensity is not None else json_payload.get("intensity", 0.5)

        chosen_midi_path = await _prepare_midi_file(midi_file, midi_path)
        client_ip = request.client.host if request.client else "anonymous"
        # 中文注释：subject 表示配额统计主体，正常情况下等于 Token；开发环境允许退化为 "ANON"。
        subject = token if token else "ANON"
        storage = _get_quota_storage()
        # 中文注释：Pro Token 属于内部或付费用户，跳过每日免费额度但仍受速率限制保护。 
        is_pro_user = token != "ANON" and is_pro_token(token)
        today = today_str()
        if is_pro_user:
            await asyncio.to_thread(storage.incr_and_check, today, subject, 0)
        else:
            allowed, used = await asyncio.to_thread(
                storage.incr_and_check,
                today,
                subject,
                DAILY_FREE_QUOTA,
            )
            if not allowed:
                # 中文注释：匿名请求仅允许在开发模式使用，生产环境应强制传入合法 Token。
                return JSONResponse(
                    {
                        "ok": False,
                        "error": {
                            "code": "E_RATE_LIMIT",
                            "message": "daily free quota exceeded",
                            "details": {"subject": subject, "used": used, "limit": DAILY_FREE_QUOTA},
                        },
                    },
                    status_code=429,
                )
        tier = "pro" if is_pro_user else "free"
        identity = subject if subject != "ANON" else client_ip
        params = {
            "midi_path": str(chosen_midi_path),
            "style": style or "cinematic",
            "intensity": float(intensity or 0.5),
            "identity": identity,
            "tier": tier,
        }

        async def job(task_id: str) -> Dict[str, Any]:
            progress_cb = lambda p: task_manager.update_progress(task_id, p)
            progress_cb(5)
            try:
                out_audio, duration = await render_via_provider_async(
                    chosen_midi_path,
                    style=params["style"],
                    intensity=params["intensity"],
                    progress_callback=progress_cb,
                )
            except RenderTimeout:
                raise
            except (RenderError, ConfigError):
                raise
            except MMError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("render provider failure")
                raise RenderError(
                    "render provider failed",
                    details={"provider": AUDIO_PROVIDER, "reason": str(exc)},
                ) from exc

            audio_url = f"/outputs/{out_audio.name}"
            result = {
                "audio_url": audio_url,
                "duration_sec": duration,
                "renderer": AUDIO_PROVIDER,
                "style": params["style"],
                "intensity": params["intensity"],
            }
            progress_cb(100)
            return result

        task_id = task_manager.create_task(job, params=params)
        logger.info(
            "render task created task_id=%s midi=%s style=%s intensity=%s", task_id, params["midi_path"], params["style"], params["intensity"]
        )

        sync_allowed = APP_ENV in {"dev", "development", "local"}
        if sync_requested and not sync_allowed:
            # 中文注释：生产环境禁用同步模式，避免误用导致请求超时。
            logger.info("sync mode requested but disabled in environment env=%s", APP_ENV)
            sync_requested = False

        if sync_requested:
            snapshot = await task_manager.wait(task_id)
            if snapshot and snapshot.status == "done" and isinstance(snapshot.result, dict):
                return JSONResponse({"ok": True, "result": snapshot.result})
            if snapshot and snapshot.status == "failed" and snapshot.error:
                err_payload = snapshot.error
                status = 500
                if isinstance(err_payload, dict) and "code" in err_payload:
                    status_map = {
                        "E_VALIDATION": 400,
                        "E_RATE_LIMIT": 429,
                        "E_CONFIG": 400,
                        "E_RENDER_TIMEOUT": 504,
                        "E_RENDER": 500,
                    }
                    status = int(err_payload.get("http_status") or status_map.get(err_payload.get("code"), 500))
                return JSONResponse({"ok": False, "error": err_payload}, status_code=status)
            return JSONResponse(
                {"ok": True, "result": {"task_id": task_id}},
                status_code=202,
            )

        return JSONResponse(
            {"ok": True, "result": {"task_id": task_id}},
            status_code=202,
        )

    except MMError as err:
        logger.error("render error: %s", err)
        return JSONResponse(error_response(err), status_code=err.http_status)
    except Exception as exc:  # noqa: BLE001
        logger.exception("render internal error")
        err = RenderError("internal rendering error")
        return JSONResponse(error_response(err), status_code=500)


@tasks_router.get("/{task_id}")
async def get_task(task_id: str) -> JSONResponse:
    """中文注释：查询指定任务的执行状态与进度。"""

    snapshot = task_manager.get(task_id)
    if not snapshot:
        err = ValidationError("task not found", details={"task_id": task_id})
        return JSONResponse(error_response(err), status_code=err.http_status)
    payload = _snapshot_to_payload(snapshot)
    return JSONResponse({"ok": True, "result": payload})


@tasks_router.delete("/{task_id}")
async def cancel_task(task_id: str) -> JSONResponse:
    """中文注释：尽力取消指定任务，若任务已完成则直接返回最新状态。"""

    snapshot = task_manager.get(task_id)
    if not snapshot:
        err = ValidationError("task not found", details={"task_id": task_id})
        return JSONResponse(error_response(err), status_code=err.http_status)
    cancelled = task_manager.cancel(task_id)
    if not cancelled and snapshot.status not in {"done", "failed", "cancelled"}:
        err = RenderError("task could not be cancelled", details={"status": snapshot.status})
        return JSONResponse(error_response(err), status_code=409)
    updated = task_manager.get(task_id)
    payload = _snapshot_to_payload(updated or snapshot)
    return JSONResponse({"ok": True, "result": payload})


def _snapshot_to_payload(snapshot: TaskSnapshot) -> Dict[str, Any]:
    """中文注释：将任务快照转换为可序列化的 JSON 字典结构。"""

    return {
        "id": snapshot.id,
        "status": snapshot.status,
        "progress": snapshot.progress,
        "result": snapshot.result,
        "error": snapshot.error,
        "created_at": snapshot.created_at.isoformat(),
        "updated_at": snapshot.updated_at.isoformat(),
        "params": snapshot.params,
    }


__all__ = [
    "router",
    "tasks_router",
    "set_quota_storage",
    "render_via_provider_async",
    "request_with_retry_async",
]
