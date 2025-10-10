"""API Token 鉴权依赖，统一解析客户端传入的 Authorization 头。

中文注释：
- 旧版依赖 ``X-User-Email`` 由前端自行声明，极易被伪造，本轮改用由服务端配置的
  Token 列表，从源头避免冒用他人身份绕过免费配额；
- Token 与白名单均保存在后端环境变量中，禁止写死在前端仓库，避免泄露后被滥用。"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Request, status

from . import config


def _parse_authorization(header_value: Optional[str]) -> Optional[str]:
    """解析 Authorization 头，兼容 Bearer 与裸 token 形式。"""

    if not header_value:
        return None
    stripped = header_value.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    if lowered.startswith("bearer "):
        return stripped[7:].strip()
    return stripped


def extract_token(request: Request) -> Optional[str]:
    """仅解析请求头中的 token，供日志或限流使用。"""

    header_value = request.headers.get(config.AUTH_HEADER)
    return _parse_authorization(header_value)


def is_pro_token(token: str) -> bool:
    """判断 token 是否属于 Pro 白名单。"""

    return token in config.PRO_USER_TOKENS


def require_token(request: Request) -> str:
    """FastAPI 依赖：校验来访请求的 API Token。"""

    token = extract_token(request)
    if token and token in config.API_TOKENS:
        return token
    if token and token not in config.API_TOKENS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_AUTH", "message": "unauthorized"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if config.AUTH_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "E_AUTH", "message": "unauthorized"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 中文注释：开发模式允许返回 "ANON"，仅供本地联调使用，生产环境必须开启 AUTH_REQUIRED。
    return "ANON"


__all__ = ["require_token", "is_pro_token", "extract_token"]
