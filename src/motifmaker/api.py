"""FastAPI 服务入口，负责暴露音乐动机生成、渲染与工程管理接口。

该版本引入统一配置、错误码、日志与限流机制，确保在不改变既有功能
的前提下提升稳健性。所有新增逻辑均包含中文注释说明设计原因。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audio_render import router as audio_render_router
from .config import settings, OUTPUT_DIR
from .errors import (
    MMError,
    PersistenceError,
    RenderError,
    ValidationError,
    error_response,
    InternalServerError,
)
from .logging_setup import get_logger, setup_logging
from .parsing import parse_natural_prompt
from .persistence import load_project_json, save_project_json
from .ratelimit import rate_limiter
from .render import RenderResult, render_project
from .schema import ProjectSpec, default_from_prompt_meta
from .utils import ensure_directory

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.api_title, version=settings.api_version)

# 允许的跨域来源来自配置，生产环境建议收敛为固定域名列表。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)

# 中文注释：挂载静态目录前确保输出路径存在，避免启动时因目录缺失而失败。
ensure_directory(OUTPUT_DIR)
# 中文注释：开发阶段直接挂载 outputs 目录用于提供 MIDI/WAV 下载；生产环境建议使用 Nginx/Caddy 等专业静态服务。
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

# 中文注释：注册音频渲染路由，保持主应用初始化时完成依赖注入。
app.include_router(audio_render_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每次请求的核心指标，便于可观测性分析。"""

    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        client_ip = request.client.host if request.client else "anonymous"
        status_code = response.status_code if response else 500
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f ip=%s",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            client_ip,
        )


@app.exception_handler(MMError)
async def handle_mm_error(request: Request, exc: MMError):
    """捕获业务层异常并返回统一错误响应。"""

    client_ip = request.client.host if request.client else "anonymous"
    logger.warning(
        "handled_error method=%s path=%s status=%s ip=%s error_code=%s",
        request.method,
        request.url.path,
        exc.http_status,
        client_ip,
        exc.code,
    )
    return JSONResponse(status_code=exc.http_status, content=error_response(exc))


@app.exception_handler(RequestValidationError)
async def handle_pydantic_error(request: Request, exc: RequestValidationError):
    """将 FastAPI 的请求校验错误转换为统一错误码。"""

    err = ValidationError("请求参数校验失败", details={"errors": exc.errors()})
    return JSONResponse(status_code=err.http_status, content=error_response(err))


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    """兜底未知异常，避免堆栈泄露给客户端。"""

    client_ip = request.client.host if request.client else "anonymous"
    logger.error(
        "unhandled_error method=%s path=%s ip=%s",
        request.method,
        request.url.path,
        client_ip,
        exc_info=exc,
    )
    err = InternalServerError()
    return JSONResponse(status_code=err.http_status, content=error_response(err))


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


class MixRequest(BaseModel):
    """混音模拟请求体：前端传入 MIDI 路径与基础调参。"""

    midi_path: str
    reverb: int
    pan: int
    volume: float
    preset: str


class MixResponse(BaseModel):
    """混音模拟响应，仅返回占位波形地址，后续可扩展更多字段。"""

    wave_url: str


class SuccessMixResponse(BaseModel):
    """混音模拟成功返回包装，保持与其他接口一致的 {ok,result} 结构。"""

    ok: Literal[True]
    result: MixResponse


class SuccessRenderResponse(BaseModel):
    """统一响应包装：渲染成功时返回 ok/result。"""

    ok: Literal[True]
    result: RenderResponse


class SuccessFreezeResponse(BaseModel):
    """冻结动机成功后的统一响应结构。"""

    ok: Literal[True]
    result: FreezeMotifResponse


class SuccessSaveResponse(BaseModel):
    """保存工程成功返回包装。"""

    ok: Literal[True]
    result: SaveProjectResponse


class SuccessLoadResponse(BaseModel):
    """载入工程成功返回包装。"""

    ok: Literal[True]
    result: LoadProjectResponse


class HealthResponse(BaseModel):
    """健康检查响应，仅暴露时间戳方便探针使用。"""

    ok: Literal[True]
    ts: int


class VersionResponse(BaseModel):
    """版本信息响应，提供后端版本号。"""

    version: str


class ConfigPublicResponse(BaseModel):
    """可公开的配置快照，排除敏感信息。"""

    output_dir: str
    projects_dir: str
    allowed_origins: list[str]


