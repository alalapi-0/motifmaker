"""音频渲染路由实现：支持多种 Provider 及失败重试。

中文注释：
- 默认 provider 为 placeholder（本地正弦波），便于离线开发；
- 当切换到 Hugging Face / Replicate 时需在 .env 中配置 Token，否则会返回
  E_CONFIG 错误提示；
- 外部请求内置指数退避重试与总超时保护，防止服务端线程长时间阻塞。
"""

from __future__ import annotations

import base64
import json
import time
import wave
from pathlib import Path
from typing import Callable, Optional, Tuple

import httpx
import numpy as np
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from .config import (
    AUDIO_PROVIDER,
    DAILY_FREE_QUOTA,
    HF_API_TOKEN,
    HF_MODEL,
    OUTPUT_DIR,
    PRO_USER_EMAILS,
    REPLICATE_API_TOKEN,
    REPLICATE_MODEL,
    RENDER_MAX_SECONDS,
    RENDER_TIMEOUT_SEC,
)
from .errors import (
    ConfigError,
    MMError,
    RateLimitError,
    RenderError,
    RenderTimeout,
    ValidationError,
    error_response,
)
from .logging_setup import get_logger
from .quota import incr_and_check, today_key
from .ratelimit import rate_limiter
from .utils import ensure_directory

# 中文注释：FastAPI 路由集中在此处，prefix 统一为 /render，方便前端调用。
router = APIRouter(prefix="/render", tags=["AudioRender"])
logger = get_logger(__name__)

# 中文注释：兼容旧的工具函数命名，避免重复实现。
ensure_dir = ensure_directory


def _safe_outputs_dir() -> Path:
    """中文注释：确保输出目录存在并返回其解析后的绝对路径。"""

    out = ensure_dir(OUTPUT_DIR)
    # 中文注释：``resolve`` 可以将相对路径转换为绝对路径，避免在后续拼接时重复出现
    # ``outputs/outputs`` 等错误目录结构，同时也让越界校验更简单。
    return Path(out).resolve()


def _resolve_under(base: Path, candidate: Path) -> Path:
    """中文注释：统一的安全路径解析工具，确保 ``candidate`` 位于 ``base`` 下。

    中文设计说明：
    - 传统的 ``startswith`` 判断仅比较字符串前缀，可能被 ``outputs_backup``
      等同名前缀目录绕过，因此必须放弃；
    - 先通过 ``resolve()`` 将基准目录与候选路径转换为绝对形式，可以自动消除
      ``..``、符号链接等带来的不确定性；
    - 随后使用 ``relative_to`` 进行严格的祖先关系判断，若抛出 ``ValueError``
      即代表越界访问，立即转为 ``ValidationError``；
    - 对于传入 ``outputs/foo.mid`` 这类已经携带根目录名的相对路径，会先剥离
      重复的首段，保证最终定位到 ``base`` 下的真实文件。
    """

    resolved_base = base.resolve()
    # 中文注释：处理传入路径时需要谨慎，既要兼容绝对路径也要兼容 ``outputs/foo.mid``。
    relative_candidate = candidate
    if candidate.is_absolute():
        combined = candidate.resolve()
        parts = combined.parts
        if len(parts) > 1 and parts[1] == resolved_base.name:
            # 中文注释：处理 ``/outputs/foo.mid``，将根目录名剥离后拼回 ``base``。
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
            # 中文注释：若首段已是 ``outputs``，剥离后再拼接，避免 ``outputs/outputs``。
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

    # 中文注释：默认返回值为 ``candidate`` 已经是绝对路径并通过了祖先校验。
    return candidate.resolve()


def _extension_from_content_type(content_type: str) -> str:
    """根据 Content-Type 推断文件扩展名，缺省为 ``.wav``。

    中文注释：外部模型返回的音频格式可能是 mp3/wav/flac，统一在此集中判断。
    """

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


