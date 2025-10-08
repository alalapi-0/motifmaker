"""错误码与异常定义模块，确保 API 对外行为稳定可预期。

统一的错误类便于在 FastAPI 与 CLI 中共享处理逻辑，错误码采用
``E_`` 前缀加大写下划线格式，保证在后续版本演进时保持对外契约稳定。
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MMError(Exception):
    """MotifMaker 自定义异常基类，包含错误码与 HTTP 状态码。"""

    code: str = "E_INTERNAL"
    http_status: int = 500
    default_message: str = "内部服务错误"

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
        http_status: Optional[int] = None,
    ) -> None:
        """初始化异常并保存详情，方便日志与响应使用。"""

        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.details = details or {}
        if http_status is not None:
            self.http_status = http_status

    def to_dict(self) -> Dict[str, Any]:
        """转换为标准 JSON 结构，便于直接序列化。"""

        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(MMError):
    """请求参数校验失败时抛出的异常，返回 HTTP 400。"""

    code = "E_VALIDATION"
    http_status = 400
    default_message = "请求参数校验失败"


class RateLimitError(MMError):
    """触发轻量限流时返回 429 Too Many Requests。"""

    code = "E_RATE_LIMIT"
    http_status = 429
    default_message = "请求过于频繁，请稍后重试"


class ConfigError(MMError):
    """配置缺失或不合法时抛出的异常，通常用于第三方凭据校验。"""

    code = "E_CONFIG"
    http_status = 400
    default_message = "configuration error"


class PersistenceError(MMError):
    """项目持久化过程出现读写问题时抛出，默认 500。"""

    code = "E_PERSIST"
    http_status = 500
    default_message = "工程持久化失败"


class RenderError(MMError):
    """渲染过程失败时抛出，通常意味着 MIDI 或分轨生成出错。"""

    code = "E_RENDER"
    http_status = 500
    default_message = "渲染失败"


class RenderTimeout(MMError):
    """外部渲染超时时抛出的异常，HTTP 状态码使用 504。"""

    code = "E_RENDER_TIMEOUT"
    http_status = 504
    default_message = "render request timed out"


class InternalServerError(MMError):
    """兜底异常类型，对未知错误统一返回 500。"""

    code = "E_INTERNAL"
    http_status = 500
    default_message = "内部服务错误"


def error_response(exc: MMError) -> Dict[str, Any]:
    """根据异常构造统一错误响应 JSON。"""

    return {
        "ok": False,
        "error": exc.to_dict(),
    }


__all__ = [
    "MMError",
    "ValidationError",
    "RateLimitError",
    "ConfigError",
    "PersistenceError",
    "RenderError",
    "RenderTimeout",
    "InternalServerError",
    "error_response",
]
