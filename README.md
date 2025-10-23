# Motifmaker

## 🌍 Language
Current UI language: **English Only**
(All labels, tooltips, and prompts have been unified in English for consistency and better global readability.)

## 1. 项目简介
Motifmaker 是一个分层式音乐生成原型，支持从自然语言 Prompt → 骨架 JSON → 动机 → 段落展开 → 和声 → 渲染 → MIDI → Web UI 试听与下载的全流程。系统强调模块解耦，既适合研究实验，也能拓展成音乐创作工具。

## 2. 系统架构说明
```
Prompt → 解析层(parsing) → 骨架JSON(schema) → 动机生成(motif)
      → 曲式展开(form) → 和声填充(harmony) → 渲染MIDI(render)
      → 输出(outputs/*.mid, *.json)
      ↑
      Web前端(web/) ←→ FastAPI API
```
- **解析层（parsing）**：解析自然语言 Prompt，提取节奏、情绪、调式、曲式等元信息。
- **骨架 JSON（schema）**：根据解析结果建立 `ProjectSpec`，定义段落结构、动机字典与配器框架。
- **动机生成（motif）**：生成核心动机音高与节奏轮廓，为后续段落扩展提供素材。
- **曲式展开（form）**：将动机映射到各个段落，设定小节长度、张力与再生成计数。
- **和声填充（harmony）**：依据调式和情绪填入和弦走向，支持基础与色彩和声混合。
- **渲染 MIDI（render）**：整合旋律、和声、配器并输出 JSON、摘要与可选分轨 MIDI。
- **Web 前端（web/）**：提供参数控制台、段落编辑、播放器与下载入口，通过 FastAPI API 调用上述层。

## 3. 使用说明
### 后端
1. **环境准备**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
2. **运行测试（可选）**
   ```bash
   pytest -q
   ```
3. **运行 CLI 示例**
   ```bash
   motifmaker init-from-prompt "城市夜景 Lo-Fi" --out outputs/demo --emit-midi
   motifmaker regen-section --spec outputs/demo/spec.json --section-index 1 --keep-motif true --out outputs/demo_regen
   motifmaker save-project --spec outputs/demo/spec.json --name city_night_v1
   motifmaker load-project --name city_night_v1 --out outputs/from_saved
   ```
4. **启动 API 服务**
   ```bash
   uvicorn motifmaker.api:app --reload
   ```

### 前端
1. 进入前端目录并安装依赖：
   ```bash
   cd web
   npm i
   ```
2. 启动开发服务器：
   ```bash
   npm run dev
   ```
