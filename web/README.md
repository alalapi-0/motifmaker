# Motifmaker Web 前端

本目录包含使用 Vite + React + TypeScript + TailwindCSS + Shoelace + Tone.js 构建的可视化控制台。界面提供 Prompt 输入、参数覆盖、曲式表格、MIDI 播放与下载能力。

## 启动步骤
1. 安装依赖并启动开发服务器：
   ```bash
   cd web
   npm install
   npm run dev
   ```
2. 浏览器访问 [http://localhost:5173](http://localhost:5173)。默认会请求本机的后端接口。
3. 后端需提前运行：
   ```bash
   uvicorn motifmaker.api:app --reload
   ```

## 环境变量
- `VITE_API_BASE`：可选。用于指定后端 API 基础地址，例如 `http://127.0.0.1:8000`。未设置时默认取本地地址。

## 联调说明
- 前端调用的接口包括 `/generate`、`/regenerate-section`、`/save-project`、`/load-project`，均采用 `POST` 并传 JSON。
- 生成成功后会返回 `mid_path` 和 `json_path`，前端仅提供下载链接，不会提交任何二进制产物到仓库。
- 播放器使用 Tone.js，需手动点击“播放”才能激活音频上下文，否则浏览器会拦截自动播放。

## 常见问题
- **播放无声**：请先在页面内点击任意按钮（例如“播放”），以触发浏览器允许音频播放。若依旧无声，可检查后端是否正确返回 MIDI 路径。
- **跨域错误**：若后端不在同一主机，请在 `.env` 中设置 `VITE_API_BASE` 并确保后端允许对应的 CORS 来源。
- **端口占用**：开发服务器默认占用 5173，可通过运行 `npm run dev -- --port 5174` 指定其他端口。
- **文件 404**：生成后的 MIDI/JSON 会保存在后端的 outputs/ 目录，若被清理需重新生成后再下载。