def _download_audio(url: str, timeout: int) -> Tuple[bytes, str]:
    """下载远程音频 URL，返回数据与扩展名。"""

    # 中文注释：下载外部资源同样受统一的重试逻辑保护，避免瞬时网络抖动导致失败。
    with httpx.Client(timeout=timeout) as client:
        def send() -> httpx.Response:
            response = client.get(url)
            response.raise_for_status()
            return response

        response = request_with_retry(send, timeout=timeout)
        content_type = response.headers.get("content-type", "audio/wav")
        suffix = _extension_from_content_type(content_type)
        return response.content, suffix


def _compose_prompt(style: str, intensity: float) -> str:
    """根据风格与强度构造文本提示，供文本到音乐模型使用。"""

    clipped = max(0.0, min(intensity, 1.0))
    return f"{style} soundtrack, intensity={clipped:.2f}, 120bpm, 4/4"


def _sine_wav(
    path: Path,
    seconds: float = 6.0,
    samplerate: int = 44100,
    freq: float = 440.0,
) -> float:
    """
    生成一段正弦波 wav（占位渲染），返回时长（秒）。
    中文注释：在没有接入真实 AI 的情况下，用该方法快速得到可播放的音频文件。
    """

    t = np.linspace(0, seconds, int(samplerate * seconds), endpoint=False)
    # 中文注释：加入淡入淡出避免音频瞬态造成爆音，幅度控制在 0.2 以内降低音量。
    fade = np.linspace(0, 1, len(t))
    waveform = 0.2 * np.sin(2 * np.pi * freq * t) * fade
    waveform_int16 = (waveform * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 中文注释：16-bit 采样宽度即可满足占位需求。
        wf.setframerate(samplerate)
        wf.writeframes(waveform_int16.tobytes())
    return seconds


def _derive_audio_name(midi_name: str, suffix: str = ".wav") -> str:
    """中文注释：基于 midi 文件名 + 时间戳派生一个不冲突的音频名称。"""

    stem = Path(midi_name).stem or "track"
    ts = int(time.time())
    return f"{stem}_{ts}{suffix}"


def request_with_retry(
    send_func: Callable[[], httpx.Response],
    *,
    retries: int = 2,
    backoff: float = 1.5,
    timeout: int = RENDER_TIMEOUT_SEC,
) -> httpx.Response:
    """执行带指数退避的请求重试，并在总超时后抛出 ``RenderTimeout``。

    中文注释：
    - send_func 内部实际发起 HTTP 请求并返回 ``httpx.Response``；
    - 当响应状态码为 429 或 5xx 时重试，间隔按 backoff 指数增长；
    - 若累计耗时超过 timeout，则抛出 ``RenderTimeout``，提示客户端稍后重试。
    """

    attempts = 0
    delay = 1.0
    deadline = time.monotonic() + max(1, timeout)
    last_exc: Optional[Exception] = None

    while attempts <= retries:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RenderTimeout("render provider timed out")
        try:
            response = send_func()
            return response
        except RenderTimeout:
            raise
        except httpx.TimeoutException as exc:
            raise RenderTimeout("render provider timed out") from exc
        except httpx.HTTPStatusError as exc:  # 中文注释：仅对 429/5xx 启用重试，其余直接抛错。
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
            time.sleep(sleep_time)
        delay *= backoff

    if isinstance(last_exc, RenderError):
        raise last_exc
    if last_exc is not None:
        raise RenderError("provider request failed", details={"reason": str(last_exc)}) from last_exc
    raise RenderError("provider request failed")


def _render_placeholder(midi_path: Path, style: str, intensity: float) -> Tuple[Path, float]:
    """本地正弦波占位渲染，返回音频路径与时长。"""

    out_dir = _safe_outputs_dir()
    seconds = float(min(RENDER_MAX_SECONDS, 6))
    out_path = out_dir / _derive_audio_name(midi_path.name, ".wav")
    base_freq = 440.0
    freq = base_freq + max(0.0, min(intensity, 1.0)) * 100.0
    duration = _sine_wav(out_path, seconds=seconds, freq=freq)
    return out_path, duration


def _render_hf(midi_path: Path, style: str, intensity: float, timeout: int) -> Tuple[Path, float]:
    """调用 Hugging Face Inference Endpoint 生成音频。"""

    prompt = _compose_prompt(style, intensity)
    url = HF_MODEL if HF_MODEL.startswith("http") else f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Accept": "application/json",
    }
    out_dir = _safe_outputs_dir()

    with httpx.Client(timeout=timeout) as client:
        def send() -> httpx.Response:
            response = client.post(url, headers=headers, json={"inputs": prompt})
            if response.status_code == 202:
                # 中文注释：202 表示模型加载中，主动抛出以触发重试。
                raise httpx.HTTPStatusError("model loading", request=response.request, response=response)
            response.raise_for_status()
            return response

        response = request_with_retry(send, timeout=timeout)

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

        # 中文注释：不同模型回参不统一，按常见字段尝试解析。
        if isinstance(payload, dict):
            candidate = payload.get("audio") or payload.get("generated_audio") or payload.get("output")
            if isinstance(candidate, list) and candidate:
                candidate = candidate[0]
            if isinstance(candidate, str):
                if candidate.startswith("http"):
                    audio_bytes, suffix = _download_audio(candidate, timeout)
                else:
                    audio_bytes, suffix = _decode_base64_audio(candidate)
        if audio_bytes is None:
            raise RenderError("hugging face response missing audio", details={"payload": payload})

    out_path = out_dir / _derive_audio_name(midi_path.name, suffix)
    out_path.write_bytes(audio_bytes)
    return out_path, float(RENDER_MAX_SECONDS)