3. 浏览器访问 [http://localhost:5173](http://localhost:5173)。如需指向远程后端，可在启动前设置 `VITE_API_BASE=http://后端地址:端口`。

### 前端 UI 使用说明
- The interface language has been standardized to English. The i18n infrastructure remains intact for future translation.
- 见 Piano-Roll 可视化与参数面板。
- 顶部状态条提供固定的 “English Only” 提示与主题切换按钮，可查看后端健康状态与接口地址。
- Prompt 面板支持 Alt+Enter 快速触发生成，参数覆盖区可随时重置为后端最新解析结果。
- 曲式表格支持键盘导航：方向键移动单元格、Enter 编辑、Esc 取消，新增的冻结列可批量勾选后点击“冻结选中的动机”。
- 播放器与 Piano-Roll 联动：拖动进度条或点击 Piano-Roll 任意位置都会同步播放指针，循环模式可在播放器右侧开关。
- “复制骨架 JSON” 与 “导出当前视图设置” 会分别写入剪贴板与 localStorage，导出内容包含 Piano-Roll 缩放与主题偏好（语言固定为英文）。
- 常见错误提示：
  - 若播放器无声，多半是浏览器自动静音限制；请先点击播放键并确认系统音量。
  - 若请求失败，Shoelace `<sl-alert>` 会在顶部出现错误提示，常见原因包括跨域配置或后端服务未启动。
  - MIDI 解析失败会在日志区提示，可下载文件手动导入 DAW 检查。

## Web UI Mode

1. Install deps: `pip install -r tools/requirements.txt fastapi uvicorn jinja2`
2. Run: `uvicorn webapp.main:app --reload --port 8000`
3. Open browser at [http://127.0.0.1:8000](http://127.0.0.1:8000)
4. Use the web interface to generate, preview, re-generate, and export 8-bit MP3.
5. Click Cleanup to reset workspace.

## Project Persistence
MotifMaker now supports saving and loading projects.

CLI:
  python tools/cli.py → Project Management menu

Web UI:
  Buttons in “Project Management” section allow you to:
  - List saved projects
  - Save current session
  - Load existing project and preview
  - Delete or rename projects

All metadata is stored in data/motifmaker.db (SQLite).
No binary files are committed to Git.

## 🎨 New UI Flow (Version 0.3)
- Black-Red Metal Theme
- Step-by-Step Music Generation
  1. Motif → 2. Melody → 3. MIDI → 4. Mix → 5. Final Track
- Mixing step now uploads MIDI to an experimental audio renderer stub.

## 🔊 Audio Rendering (Providers)
- **Providers**：通过 `.env` 中的 `AUDIO_PROVIDER` 切换，当前支持：
  - `placeholder`：本地正弦波模拟渲染，开发调试零成本；
  - `hf`：调用 Hugging Face Inference API（需 `HF_API_TOKEN` 与 `HF_MODEL`）；
  - `replicate`：调用 Replicate Prediction API（需 `REPLICATE_API_TOKEN` 与 `REPLICATE_MODEL`）。
- **配置示例**（节选自 `.env.example`，请勿将真实 Token 入库）：

  ```ini
  AUDIO_PROVIDER=hf
  HF_API_TOKEN=hf_xxx                     # Hugging Face 个人 Token
  HF_MODEL=facebook/musicgen-small        # 可替换为私有端点
  RENDER_TIMEOUT_SEC=120                  # 推理超时（秒）
  RENDER_MAX_SECONDS=30                   # 限制生成音频最长时长
  AUTH_REQUIRED=true                      # 生产环境必须开启鉴权
  API_KEYS=tok_dev, tok_team              # 允许访问的 Token 列表
  PRO_USER_TOKENS=tok_team                # Pro 用户 Token 白名单
  DAILY_FREE_QUOTA=10                     # 每 Token 每日免费次数
  QUOTA_BACKEND=sqlite                    # 配额存储后端
  ```

- **成本与配额策略**：
  - 免费用户：按 Token 统计每日调用次数，默认 `DAILY_FREE_QUOTA=10`；
  - Pro 用户：将 Token 加入 `PRO_USER_TOKENS` 白名单，可跳过每日免费额度；
  - 配额存储由 `QUOTA_BACKEND` 决定，默认 `sqlite`（`var/usage.db`），开发可改为 `memory`，未来将支持集中式 Redis。
- **风险提示**：
  - 外部模型可能返回 429/5xx，后端已内置指数退避与 504 超时保护；
  - 不同 Provider 输出格式可能为 WAV/MP3，请在消费端处理多种音频类型；
  - 超时或模型加载（202 Accepted）会触发重试，必要时可增加 timeout。
- **安全提示**：
  - API Token 仅存放在 `.env`，务必加入 `.gitignore`，禁止提交到仓库；
  - 新版鉴权已弃用可伪造的 `X-User-Email`，所有付费路径必须依赖后端下发的 Token；
  - 前端不应硬编码 Token，如需测试请通过环境变量注入；
  - 生产部署建议将生成的音频上传到对象存储/CDN，由静态链接供前端访问，并确保开启 HTTPS。

## API Authentication & Quotas

### Authentication
- All costful endpoints (e.g., `/render`) require an API token.
- Header: `Authorization: Bearer <token>`.
- Tokens are configured via environment variable `API_KEYS`.
- In development you may set `AUTH_REQUIRED=false` (NOT recommended for production).

### Pro Tokens
- Tokens listed in `PRO_USER_TOKENS` bypass daily free quota checks.

### Quotas
- Daily free quota is per token (`DAILY_FREE_QUOTA`).
- Storage backends:
  - memory (dev only)
  - sqlite (default)
  - redis (planned)

## ⚙️ Async Rendering & Task API
- `POST /render/` → `202 Accepted`，返回 `{"task_id": "..."}`；任务将在后台异步执行。
- `GET /tasks/{id}` → 查询任务状态、进度以及 `result`/`error` 字段，供前端轮询。
- `DELETE /tasks/{id}` → 取消运行中的任务（尽力而为），返回最新状态快照。
- 默认运行模式为异步；在 `.env` 中将 `ENV=dev` 后，可通过 `?sync=1` 或请求体携带 `{"sync": true}` 触发同步调试，仅建议在开发环境使用。
- 渲染调用改为非阻塞实现，所有外部请求均使用 `httpx.AsyncClient` 与指数退避重试，事件循环可快速响应创建请求。
- `RENDER_MAX_CONCURRENCY` 控制并发上限，防止瞬时压垮第三方 Provider，后续可平滑替换为 Redis/消息队列。

> 兼容性提示：旧版前端若仍依赖同步返回音频 URL，可暂时在开发环境附加 `?sync=1` 参数。生产环境请尽快迁移至轮询任务模式。

## Path Safety & Download Rules
- All file paths are validated by `resolve()` + `relative_to()` against whitelisted roots.
- Allowed roots: `OUTPUT_DIR`, `PROJECTS_DIR`.
- Any attempt to access files outside these roots will be rejected with `E_VALIDATION`.
- Do not rely on string `startswith` checks. We use strict `Path`-based validation.

### 典型操作流程
1. 在 Web UI 输入 Prompt 并点击“生成”。
2. 试听或下载返回的 MIDI；必要时保存工程以便下次载入。
3. 在 FormTable 中调整段落参数，选择“局部再生成”或“保留动机再生”。
4. 使用“动机冻结”防止特定素材被替换，或通过“保存工程”持久化修改。
5. 需要分轨导出时，在参数面板勾选对应轨道后重新渲染。

## 4. 当前功能
- 一键生成：从 Prompt 自动生成动机、段落、和声与渲染输出。
- 局部再生：针对任意段落重新生成并更新再生成计数。
- 动机冻结：锁定动机标签，避免再生时被替换。
- 保存/加载工程：将 `ProjectSpec` 保存在 `projects/` 中，实现多轮迭代。
- 分轨导出：选择旋律、和声、贝斯、打击等轨道并获取统计信息。
- Web UI 试听与下载：基于 Tone.js 的播放器与 MIDI/JSON 下载链接。

## 5. 参数与交互
- **Tempo/Meter/Key/Mode**：调整速度、拍号与调式，直接影响渲染节奏与和声。
- **Instrumentation**：选择配器厚度或特定乐器组合，决定导出的轨道类型。
- **Harmony Options**：控制和声层级、二级属使用与色彩程度。
- **FormTable 编辑**：可修改段落小节数、张力值，并在任意行触发局部再生成或切换动机。
- **局部再生成逻辑**：当勾选“保留动机”时沿用原动机；取消勾选时会选择未冻结的替代动机。
- **播放器**：提供基本播放/暂停，当前音色仅为参考，导出的 MIDI 可在 DAW 中重新配置。

## 6. 输出文件结构
- `outputs/`：包含生成的 `.mid` 与 `.json` 文件，用于临时试听与下载（不提交仓库）。
- `projects/`：保存工程快照的 JSON 文件，便于在不同会话中继续编辑（不提交仓库）。
- `web/dist/`：前端构建产物，仅在部署时使用（不提交仓库）。

## 7. 后端稳态与部署注意

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `API_TITLE` | `MotifMaker API` | FastAPI 文档标题，可在生产环境展示品牌名称 |
| `API_VERSION` | `0.2.0` | 对外版本号，/version 端点也会返回该值 |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CORS 白名单，建议线上环境收敛到固定域名 |
| `OUTPUT_DIR` | `outputs` | 渲染产物存放目录，测试环境会自动指向临时目录 |
| `PROJECTS_DIR` | `projects` | 工程 JSON 持久化目录，确保具备读写权限 |
| `RATE_LIMIT_RPS` | `2` | 每个 IP 每秒允许的请求次数，轻量级内存限流 |
| `LOG_LEVEL` | `INFO` | 日志等级，可调为 `DEBUG` 或 `WARNING` |

示例 `.env`：

```env
# API_TITLE=My MotifMaker API
# API_VERSION=1.0.0
# ALLOWED_ORIGINS=https://music.example.com
# OUTPUT_DIR=/var/motifmaker/outputs
# PROJECTS_DIR=/var/motifmaker/projects
# RATE_LIMIT_RPS=5
# LOG_LEVEL=INFO
```

错误码以 `E_` 前缀表示，例如参数校验失败会返回：

```json
{
  "ok": false,
  "error": {
    "code": "E_VALIDATION",
    "message": "请求参数校验失败",
    "details": {"errors": [...]}
  }
}
```

应用日志采用统一格式 `[时间] 等级 模块 - 消息`，可通过 `LOG_LEVEL` 控制输出。若需对接集中日志服务，可在 `logging_setup.py` 中扩展 JSON Handler。

限流器为内存版滑动窗口，默认按 `IP+路径` 每秒 2 次。部署到多实例时请考虑迁移到 Redis 或 API Gateway 限流。

健康检查与元信息：

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/version
curl http://localhost:8000/config-public
```

仓库已在 `.gitignore` 中忽略 `outputs/`、`projects/`、`*.mid`、`web/node_modules/`、`web/dist/` 等目录，禁止将渲染产物与前端构建文件提交到版本库。

## Troubleshooting
- **Download returns E_VALIDATION**: ensure the requested path lives inside the configured outputs/projects directories; avoid lookalike folders such as `outputs_backup`.

## Desktop (Electron)

- **安装依赖**：
  ```bash
  cd desktop
  npm install
  ```
- **开发模式一键启动**（Vite + FastAPI + Electron 同时运行，Electron 会在 `MM_ELECTRON_SKIP_BACKEND=1` 的前提下跳过内置子进程，仅负责健康检查与窗口加载）：
  ```bash
  cd desktop
  npm run dev
  ```
  - 脚本内部并发执行 `web` 的 `npm run dev`、`python -m uvicorn ... --reload` 与 `ts-node src/main.ts --dev`，前端热更新与后端自动重载可即时生效。
- **手动分步启动（可选）**：在三个终端中依次运行 `cd web && npm run dev`、`python -m uvicorn motifmaker.api:app --reload`、`cd desktop && ts-node src/main.ts --dev`。
- **生产构建流程**：
  ```bash
  cd web && npm install && npm run build
  cd ../desktop && npm install && npm run build
  npm run dist   # 产物写入仓库根目录 release/
  ```
- **运行行为**：生产模式下 Electron 会自动拉起 FastAPI 子进程，轮询 `/healthz` 确认就绪后加载 `web/dist` 静态资源；退出时通过 SIGTERM（或 Windows taskkill）确保后端不残留。
- **常见问题**：
  - 端口占用：请确认 5173（Vite）与 8000（FastAPI）空闲，可通过 `MM_BACKEND_PORT` 调整后端监听端口。
  - Python 缺失：启动失败会弹出错误提示，请在仓库根执行 `pip install -r requirements.txt`。
  - 白屏或资源 404：通常是 `web/dist` 未构建或 CSP 阻止外部资源，请重新执行 `npm run build` 并确保未手动修改 `electron-builder.yml` 中的路径。
  - 离线场景：桌面端完全依赖本地 FastAPI，断网后仍可完成 MIDI 生成、试听与下载。

## 8. 未来路线图（Roadmap）
- **和声扩展**：引入借用和弦、更多二级属、调式交替的策略库。
- **旋律发展**：支持节奏置换、序列推进、尾音延长的自动化操作。
- **表现力**：加入人性化力度、时值随机与动态曲线控制。
- **乐器库**：映射更丰富的 GM 音色，并预设与 DAW 模板的对接方案。
- **多模型支持**：允许接入外部旋律/和声生成模型或第三方 AI 服务。
- **UI 扩展**：增加谱面可视化、参数自动推荐与历史对比视图。

## 9. 常见问题 FAQ
- **为什么生成的旋律不悦耳？** 尝试降低节奏复杂度、减少张力峰值或切换至稳定调式。
- **浏览器为什么没声音？** 浏览器需要用户手势激活音频，请先点击播放按钮或其他控件。
- **跨域问题？** 确保后端启用了 CORS，并检查 `VITE_API_BASE` 是否指向正确域名与端口。

## 10. 部署与运维
- **最简部署命令清单**：
  1. `bash deploy/scripts/install_python_venv.sh`
  2. `cp deploy/env/.env.example.server .env && vim .env`
  3. `bash deploy/scripts/setup_systemd.sh`
  4. 配置 Nginx 或 Caddy（示例见 `deploy/nginx/` 与 `deploy/caddy/`）
- **健康检查**：部署完成后务必执行 `bash deploy/scripts/check_health.sh` 与 `bash deploy/scripts/smoke_test.sh`，确保链路通畅。
- **更多细节**：包含 Docker/Compose、日志、安全实践在内的完整指南请阅读 [`deploy/README_DEPLOY.md`](deploy/README_DEPLOY.md)。

## Continuous Integration
This repository ships with a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs:
- Python linting (ruff) and unit tests (pytest)
- Web ESLint and unit tests (Vitest + React Testing Library)
- Optional typecheck for the Electron project

Run locally:
- Python: `ruff .` and `pytest -q`
- Web: `cd web && npm run lint && npm run test`
- Electron (optional): `cd desktop && tsc -p tsconfig.json --noEmit`

## 10. 许可与致谢
- 许可证：MIT（详见 [LICENSE](LICENSE)）。
- 致谢：项目使用了 FastAPI、Typer、music21、pretty_midi、Tone.js、React、TailwindCSS、Shoelace 等开源库。

## 11. 需要你来做（仓库所有者需执行的事项）
- **若要上线 Demo**：
  - 提供前端托管环境（如 Vercel、Netlify）。
  - 提供后端运行环境（VPS、Render、Railway 等）。
- **若要接入外部 AI 模型**：
  - 提供 API Key 并存放于 `.env`，不要提交到仓库。
- **若要使用自定义域名和 HTTPS**：
  - 提供域名与证书，或选择平台自动证书配置。
- **若要启用云存储（可选）**：
  - 提供云存储凭据（S3、OSS 等）以保存渲染结果。
- **本地开发环境准备**：
  - 安装 Node.js ≥ 18 与 Python ≥ 3.10，以确保前后端均可正常运行。


## Lightweight 8-bit Music Generator (CLI)

Run:
```
pip install -r tools/requirements.txt
python tools/cli.py
```

Menu:
```
1) Check environment
2) Generate motif (previewable)
3) Generate melody & arrangement (previewable)
4) Render 8-bit & export MP3
5) Cleanup / Reset
6) Exit
```

Options:
```
--run-all     Run all steps automatically
--keep-wav    Keep intermediate WAV files
```

Notes:
- `pydub` requires a working `ffmpeg` installation for MP3 export.
- All rendered audio stays under the local `outputs/` directory and is ignored by git.
- The repository ships without any audio binaries; use the CLI to preview content on demand.
- Users can regenerate previews at each step until they are satisfied.
