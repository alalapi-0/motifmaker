"""配置模块：集中管理后端行为的可调参数。

由于运行环境不一定预装 ``pydantic-settings``，此处使用轻量的
``os.getenv`` + ``.env`` 解析方案实现同样的配置化效果。通过集中配置
可以在不修改代码的情况下调整 API 标题、版本、跨域白名单、输出目录、
工程目录、限流速率与日志等级。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _load_env_file() -> None:
    """读取根目录下的 .env 文件并合并到环境变量。"""

    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _split_list(value: str) -> List[str]:
    """将逗号分隔的字符串拆分为列表。"""

    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass
class Settings:
    """后端运行所需的所有环境配置，支持 .env 与环境变量覆盖。"""

    api_title: str = field(default="MotifMaker API")
    api_version: str = field(default="0.2.0")
    allowed_origins: List[str] = field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    output_dir: str = field(default="outputs")
    projects_dir: str = field(default="projects")
    rate_limit_rps: int = field(default=2)
    log_level: str = field(default="INFO")

    @classmethod
    def from_env(cls) -> "Settings":
        """根据环境变量构造配置实例。"""

        _load_env_file()
        allowed = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:3000",
        )
        return cls(
            api_title=os.getenv("API_TITLE", "MotifMaker API"),
            api_version=os.getenv("API_VERSION", "0.2.0"),
            allowed_origins=_split_list(allowed),
            output_dir=os.getenv("OUTPUT_DIR", "outputs"),
            projects_dir=os.getenv("PROJECTS_DIR", "projects"),
            rate_limit_rps=int(os.getenv("RATE_LIMIT_RPS", "2")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.from_env()
"""全局唯一的配置实例，供其它模块引用。"""

# 中文注释：输出目录常量供路由等模块引用，保持配置来源单一。
OUTPUT_DIR = settings.output_dir

