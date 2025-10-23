"""FastAPI Web 界面入口，封装 MotifMaker 简化版的各项服务。"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tools import generator
from tools.cleanup import cleanup_outputs
from tools import synth

# Web 应用所在的根目录，便于拼装模板与静态文件路径
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# 与 CLI 共用的 outputs 目录，所有音频与 JSON 临时文件都会写入这里
OUTPUT_DIR = generator.OUTPUT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="MotifMaker 8-bit Web UI")

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


def _delayed_shutdown() -> None:
    """延迟执行进程退出，确保响应先返回给客户端。"""

    time.sleep(0.5)
    os._exit(0)


@app.post("/shutdown")
async def shutdown_server() -> JSONResponse:
    """触发服务器的优雅关闭流程。"""

    threading.Thread(target=_delayed_shutdown, daemon=True).start()
    return JSONResponse(status_code=200, content={"status": "shutting_down"})