def _render_replicate(
    midi_path: Path,
    style: str,
    intensity: float,
    timeout: int,
) -> Tuple[Path, float]:
    """调用 Replicate Prediction API 渲染音频并保存到本地。"""

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

    with httpx.Client(timeout=timeout) as client:
        def create_prediction() -> httpx.Response:
            response = client.post("https://api.replicate.com/v1/predictions", headers=headers, json=payload)
            response.raise_for_status()
            return response

        creation = request_with_retry(create_prediction, timeout=timeout)
        data = creation.json()
        prediction_id = data.get("id")
        if not prediction_id:
            raise RenderError("replicate response missing id", details={"response": data})

        status = data.get("status")
        if status == "failed":
            raise RenderError("replicate prediction failed", details={"response": data})

        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        poll_delay = 2.0

        while True:
            if time.monotonic() - start > timeout:
                raise RenderTimeout("replicate polling timed out")

            def poll() -> httpx.Response:
                response = client.get(poll_url, headers=headers)
                response.raise_for_status()
                return response

            poll_resp = request_with_retry(poll, timeout=timeout)
            payload = poll_resp.json()
            status = payload.get("status")
            if status == "succeeded":
                outputs = payload.get("output") or []
                audio_url = outputs[-1] if isinstance(outputs, list) and outputs else None
                if not audio_url or not isinstance(audio_url, str):
                    raise RenderError("replicate response missing audio url", details={"payload": payload})
                audio_bytes, suffix = _download_audio(audio_url, timeout)
                out_path = out_dir / _derive_audio_name(midi_path.name, suffix)
                out_path.write_bytes(audio_bytes)
                return out_path, float(RENDER_MAX_SECONDS)
            if status == "failed":
                raise RenderError("replicate prediction failed", details={"payload": payload})
            time.sleep(poll_delay)


def render_via_provider(midi_path: Path, style: str, intensity: float) -> Tuple[Path, float]:
    """
    中文注释：真实渲染入口，根据 AUDIO_PROVIDER 分发到具体实现。
    - placeholder：调用本地正弦波占位；
    - hf：调用 Hugging Face Inference API；
    - replicate：调用 Replicate Prediction API。
    """

    provider = AUDIO_PROVIDER.lower()
    if provider == "placeholder":
        return _render_placeholder(midi_path, style, intensity)
    if provider == "hf":
        if not HF_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "hf"})
        return _render_hf(midi_path, style, intensity, RENDER_TIMEOUT_SEC)
    if provider == "replicate":
        if not REPLICATE_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "replicate"})
        return _render_replicate(midi_path, style, intensity, RENDER_TIMEOUT_SEC)
    raise ConfigError("unknown audio provider", details={"provider": AUDIO_PROVIDER})


