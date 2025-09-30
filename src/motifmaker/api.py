"""FastAPI 服务入口，提供 Prompt 解析与渲染 API。

模块同时启用 CORS 以便 Vite 前端通过 http://localhost:5173 或
http://localhost:3000 访问。所有关键步骤均附带中文注释，解释如何在服务端
执行生成、局部再生成、动机冻结以及工程持久化等操作。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .parsing import parse_natural_prompt
from .persistence import load_project_json, save_project_json
from .render import RenderResult, render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import ensure_directory

logger = logging.getLogger(__name__)

app = FastAPI(title="Motifmaker")

# 允许本地前端 (Vite/Shoelace) 直接调用 API，开发调试更顺畅。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerationOptions(BaseModel):
    """生成时的可选参数，镜像 CLI 与 Web UI 控件。"""

    motif_style: Optional[Literal["ascending_arc", "wavering", "zigzag"]] = None
    rhythm_density: Optional[Literal["low", "medium", "high"]] = None
    harmony_level: Optional[Literal["basic", "colorful"]] = None
    emit_midi: bool = False
    tracks: list[str] | None = None  # 分轨选择，允许前端自定义导出内容。


class GenerateRequest(BaseModel):
    """Prompt 生成请求体。"""

    prompt: str
    options: GenerationOptions | None = None


class RenderResponse(BaseModel):
    """渲染结果结构体，包含文件路径、规格与统计信息。"""

    output_dir: str
    spec: str
    summary: str
    midi: str | None
    project: ProjectSpec
    sections: dict[str, dict[str, object]]
    track_stats: list[dict[str, object]]


class RenderRequest(BaseModel):
    """显式渲染既有 ProjectSpec 的请求。"""

    project: ProjectSpec
    emit_midi: bool = False
    tracks: list[str] | None = None


class RegenerateSectionRequest(BaseModel):
    """局部再生请求体，支持是否保留动机与分轨控制。"""

    spec: ProjectSpec
    section_index: int
    keep_motif: bool = True
    emit_midi: bool = True
    tracks: list[str] | None = None


class FreezeMotifRequest(BaseModel):
    """冻结动机请求体，将指定标签标记为只读。"""

    spec: ProjectSpec
    motif_tags: list[str]


class FreezeMotifResponse(BaseModel):
    """返回更新后的 ProjectSpec，供前端继续编辑。"""

    project: ProjectSpec


class SaveProjectRequest(BaseModel):
    """保存工程的请求体，携带名称与规格。"""

    spec: ProjectSpec
    name: str


class SaveProjectResponse(BaseModel):
    """保存成功后返回的路径信息。"""

    path: str


class LoadProjectRequest(BaseModel):
    """载入工程的请求体，仅需名称。"""

    name: str


class LoadProjectResponse(BaseModel):
    """返回载入的 ProjectSpec 以及源路径。"""

    project: ProjectSpec
    path: str


def _apply_options(spec: ProjectSpec, options: GenerationOptions | None) -> ProjectSpec:
    """合并前端传入的可选参数，返回新的 ProjectSpec。"""

    if not options:
        return spec
    update: dict[str, object] = {}
    motif_specs = dict(spec.motif_specs)
    primary = dict(motif_specs.get("primary", {}))
    if options.motif_style:
        update["motif_style"] = options.motif_style
        primary["motif_style"] = options.motif_style
        primary["contour"] = options.motif_style
    if options.rhythm_density:
        update["rhythm_density"] = options.rhythm_density
        primary["rhythm_density"] = options.rhythm_density
    if options.harmony_level:
        update["harmony_level"] = options.harmony_level
    motif_specs["primary"] = primary
    update["motif_specs"] = motif_specs
    return spec.model_copy(update=update)


def _render_with_paths(
    spec: ProjectSpec,
    *,
    emit_midi: bool,
    tracks_to_export: list[str] | None = None,
) -> RenderResult:
    """在 outputs/ 下渲染并返回渲染结果。"""

    output_dir = ensure_directory(Path("outputs") / f"prompt_{uuid4().hex[:8]}")
    logger.info(
        "API rendering into %s (emit_midi=%s, tracks=%s)",
        output_dir,
        emit_midi,
        tracks_to_export,
    )
    return render_project(
        spec,
        output_dir,
        emit_midi=emit_midi,
        tracks_to_export=tracks_to_export,
    )


def _build_render_response(result: RenderResult) -> RenderResponse:
    """辅助函数：将渲染结果转换为 Pydantic 响应。"""

    return RenderResponse(
        output_dir=result["output_dir"],
        spec=result["spec"],
        summary=result["summary"],
        midi=result["midi"],
        project=result["project_spec"],
        sections=result["sections"],
        track_stats=result["track_stats"],
    )


@app.post("/generate", response_model=RenderResponse)
async def generate(request: GenerateRequest) -> RenderResponse:
    """根据自然语言 Prompt 生成项目规格并渲染。"""

    meta = parse_natural_prompt(request.prompt)
    spec = default_from_prompt_meta(meta)
    spec = _apply_options(spec, request.options)
    tracks = request.options.tracks if request.options else None
    result = _render_with_paths(
        spec,
        emit_midi=bool(request.options and request.options.emit_midi),
        tracks_to_export=tracks,
    )
    return _build_render_response(result)


@app.post("/render", response_model=RenderResponse)
async def render_existing(request: RenderRequest) -> RenderResponse:
    """渲染已有 ProjectSpec，常用于前端编辑后的再渲染。"""

    try:
        result = _render_with_paths(
            request.project,
            emit_midi=request.emit_midi,
            tracks_to_export=request.tracks,
        )
    except Exception as exc:  # pragma: no cover - FastAPI 错误路径
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _build_render_response(result)


@app.post("/regenerate-section", response_model=RenderResponse)
async def regenerate_section_api(
    request: RegenerateSectionRequest,
) -> RenderResponse:
    """仅针对某个段落执行再生成，返回新的摘要与 MIDI 路径。"""

    section_count = len(request.spec.form)
    if request.section_index < 0 or request.section_index >= section_count:
        raise HTTPException(status_code=400, detail="段落索引越界")

    spec = request.spec
    sections = list(spec.form)
    target_section = sections[request.section_index]

    # 当不保留动机时，尝试切换到未冻结的替代动机。
    if not request.keep_motif:
        motif_specs = {label: dict(data) for label, data in spec.motif_specs.items()}
        current_label = target_section.motif_label
        alternative = None
        for label, data in motif_specs.items():
            if label == current_label or data.get("_frozen"):
                continue
            alternative = label
            break
        if alternative:
            sections[request.section_index] = target_section.model_copy(
                update={"motif_label": alternative}
            )
            spec = spec.model_copy(update={"form": sections})

    # 更新再生成计数，保证渲染后 summary 记录正确次数。
    existing = dict(spec.generated_sections or {})
    target_name = spec.form[request.section_index].section
    entry = dict(existing.get(target_name, {}))
    entry["regeneration_count"] = int(entry.get("regeneration_count", 0)) + 1
    existing[target_name] = entry
    spec = spec.model_copy(update={"generated_sections": existing})

    result = _render_with_paths(
        spec,
        emit_midi=request.emit_midi,
        tracks_to_export=request.tracks,
    )
    return _build_render_response(result)


@app.post("/freeze-motif", response_model=FreezeMotifResponse)
async def freeze_motif(request: FreezeMotifRequest) -> FreezeMotifResponse:
    """将指定动机标签标记为冻结，防止后续被替换。"""

    motif_specs = {label: dict(data) for label, data in request.spec.motif_specs.items()}
    updated = False
    for tag in request.motif_tags:
        if tag not in motif_specs:
            raise HTTPException(status_code=404, detail=f"未知动机标签: {tag}")
        if not motif_specs[tag].get("_frozen"):
            motif_specs[tag]["_frozen"] = True
            updated = True
    if not updated:
        logger.info("Motif freeze request did not modify any state")
    project = request.spec.model_copy(update={"motif_specs": motif_specs})
    return FreezeMotifResponse(project=project)


@app.post("/save-project", response_model=SaveProjectResponse)
async def save_project(request: SaveProjectRequest) -> SaveProjectResponse:
    """将 ProjectSpec 保存到 projects/ 目录，返回文件路径。"""

    path = save_project_json(request.spec, request.name)
    return SaveProjectResponse(path=str(path))


@app.post("/load-project", response_model=LoadProjectResponse)
async def load_project(request: LoadProjectRequest) -> LoadProjectResponse:
    """从 projects/ 目录读取 ProjectSpec。"""

    try:
        spec = load_project_json(request.name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:  # pragma: no cover - 错误路径
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    path = str(Path("projects") / f"{request.name.replace('/', '_').replace('\\', '_')}.json")
    return LoadProjectResponse(project=spec, path=path)


@app.get("/download")
async def download_file(path: str) -> FileResponse:
    """提供输出目录内文件的下载服务，供前端获取 MIDI/JSON。"""

    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    resolved = file_path.resolve()
    allowed_roots = [Path("outputs").resolve(), Path("projects").resolve()]
    if not any(str(resolved).startswith(str(root)) for root in allowed_roots):
        raise HTTPException(status_code=400, detail="禁止访问该路径")
    return FileResponse(resolved, filename=file_path.name)


__all__ = ["app"]
