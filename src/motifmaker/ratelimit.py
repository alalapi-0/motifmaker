"""轻量限流实现：为开发环境提供基础的请求速率控制。"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from fastapi import Request

from .auth import extract_token
from .config import settings
from .errors import RateLimitError

# 该实现使用内存中基于 deque 的滑动窗口计数，适合单进程部署场景。
# 在生产环境推荐接入 Redis/限流代理（如 NGINX 或 Envoy）以获取分布式能力。
_WINDOW_SECONDS = 1.0

# 存储每个限流键（IP+路径）的访问时间戳序列。
_RATE_BUCKETS: Dict[str, Deque[float]] = defaultdict(deque)
_LOCK = Lock()


def rate_limiter(request: Request) -> None:
    """FastAPI 依赖：按客户端 IP + 路径维度限制每秒请求次数。"""

    client_ip = request.client.host if request.client else "anonymous"
    token = extract_token(request)
    # 中文注释：优先按 Token 限流，只有匿名开发流量才退化到按 IP 统计，减少共享出口的误杀。
    rate_key = f"token:{token}" if token else f"ip:{client_ip}"
    key = f"{rate_key}:{request.url.path}"
    now = time.monotonic()
    with _LOCK:
        bucket = _RATE_BUCKETS[key]
        # 移除窗口之外的时间戳，保持队列长度不会无限增长。
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        # 如果当前计数已达到上限，则抛出限流异常。
        if len(bucket) >= max(1, settings.rate_limit_rps):
            raise RateLimitError(details={"retry_after": 1})
        bucket.append(now)


__all__ = ["rate_limiter"]