@router.post("/")
async def render_audio(
    request: Request,
    midi_file: Optional[UploadFile] = File(default=None),
    midi_path: Optional[str] = Form(default=None),
    style: str = Form(default="cinematic"),
    intensity: float = Form(default=0.5),
    _: None = Depends(rate_limiter),
):
    """
    中文说明：
    - 支持二选一输入：上传的 midi_file 或已有的 midi_path（outputs 内）；
    - 使用占位或远程服务生成音频，并返回可访问的 audio_url；
    - 引入每日免费额度与 Pro 白名单，防止无限制调用导致成本失控。
    """

    try:
        out_dir = _safe_outputs_dir()
        # 中文注释：所有后续路径操作都基于 ``out_dir`` 的绝对路径，避免因相对路径导致的误判。
        chosen_midi_path: Optional[Path] = None

        provider = AUDIO_PROVIDER.lower()
        if provider == "hf" and not HF_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "hf"})
        if provider == "replicate" and not REPLICATE_API_TOKEN:
            raise ConfigError("provider token missing", details={"provider": "replicate"})

        if midi_file is not None:
            # 中文注释：将上传的 MIDI 存到 outputs，文件名加时间戳避免覆盖。
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
            tmp_midi.write_bytes(content)
            chosen_midi_path = tmp_midi

        if midi_path and not chosen_midi_path:
            # 中文注释：统一通过 ``_resolve_under`` 校验，兼容相对/绝对路径并严格防止越界。
            resolved = _resolve_under(out_dir, Path(midi_path))
            if not resolved.exists():
                raise ValidationError("midi_path not found", details={"path": midi_path})
            if not resolved.is_file():
                raise ValidationError("midi_path must be a file", details={"path": midi_path})
            chosen_midi_path = resolved

        if not chosen_midi_path:
            raise ValidationError("either midi_file or midi_path is required")

        # 中文注释：按请求头优先使用 email 作为配额键，其次回退到客户端 IP。
        client_ip = request.client.host if request.client else "anonymous"
        raw_email = request.headers.get("X-User-Email")
        email = raw_email.lower() if raw_email else None
        is_pro = bool(email and email in PRO_USER_EMAILS)
        if not is_pro:
            day, quota_key = today_key(email or client_ip)
            allowed = incr_and_check(day, quota_key, DAILY_FREE_QUOTA)
            if not allowed:
                raise RateLimitError(
                    "daily free quota exceeded",
                    details={"quota": DAILY_FREE_QUOTA, "key": quota_key},
                )

        try:
            out_audio, duration = render_via_provider(
                chosen_midi_path,
                style=style,
                intensity=float(intensity),
            )
        except RenderTimeout:
            raise
        except (RenderError, ConfigError, RateLimitError):
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

        return JSONResponse(
            {
                "ok": True,
                "result": {
                    "audio_url": audio_url,
                    "duration_sec": duration,
                    "renderer": AUDIO_PROVIDER,
                    "style": style,
                    "intensity": float(intensity),
                },
            }
        )

    except MMError as err:
        # 中文注释：统一记录业务异常，方便观察错误码与上下文。
        logger.error("render error: %s", err)
        return JSONResponse(error_response(err), status_code=err.http_status)
    except Exception as exc:  # noqa: BLE001
        # 中文注释：兜底异常，防止堆栈泄露给客户端，同时记录日志排查。
        logger.exception("render internal error")
        err = RenderError("internal rendering error")
        return JSONResponse(error_response(err), status_code=500)


__all__ = ["router", "render_via_provider", "request_with_retry"]
