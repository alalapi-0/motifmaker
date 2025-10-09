"""配置模块：集中管理后端行为的可调参数。

由于运行环境不一定预装 ``pydantic-settings``，此处使用轻量的
``os.getenv`` + ``.env`` 解析方案实现同样的配置化效果。通过集中配置
可以在不修改代码的情况下调整 API 标题、版本、跨域白名单、输出目录、
工程目录、限流速率与日志等级。

本次扩展额外引入音频渲染提供商配置、第三方访问凭据、渲染超时/时长
限制与每日配额阈值，所有新字段均通过中文注释说明默认值及安全边界，
便于在开发/部署阶段快速校验环境变量填写是否正确。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set


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
    audio_provider: str = field(default="placeholder")
    hf_api_token: str = field(default="")
    hf_model: str = field(default="facebook/musicgen-small")
    replicate_api_token: str = field(default="")
    replicate_model: str = field(default="meta/musicgen:latest")
    environment: str = field(default="production")
    render_timeout_sec: int = field(default=120)
    render_max_seconds: int = field(default=30)
    render_max_concurrency: int = field(default=2)
    daily_free_quota: int = field(default=10)
    pro_user_emails: List[str] = field(default_factory=list)
    usage_db_path: str = field(default="var/usage.db")

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
            audio_provider=os.getenv("AUDIO_PROVIDER", "placeholder"),
            hf_api_token=os.getenv("HF_API_TOKEN", ""),
            hf_model=os.getenv("HF_MODEL", "facebook/musicgen-small"),
            replicate_api_token=os.getenv("REPLICATE_API_TOKEN", ""),
            replicate_model=os.getenv("REPLICATE_MODEL", "meta/musicgen:latest"),
            environment=os.getenv("ENV", "production"),
            render_timeout_sec=int(os.getenv("RENDER_TIMEOUT_SEC", "120")),
            render_max_seconds=int(os.getenv("RENDER_MAX_SECONDS", "30")),
            render_max_concurrency=int(os.getenv("RENDER_MAX_CONCURRENCY", "2")),
            daily_free_quota=int(os.getenv("DAILY_FREE_QUOTA", "10")),
            pro_user_emails=_split_list(os.getenv("PRO_USER_EMAILS", "")),
            usage_db_path=os.getenv("USAGE_DB_PATH", "var/usage.db"),
        )


settings = Settings.from_env()
"""全局唯一的配置实例，供其它模块引用。"""

# 中文注释：输出目录常量供路由等模块引用，保持配置来源单一。
OUTPUT_DIR = settings.output_dir
# 中文注释：工程目录同样暴露常量，便于测试及 API 校验统一引用。
PROJECTS_DIR = settings.projects_dir

# 中文注释：将常用配置以常量暴露，方便渲染与限流模块直接引用，避免层层传参。
AUDIO_PROVIDER: str = settings.audio_provider.lower()
HF_API_TOKEN: str = settings.hf_api_token
HF_MODEL: str = settings.hf_model
REPLICATE_API_TOKEN: str = settings.replicate_api_token
REPLICATE_MODEL: str = settings.replicate_model
RENDER_TIMEOUT_SEC: int = max(1, settings.render_timeout_sec)
RENDER_MAX_SECONDS: int = max(1, settings.render_max_seconds)
RENDER_MAX_CONCURRENCY: int = max(1, settings.render_max_concurrency)
DAILY_FREE_QUOTA: int = settings.daily_free_quota
PRO_USER_EMAILS: Set[str] = {email.lower() for email in settings.pro_user_emails}
USAGE_DB_PATH: str = settings.usage_db_path

# 中文注释：环境标识用于控制调试行为（例如同步渲染仅在开发环境启用）。
APP_ENV: str = settings.environment.lower()

# 中文注释：为了避免配额数据库意外提交，确保运行目录在仓库忽略列表内。
Path(USAGE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

