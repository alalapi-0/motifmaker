# Motifmaker

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

## 7. 未来路线图（Roadmap）
- **和声扩展**：引入借用和弦、更多二级属、调式交替的策略库。
- **旋律发展**：支持节奏置换、序列推进、尾音延长的自动化操作。
- **表现力**：加入人性化力度、时值随机与动态曲线控制。
- **乐器库**：映射更丰富的 GM 音色，并预设与 DAW 模板的对接方案。
- **多模型支持**：允许接入外部旋律/和声生成模型或第三方 AI 服务。
- **UI 扩展**：增加谱面可视化、参数自动推荐与历史对比视图。

## 8. 常见问题 FAQ
- **为什么生成的旋律不悦耳？** 尝试降低节奏复杂度、减少张力峰值或切换至稳定调式。
- **浏览器为什么没声音？** 浏览器需要用户手势激活音频，请先点击播放按钮或其他控件。
- **跨域问题？** 确保后端启用了 CORS，并检查 `VITE_API_BASE` 是否指向正确域名与端口。

## 9. 许可与致谢
- 许可证：MIT（详见 [LICENSE](LICENSE)）。
- 致谢：项目使用了 FastAPI、Typer、music21、pretty_midi、Tone.js、React、TailwindCSS、Shoelace 等开源库。

## 10. 需要你来做（仓库所有者需执行的事项）
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
