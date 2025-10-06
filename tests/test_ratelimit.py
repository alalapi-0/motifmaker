"""验证轻量限流依赖在高频请求时返回 429。"""

import time

from fastapi.testclient import TestClient

from motifmaker.api import app
from motifmaker.config import settings
from motifmaker import ratelimit

client = TestClient(app)


def test_rate_limit_trigger(monkeypatch) -> None:
    """在极低限额下连续请求应触发 E_RATE_LIMIT。"""

    monkeypatch.setattr(settings, "rate_limit_rps", 1, raising=False)
    ratelimit._RATE_BUCKETS.clear()
    assert settings.rate_limit_rps == 1
    payload = {"prompt": "限流测试"}
    first = client.post("/generate", json=payload)
    assert first.status_code == 200
    second = client.post("/generate", json=payload)
    assert second.status_code == 429
    body = second.json()
    assert body["error"]["code"] == "E_RATE_LIMIT"
    time.sleep(1.1)
    ratelimit._RATE_BUCKETS.clear()