def success_response(
    payload: BaseModel | RenderResult | dict[str, object],
) -> dict[str, object]:
    """统一成功响应格式，兼容 Pydantic 模型与普通字典。"""

    if isinstance(payload, BaseModel):
        result = payload.model_dump(mode="json")
    elif isinstance(payload, dict):
        result = payload
    else:
        result = dict(payload)
    return {"ok": True, "result": result}


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
    """在配置指定的目录下渲染并返回结果。"""

    base_dir = ensure_directory(settings.output_dir)
    output_dir = ensure_directory(Path(base_dir) / f"prompt_{uuid4().hex[:8]}")
    logger.info(
        "render_start",
        extra={
            "output_dir": str(output_dir),
            "emit_midi": emit_midi,
            "tracks": tracks_to_export,
        },
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


@app.post(
    "/generate",
    response_model=SuccessRenderResponse,
    dependencies=[Depends(rate_limiter)],
)
async def generate(request: GenerateRequest) -> dict[str, object]:
    """根据自然语言 Prompt 生成项目规格并渲染。"""

    if not request.prompt.strip():
        raise ValidationError("Prompt 不能为空")
    meta = parse_natural_prompt(request.prompt)
    spec = default_from_prompt_meta(meta)
    spec = _apply_options(spec, request.options)
    tracks = request.options.tracks if request.options else None
    result = _render_with_paths(
        spec,
        emit_midi=bool(request.options and request.options.emit_midi),
        tracks_to_export=tracks,
    )
    return success_response(_build_render_response(result))


@app.post(
    "/render",
    response_model=SuccessRenderResponse,
    dependencies=[Depends(rate_limiter)],
)
async def render_existing(request: RenderRequest) -> dict[str, object]:
    """渲染已有 ProjectSpec，常用于前端编辑后的再渲染。"""

    try:
        result = _render_with_paths(
            request.project,
            emit_midi=request.emit_midi,
            tracks_to_export=request.tracks,
        )
    except MMError:
        raise
    except Exception as exc:
        raise RenderError(str(exc)) from exc
    return success_response(_build_render_response(result))


@app.post(
    "/regenerate-section",
    response_model=SuccessRenderResponse,
    dependencies=[Depends(rate_limiter)],
)
async def regenerate_section_api(
    request: RegenerateSectionRequest,
) -> dict[str, object]:
    """仅针对某个段落执行再生成，返回新的摘要与 MIDI 路径。"""

    section_count = len(request.spec.form)
    if request.section_index < 0 or request.section_index >= section_count:
        raise ValidationError("段落索引越界")

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
    return success_response(_build_render_response(result))


@app.post(
    "/freeze-motif",
    response_model=SuccessFreezeResponse,
    dependencies=[Depends(rate_limiter)],
)
async def freeze_motif(request: FreezeMotifRequest) -> dict[str, object]:
    """将指定动机标签标记为冻结，防止后续被替换。"""

    motif_specs = {
        label: dict(data) for label, data in request.spec.motif_specs.items()
    }
    updated = False
    for tag in request.motif_tags:
        if tag not in motif_specs:
            raise ValidationError(f"未知动机标签: {tag}")
        if not motif_specs[tag].get("_frozen"):
            motif_specs[tag]["_frozen"] = True
            updated = True
    if not updated:
        logger.info("freeze_motif_skip", extra={"tags": request.motif_tags})
    project = request.spec.model_copy(update={"motif_specs": motif_specs})
    return success_response(FreezeMotifResponse(project=project))


@app.post(
    "/save-project",
    response_model=SuccessSaveResponse,
    dependencies=[Depends(rate_limiter)],
)
async def save_project(request: SaveProjectRequest) -> dict[str, object]:
    """将 ProjectSpec 保存到配置的 projects/ 目录，返回文件路径。"""

    try:
        path = save_project_json(request.spec, request.name)
    except MMError:
        raise
    except Exception as exc:
        raise PersistenceError(str(exc)) from exc
    return success_response(SaveProjectResponse(path=str(path)))


@app.post(
    "/load-project",
    response_model=SuccessLoadResponse,
    dependencies=[Depends(rate_limiter)],
)
async def load_project(request: LoadProjectRequest) -> dict[str, object]:
    """从配置的 projects/ 目录读取 ProjectSpec。"""

    try:
        spec = load_project_json(request.name)
    except MMError as exc:
        raise exc
    except FileNotFoundError as exc:
        raise PersistenceError(
            str(exc), details={"name": request.name}, http_status=404
        ) from exc
    except Exception as exc:
        raise PersistenceError(str(exc)) from exc
    path = Path(settings.projects_dir) / f"{request.name}.json"
    return success_response(LoadProjectResponse(project=spec, path=str(path)))


@app.post("/mix", response_model=SuccessMixResponse, dependencies=[Depends(rate_limiter)])
async def mix_preview(request: MixRequest) -> dict[str, object]:
    """模拟混音端点：当前返回占位音频地址，后续可替换为真实渲染。"""

    if not request.midi_path.strip():
        raise ValidationError("MIDI 路径不能为空")
    logger.info(
        "mix_preview", extra={"preset": request.preset, "reverb": request.reverb, "pan": request.pan, "volume": request.volume}
    )
    # 预留钩子：未来可在此调用外部模型或内部渲染引擎生成波形文件。
    dummy_url = "/dummy/audio_preview.mp3"
    return success_response(MixResponse(wave_url=dummy_url))


@app.get("/download")
async def download_file(path: str) -> FileResponse:
    """提供输出目录内文件的下载服务，供前端获取 MIDI/JSON。"""

    file_path = Path(path)
    if not file_path.exists():
        raise ValidationError("文件不存在")
    resolved = file_path.resolve()
    allowed_roots = [
        Path(settings.output_dir).resolve(),
        Path(settings.projects_dir).resolve(),
    ]
    if not any(str(resolved).startswith(str(root)) for root in allowed_roots):
        raise ValidationError("禁止访问该路径")
    return FileResponse(resolved, filename=file_path.name)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> dict[str, object]:
    """健康检查端点，供容器探针/监控系统探活。"""

    ts = int(time.time() * 1000)
    return {"ok": True, "ts": ts}


@app.get("/version", response_model=VersionResponse)
async def version() -> dict[str, object]:
    """返回后端版本信息，便于客户端与监控记录。"""

    return {"version": settings.api_version}


@app.get("/config-public", response_model=ConfigPublicResponse)
async def config_public() -> dict[str, object]:
    """返回可公开的配置快照，不包含敏感凭据。"""

    return {
        "output_dir": settings.output_dir,
        "projects_dir": settings.projects_dir,
        "allowed_origins": settings.allowed_origins,
    }


__all__ = ["app"]
