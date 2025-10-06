"""日志初始化模块：统一 FastAPI/uvicorn 的日志格式与等级。

通过集中配置可以在单元测试、CLI 与 API 服务之间复用相同的日志风格。
生产环境可进一步扩展为 JSON 结构化输出并接入集中日志系统。"""

from __future__ import annotations

import logging
from typing import Final

from .config import settings

_LOG_FORMAT: Final[str] = "[%(asctime)s] %(levelname)s %(name)s - %(message)s"


def setup_logging() -> None:
    """配置根日志记录器，避免重复添加处理器。"""

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)

    # 同时调整 uvicorn.access，保证访问日志与应用日志风格一致。
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    access_logger.addHandler(handler)
    access_logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """根据模块名称获取日志记录器，确保统一配置已经生效。"""

    setup_logging()
    return logging.getLogger(name)


__all__ = ["setup_logging", "get_logger"]
