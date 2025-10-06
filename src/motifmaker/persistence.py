"""工程持久化模块，负责安全地读写 ProjectSpec JSON 文件。

为防止目录穿越与非法文件名，该模块对工程名称执行正则白名单校验，
并将所有文件写入配置指定的 ``PROJECTS_DIR`` 目录。读写异常会转换为
统一的 :class:`~motifmaker.errors.PersistenceError`，确保 API 返回稳定的错误码。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .config import settings
from .errors import PersistenceError, ValidationError
from .schema import ProjectSpec
from .utils import ensure_directory

# 允许的工程名称字符集，兼顾可读性与安全性。
_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def _project_path(name: str) -> Path:
    """根据用户提供的名称生成合法且安全的工程文件路径。"""

    if not _NAME_PATTERN.fullmatch(name):
        raise ValidationError("工程名称只能包含字母、数字、下划线或短横线")
    base_dir = ensure_directory(settings.projects_dir)
    path = (base_dir / f"{name}.json").resolve()
    # 再次确认文件位于目标目录下，避免通过符号链接绕过限制。
    if not str(path).startswith(str(Path(base_dir).resolve())):
        raise ValidationError("禁止访问工程目录之外的路径")
    return path


def save_project_json(spec: ProjectSpec, name: str) -> Path:
    """将项目规格保存为 JSON 文件，并返回写入的路径。"""

    path = _project_path(name)
    data = spec.model_dump(mode="json")
    try:
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        raise PersistenceError("写入工程文件失败", details={"path": str(path)}) from exc
    return path


def load_project_json(name: str) -> ProjectSpec:
    """从磁盘读取工程 JSON 并转换为 :class:`ProjectSpec`。"""

    path = _project_path(name)
    if not path.exists():
        raise FileNotFoundError(f"项目文件不存在: {path}")
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PersistenceError("读取工程文件失败", details={"path": str(path)}) from exc
    try:
        return ProjectSpec.model_validate_json(payload)
    except Exception as exc:  # pragma: no cover - 具体错误由模型抛出
        raise PersistenceError("工程文件格式错误", details={"path": str(path)}) from exc


__all__ = ["save_project_json", "load_project_json"]
