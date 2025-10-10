"""鉴权与每日配额相关的集成测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from requests import Response

from motifmaker import api, audio_render, config
from motifmaker.quota import BaseQuotaStorage, create_quota_storage, today_str


def _configure_app(
    monkeypatch: pytest.MonkeyPatch,
    *,
    auth_required: bool,
    api_keys: set[str] | None = None,
    pro_tokens: set[str] | None = None,
    quota_backend: str = "memory",
    daily_quota: int = 3,
    usage_db_path: str | None = None,
) -> tuple[TestClient, BaseQuotaStorage]:
    """根据测试需要动态注入鉴权与配额配置。"""

    monkeypatch.setattr(config, "AUTH_REQUIRED", auth_required, raising=False)
    monkeypatch.setattr(config.settings, "auth_required", auth_required, raising=False)
    tokens = api_keys or set()
    monkeypatch.setattr(config, "API_TOKENS", tokens, raising=False)
    monkeypatch.setattr(config.settings, "api_keys", list(tokens), raising=False)
    pro = pro_tokens or set()
    monkeypatch.setattr(config, "PRO_USER_TOKENS", pro, raising=False)
    monkeypatch.setattr(config.settings, "pro_user_tokens", list(pro), raising=False)
    monkeypatch.setattr(config, "DAILY_FREE_QUOTA", daily_quota, raising=False)
    monkeypatch.setattr(config.settings, "daily_free_quota", daily_quota, raising=False)
    monkeypatch.setattr(audio_render, "DAILY_FREE_QUOTA", daily_quota, raising=False)
    monkeypatch.setattr(config, "QUOTA_BACKEND", quota_backend, raising=False)
    monkeypatch.setattr(config.settings, "quota_backend", quota_backend, raising=False)
    if usage_db_path is not None:
        monkeypatch.setattr(config, "USAGE_DB_PATH", usage_db_path, raising=False)
        monkeypatch.setattr(config.settings, "usage_db_path", usage_db_path, raising=False)
    storage = create_quota_storage(quota_backend, usage_db_path or config.USAGE_DB_PATH)
    monkeypatch.setattr(api, "quota", storage, raising=False)
    api.app.state.quota_storage = storage
    audio_render.set_quota_storage(storage)
    client = TestClient(api.app)
    return client, storage


def _render_once(client: TestClient, *, token: str | None = None) -> Response:
    """触发一次渲染请求，必要时附带 Authorization 头。"""

    headers = {"Authorization": f"Bearer {token}"} if token else None
    response = client.post(
        "/render/",
        files={"midi_file": ("demo.mid", b"MThd", "audio/midi")},
        data={"style": "cinematic", "intensity": "0.5"},
        headers=headers,
    )
    return response


def test_render_requires_token_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTH_REQUIRED=True 时未提供 Token 应返回 401。"""

    client, _ = _configure_app(monkeypatch, auth_required=True, api_keys={"tok_a"})
    resp = _render_once(client)
    assert resp.status_code == 401
    payload = resp.json()
    assert payload == {"ok": False, "error": {"code": "E_AUTH", "message": "unauthorized"}}


def test_anon_quota_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    """开发模式允许匿名访问，但以 "ANON" 作为主体计费。"""

    client, storage = _configure_app(
        monkeypatch,
        auth_required=False,
        quota_backend="memory",
        daily_quota=2,
    )
    first = _render_once(client)
    second = _render_once(client)
    third = _render_once(client)
    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    quota_day = today_str()
    assert storage.get(quota_day, "ANON") == 3
    assert third.json()["error"]["code"] == "E_RATE_LIMIT"


def test_valid_and_invalid_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    """合法 Token 可以通过，非法 Token 返回 401。"""

    client, _ = _configure_app(
        monkeypatch,
        auth_required=True,
        api_keys={"tok_a", "tok_b"},
        daily_quota=5,
    )
    ok = _render_once(client, token="tok_a")
    bad = _render_once(client, token="invalid")
    assert ok.status_code == 202
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "E_AUTH"


def test_pro_token_bypass_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pro Token 不应命中每日免费额度限制。"""

    client, storage = _configure_app(
        monkeypatch,
        auth_required=True,
        api_keys={"tok_pro"},
        pro_tokens={"tok_pro"},
        daily_quota=1,
    )
    for _ in range(3):
        resp = _render_once(client, token="tok_pro")
        assert resp.status_code == 202
    quota_day = today_str()
    # 中文注释：即便多次调用，底层计数仍记录，但不会触发 429。
    assert storage.get(quota_day, "tok_pro") == 3


def test_quota_backends_memory_and_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """不同配额后端需要正确累计调用次数，SQLite 需具备持久化能力。"""

    client_memory, storage_memory = _configure_app(
        monkeypatch,
        auth_required=False,
        quota_backend="memory",
        daily_quota=5,
    )
    _ = _render_once(client_memory)
    quota_day = today_str()
    assert storage_memory.get(quota_day, "ANON") == 1

    sqlite_path = str(tmp_path / "usage.db")
    client_sqlite, storage_sqlite = _configure_app(
        monkeypatch,
        auth_required=False,
        quota_backend="sqlite",
        usage_db_path=sqlite_path,
        daily_quota=5,
    )
    _ = _render_once(client_sqlite)
    assert storage_sqlite.get(quota_day, "ANON") == 1
    # 中文注释：重新创建存储实例，验证 SQLite 记录在进程重启后仍然存在。
    storage_after_restart = create_quota_storage("sqlite", sqlite_path)
    assert storage_after_restart.get(quota_day, "ANON") == 1
