"""FastAPI Web 界面入口，封装 MotifMaker 简化版的各项服务。"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tools import generator
from tools.cleanup import cleanup_outputs
from tools import synth
from tools import db as project_db

# Web 应用所在的根目录，便于拼装模板与静态文件路径
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# 与 CLI 共用的 outputs 目录，所有音频与 JSON 临时文件都会写入这里
OUTPUT_DIR = generator.OUTPUT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MotifMaker 8-bit Web UI")
project_db.init_db()

# 配置模板系统与静态文件服务，便于浏览器加载页面与脚本
try:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
except AssertionError:
    # 若运行环境未安装 jinja2，则延迟到路由中手动读取静态 HTML
    templates = None

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")


def _safe_output_path(filename: str) -> Path:
    """对外暴露的文件名必须限制在 outputs 目录内。"""

    candidate = OUTPUT_DIR / filename
    resolved = candidate.resolve()
    try:
        resolved.relative_to(OUTPUT_DIR.resolve())
    except ValueError as exc:  # noqa: B904
        raise HTTPException(status_code=400, detail="Invalid file path") from exc
    return resolved


def _compute_length_beats(arrangement: Optional[Dict[str, Any]]) -> Optional[int]:
    """根据编曲数据估算总拍数，用于统计时长。"""

    if not arrangement:
        return None
    melody = arrangement.get("melody") if isinstance(arrangement, dict) else None
    if not isinstance(melody, list):
        return None
    total = 0.0
    for note in melody:
        if isinstance(note, dict):
            duration = note.get("duration")
            if isinstance(duration, (int, float)):
                total += float(duration)
    if total <= 0:
        return None
    return int(round(total))


def _safe_int(value: object) -> Optional[int]:
    """尝试将传入值转换为整数，失败则返回 None。"""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _collect_project_payload(mp3_name: Optional[str]) -> Dict[str, Optional[object]]:
    """组合保存项目所需的数据，若缺少关键文件则抛出异常。"""

    motif_path = OUTPUT_DIR / "motif.json"
    motif_scale: Optional[str] = None
    motif_value: Optional[str] = None
    if motif_path.exists():
        motif_value = str(motif_path)
        try:
            with motif_path.open("r", encoding="utf-8") as fh:
                motif_meta = json.load(fh)
            motif_scale = motif_meta.get("scale")
        except (OSError, json.JSONDecodeError):
            motif_scale = None

    arrangement_path = OUTPUT_DIR / "arrangement.json"
    if not arrangement_path.exists():
        raise ValueError("Arrangement data not found. Please generate melody first.")

    try:
        with arrangement_path.open("r", encoding="utf-8") as fh:
            arrangement = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Failed to read arrangement data.") from exc

    if not mp3_name:
        raise ValueError("MP3 name is required for project saving.")

    mp3_path = _safe_output_path(mp3_name)
    if not mp3_path.exists():
        raise FileNotFoundError(str(mp3_path))

    length_beats = _compute_length_beats(arrangement)
    bpm_value = arrangement.get("bpm") if isinstance(arrangement, dict) else None

    return {
        "motif_path": motif_value,
        "arrangement_path": str(arrangement_path),
        "mp3_path": str(mp3_path),
        "bpm": _safe_int(bpm_value),
        "scale": motif_scale,
        "length": _safe_int(length_beats),
    }


def _mp3_url_from_path(mp3_path: Optional[str]) -> Optional[str]:
    """将文件路径转换为对外可访问的 URL。"""

    if not mp3_path:
        return None
    candidate = Path(mp3_path)
    if not candidate.exists():
        return None
    try:
        candidate.relative_to(OUTPUT_DIR)
    except ValueError:
        return None
    return f"/outputs/{candidate.name}"


def _error_response(message: str, status_code: int = 400) -> JSONResponse:
    """统一的错误响应格式，包含 error 标记与消息。"""

    return JSONResponse(status_code=status_code, content={"error": True, "message": message})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """渲染主页模板，提供按钮式操作界面。"""

    if templates is None:
        html_path = TEMPLATES_DIR / "index.html"
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/check_env")
async def check_env() -> JSONResponse:
    """调用现有生成器模块的环境检查函数。"""

    status = generator.check_environment()
    return JSONResponse(status_code=200, content=status)


@app.post("/generate_motif")
async def generate_motif_endpoint() -> JSONResponse:
    """生成新动机并输出预览音频，供前端循环试听。"""

    motif = generator.generate_motif()
    preview_path = OUTPUT_DIR / "preview_motif.wav"
    synth.synthesize_preview(motif, preview_path)
    response: Dict[str, Any] = {
        "motif": motif,
        "preview_url": f"/preview?file={preview_path.name}",
    }
    return JSONResponse(status_code=200, content=response)


@app.post("/generate_melody")
async def generate_melody_endpoint() -> JSONResponse:
    """基于上一阶段的动机生成旋律与编曲，并返回预览地址。"""

    motif_file = OUTPUT_DIR / "motif.json"
    if not motif_file.exists():
        raise HTTPException(status_code=400, detail="Motif not found. Please generate motif first.")

    with motif_file.open("r", encoding="utf-8") as fh:
        motif_data = json.load(fh)

    motif_list = motif_data.get("motif")
    if not isinstance(motif_list, list) or not motif_list:
        raise HTTPException(status_code=400, detail="Stored motif is invalid.")

    melody = generator.expand_motif_to_melody(motif_list)
    arrangement = generator.arrange_to_tracks(melody)

    preview_path = OUTPUT_DIR / "preview_melody.wav"
    synth.synthesize_preview(arrangement, preview_path)

    response: Dict[str, Any] = {
        "arrangement": arrangement,
        "preview_url": f"/preview?file={preview_path.name}",
    }
    return JSONResponse(status_code=200, content=response)


@app.get("/preview")
async def preview(file: str = Query(..., description="Name of the preview WAV file")) -> FileResponse:
    """以文件下载的方式返回最新的预览 WAV 音频。"""

    preview_path = _safe_output_path(file)
    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview file not found.")
    return FileResponse(preview_path, media_type="audio/wav", filename=preview_path.name)


@app.post("/render")
async def render_final() -> JSONResponse:
    """渲染最终 8-bit MP3，并返回可供下载的链接。"""

    arrangement_file = OUTPUT_DIR / "arrangement.json"
    if not arrangement_file.exists():
        raise HTTPException(status_code=400, detail="Arrangement not found. Please generate melody first.")

    with arrangement_file.open("r", encoding="utf-8") as fh:
        arrangement = json.load(fh)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    wav_path = OUTPUT_DIR / f"final_{timestamp}.wav"
    mp3_path = OUTPUT_DIR / f"final_{timestamp}.mp3"

    synth.synthesize_8bit_wav(arrangement, wav_path)
    synth.wav_to_mp3(wav_path, mp3_path, keep_wav=False)

    response = {
        "mp3_url": f"/outputs/{mp3_path.name}",
        "filename": mp3_path.name,
    }
    return JSONResponse(status_code=200, content=response)


@app.delete("/cleanup")
async def cleanup_endpoint() -> JSONResponse:
    """删除 outputs 目录下的所有运行时产物，并返回清理结果。"""

    deleted_files = []
    if OUTPUT_DIR.exists():
        deleted_files = [path.name for path in OUTPUT_DIR.iterdir()]
    cleanup_outputs(auto_confirm=True)
    response = {
        "deleted_files": deleted_files,
        "status": "ok",
    }
    return JSONResponse(status_code=200, content=response)


@app.get("/projects")
async def list_projects_endpoint() -> JSONResponse:
    """返回所有已保存项目的列表，附带可用的 MP3 链接。"""

    project_db.init_db()
    raw_projects = project_db.list_projects()
    projects = []
    for item in raw_projects:
        entry = dict(item)
        entry["mp3_url"] = _mp3_url_from_path(entry.get("mp3_path"))
        projects.append(entry)
    print(f"Listing {len(projects)} saved project(s) via API.")
    return JSONResponse(status_code=200, content={"projects": projects})


@app.post("/projects")
async def save_project_endpoint(request: Request) -> JSONResponse:
    """保存当前输出目录中的项目数据。"""

    payload = await request.json()
    name = (payload.get("name") or "").strip()
    mp3_name = payload.get("mp3_name") or payload.get("mp3") or payload.get("mp3_path")
    if not name:
        name = datetime.now().strftime("Project %Y-%m-%d %H:%M:%S")

    project_db.init_db()
    try:
        project_payload = _collect_project_payload(mp3_name)
        project_id = project_db.save_project(
            name=name,
            motif_path=project_payload["motif_path"],
            arrangement_path=project_payload["arrangement_path"],
            mp3_path=project_payload["mp3_path"],
            bpm=project_payload["bpm"],
            scale=project_payload["scale"],
            length=project_payload["length"],
        )
    except ValueError as exc:
        return _error_response(str(exc), status_code=400)
    except FileNotFoundError:
        return _error_response("MP3 file not found. Please render before saving.", status_code=400)
    except Exception as exc:  # noqa: BLE001
        return _error_response(f"Unexpected error: {exc}", status_code=500)

    print(f"Saved project #{project_id} with name '{name}' via API.")
    return JSONResponse(status_code=201, content={"id": project_id, "name": name})


@app.get("/projects/{project_id}")
async def load_project_endpoint(project_id: int) -> JSONResponse:
    """根据项目 ID 返回完整信息，附带 MP3 URL。"""

    project_db.init_db()
    try:
        project = project_db.load_project(project_id)
    except ValueError:
        return _error_response("Project not found.", status_code=404)

    response = {
        "project": project,
        "mp3_url": _mp3_url_from_path(project.get("mp3_path")),
    }
    print(f"Loaded project #{project_id} via API.")
    return JSONResponse(status_code=200, content=response)


@app.delete("/projects/{project_id}")
async def delete_project_endpoint(project_id: int) -> JSONResponse:
    """删除项目记录并清理关联文件。"""

    project_db.init_db()
    try:
        project_db.delete_project(project_id)
    except ValueError:
        return _error_response("Project not found.", status_code=404)

    print(f"Deleted project #{project_id} via API.")
    return JSONResponse(status_code=200, content={"status": "deleted", "id": project_id})


@app.patch("/projects/{project_id}/rename")
async def rename_project_endpoint(project_id: int, request: Request) -> JSONResponse:
    """更新项目名称，支持前端重命名操作。"""

    payload = await request.json()
    new_name = (payload.get("name") or payload.get("new_name") or "").strip()
    if not new_name:
        return _error_response("New project name is required.")

    project_db.init_db()
    try:
        project_db.rename_project(project_id, new_name)
    except ValueError:
        return _error_response("Project not found.", status_code=404)

    print(f"Renamed project #{project_id} to '{new_name}' via API.")
    return JSONResponse(status_code=200, content={"status": "renamed", "id": project_id, "name": new_name})


def _delayed_shutdown() -> None:
    """延迟执行进程退出，确保响应先返回给客户端。"""

    time.sleep(0.5)
    os._exit(0)


@app.post("/shutdown")
async def shutdown_server() -> JSONResponse:
    """触发服务器的优雅关闭流程。"""

    threading.Thread(target=_delayed_shutdown, daemon=True).start()
    return JSONResponse(status_code=200, content={"status": "shutting_down"})
