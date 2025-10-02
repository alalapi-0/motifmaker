# Motifmaker

Motifmaker 是一个分层式音乐生成原型，按照“动机 → 旋律 → 和声 → 渲染”的流水线，将自然语言 Prompt 解析成结构化的项目规格并输出文本、JSON 与可选 MIDI。

## 系统架构说明
- Prompt 解析层：`parsing.py` 负责提取情绪、速度、拍号与曲式线索，输出 `ProjectSpec` 所需的元数据。
- 骨架 JSON：`schema.py` 依据解析结果构造项目骨架，定义段落（Form）、动机字典、配器等字段。
- 动机层：`motif.py` 根据轮廓模板与节奏密度生成核心动机素材。
- 曲式展开：`form.py` 将动机映射到 A/B/Bridge 等段落，生成带节奏信息的草图。
- 和声层：`harmony.py` 结合调式与情绪，生成基础/色彩和声，并支持自然小调的属功能与二级属。
- 渲染层：`render.py` 输出 JSON、文字摘要及可选分轨 MIDI，并提供局部再生统计。
- Web UI：Vite + React + TailwindCSS + Shoelace + Tone.js 作为可视化控制台，通过 FastAPI 与上述层级交互。

## 当前功能（本次迭代）
- 自然语言生成与再生：支持全量生成、局部再生、动机冻结。
- 分轨导出：可选择旋律/和声/贝斯/打击任意子集，并返回每条轨道的音符数量与时长。
- 工程持久化：CLI/API 可保存与载入 `ProjectSpec`，便于多轮迭代。
- Web UI：提供 Prompt 输入、参数旋钮、段落表格、局部再生按钮、在线播放（Tone.js）与 MIDI 下载。
- CLI 增强：新增 `regen-section`、`save-project`、`load-project` 三个命令，均附中文帮助与错误提示。
- 解析增强：覆盖 10+ 情绪场景预设，支持显式 BPM/拍号/曲式模板解析，自动识别“二级属”等关键词。

## 使用步骤
### Python 端
1. 安装依赖并运行测试：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 使用 .venv\\Scripts\\activate
   pip install -r requirements.txt
   pytest -q
   ```
2. 启动 API 服务：
   ```bash
   uvicorn motifmaker.api:app --reload
   ```
3. 使用 CLI 生成或再生：
   ```bash
   motifmaker init-from-prompt "城市夜景 Lo-Fi" --out outputs/demo --emit-midi
   motifmaker regen-section --spec outputs/demo/spec.json --section-index 1 --keep-motif true --out outputs/demo_regen
   motifmaker save-project --spec outputs/demo/spec.json --name city_night_v1
   motifmaker load-project --name city_night_v1 --out outputs/from_saved
   ```

### Web 端
1. 启动前端开发服务器：
   ```bash
   cd web
   npm install
   npm run dev
   ```
2. 浏览器访问 http://localhost:5173；若后端不在本机，可在启动前设置 `VITE_API_BASE=http://后端地址:端口`。
3. 保证后端 FastAPI 通过 `uvicorn motifmaker.api:app --reload` 运行后，再在 UI 中输入 Prompt 并点击“一键生成”。
4. 左侧面板可覆盖节奏/调性/配器，右侧表格可编辑段落并局部再生成；下载栏仅提供链接，不会将 .mid/.json 纳入仓库。
5. 若浏览器无声，请先点击播放按钮以激活音频上下文；如遇跨域需在后端允许前端来源。

## 参数与交互大纲
- 情绪旋钮：滑块映射至和声复杂度（柔和/色彩），对应 `harmony_level`。
- 乐理旋钮：下拉菜单控制调性、调式、速度(BPM)与拍号，实时更新 `ProjectSpec`。
- 制作旋钮：复选框切换配器厚度（钢琴、弦乐、合成器等），同时可选择分轨导出集合。
- 曲式编辑表：表格支持修改每段的 `bars` 与 `tension`，并提供“局部再生成”“更换动机再生”“冻结动机”按钮。
- 局部再生：调用 `/regenerate-section`，可选择是否保留原动机标签。
- 动机冻结：调用 `/freeze-motif` 将指定标签的 `_frozen` 标记设为 `true`。

## 输出与文件结构
- `outputs/*.mid`：可选生成的 MIDI，命名如 `outputs/prompt_xxxx/track.mid`。
- `outputs/*.json`：渲染后的项目规格（带再生计数）。
- `outputs/summary.txt`：按段落生成的文字摘要。
- `projects/*.json`：通过 `save-project` 或 API `/save-project` 保存的工程快照。
- Web UI 产物存放于 `web/`，构建产出的 `web/dist/` 已加入 `.gitignore`。

## 未来蓝图（Roadmap）
- 高级和声：引入借用和弦、完善二级属体系，支持更多调式转换案例。
- 变奏算子：扩展节奏置换、序列推进、力度与时值人性化处理。
- 音色库：建立 GM 到多音源的映射，并与 Ableton/Logic 等 DAW 模板打通。
- 多模型支持：允许接入外部旋律/和声生成模型，构建多风格模板库。

## 常见问题（FAQ）
- **生成结果不悦耳怎么办？** 降低节奏密度、提高调性稳定度、减少张力峰值即可获得更平滑的编排。
- **浏览器播放无声？** 某些浏览器需要用户点击页面后才允许播放音频，请先与页面交互后再点击播放按钮。
- **如何仅导出旋律轨？** 在参数面板勾选需要的分轨即可，渲染结果的 `track_stats` 会同步更新。
- **下载按钮提示 404？** 请确认后端服务仍在运行，并检查生成的 `outputs/` 目录中文件是否仍存在；必要时重新触发一次渲染以刷新文件路径。

## 许可与致谢
- 许可证：MIT（详见 [LICENSE](LICENSE)）。
- 致谢：项目使用了 FastAPI、Typer、pretty_midi、TailwindCSS、Shoelace、Tone.js、@tonejs/midi 等优秀的开源组件。

## 需要你来做
- 如要部署线上 Demo：准备一个静态托管平台（Vercel/Netlify 等）及后端部署位置（Railway/Render/自有 VPS）。
- 如要接入外部 AI 模型：请在本地 `.env` 中配置 API Key，避免提交到仓库。
- 如要启用 HTTPS 或自定义域名：准备域名与证书，或使用托管平台的自动证书功能。
- 如需持久云存储：提供 S3/OSS 等凭据（同样建议放置在 `.env`）。
- 本地开发需安装 Node.js ≥ 18 用于前端构建与调试。

