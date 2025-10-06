import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from motifmaker.config import settings
from motifmaker import ratelimit


@pytest.fixture(autouse=True)
def _isolate_io_directories(tmp_path, monkeypatch):
    """将输出与工程目录指向临时路径，避免污染仓库。"""

    out_dir = tmp_path / "outputs"
    project_dir = tmp_path / "projects"
    monkeypatch.setattr(settings, "output_dir", str(out_dir), raising=False)
    monkeypatch.setattr(settings, "projects_dir", str(project_dir), raising=False)
    monkeypatch.setattr(settings, "rate_limit_rps", 100, raising=False)
    ratelimit._RATE_BUCKETS.clear()
    yield
