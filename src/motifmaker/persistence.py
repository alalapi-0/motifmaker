"""项目规格持久化工具，负责保存与读取工程快照。

该模块提供简单的 JSON 序列化封装，便于 API 与 CLI 将 `ProjectSpec`
状态保存到 `projects/` 目录并在后续会话中恢复。所有函数都以路径与
异常处理加中文注释说明，方便后续接入数据库或云存储时扩展。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from .schema import ProjectSpec
from .utils import ensure_directory

# 项目文件统一存放于仓库根目录下的 projects/ 目录，便于开发者手动查看与管理。
_PROJECTS_DIR: Final[Path] = Path("projects")


def _project_path(name: str) -> Path:
    """根据用户提供的名称生成合法的工程文件路径。"""

    # 以最简单的方式替换路径分隔符，避免用户输入带有目录跳转符号导致安全隐患。
    safe_name = name.replace("/", "_").replace("\\", "_")
    return ensure_directory(_PROJECTS_DIR) / f"{safe_name}.json"


def save_project_json(spec: ProjectSpec, name: str) -> Path:
    """将项目规格保存为 JSON 文件。

    参数:
        spec: 需要持久化的 :class:`ProjectSpec` 对象。
        name: 用户自定义的工程名称，最终会转换为 ``projects/<name>.json``。

    返回:
        写入完成的 ``Path`` 对象，方便调用方在响应体中返回或进一步处理。

    设计意图:
        - 使用 UTF-8 与 ``ensure_ascii=False`` 保证中文参数不会被转义。
        - 通过 :meth:`ProjectSpec.model_dump` 保留所有字段，未来若新增字段仍兼容。
    """

    path = _project_path(name)
    data = spec.model_dump(mode="json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_project_json(name: str) -> ProjectSpec:
    """从 JSON 文件还原项目规格。

    参数:
        name: 之前保存工程时使用的名称。

    返回:
        解析后的 :class:`ProjectSpec` 对象，供渲染或 API 调用继续使用。

    异常:
        FileNotFoundError: 当对应的 JSON 文件不存在时抛出，由上层捕获并转换为
            友好的提示信息。
        ValueError: 当 JSON 数据格式错误或缺失字段时，Pydantic 校验将触发
            ``ValidationError``，此处将其转换为 ``ValueError`` 方便 CLI/API 统一处理。
    """

    path = _project_path(name)
    if not path.exists():
        raise FileNotFoundError(f"项目文件不存在: {path}")
    try:
        payload = path.read_text(encoding="utf-8")
        return ProjectSpec.model_validate_json(payload)
    except Exception as exc:  # pragma: no cover - 异常流程简单委托上层
        raise ValueError(f"无法解析项目文件 {path}: {exc}") from exc


__all__ = ["save_project_json", "load_project_json"]
