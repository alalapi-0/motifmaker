# Motifmaker Web 前端

本目录包含 Motifmaker 的 React + TypeScript 可视化控制台，提供 Prompt 输入、参数覆盖、曲式表格、播放器与下载功能。

## 快速开始
1. 安装依赖：
   ```bash
   cd web
   npm install
   ```
2. 启动开发服务器：
   ```bash
   npm run dev
   ```
3. 打开浏览器访问 [http://localhost:5173](http://localhost:5173)，确保后端 FastAPI 服务已通过 `uvicorn motifmaker.api:app --reload` 启动。

## 构建与其他脚本
- `npm run build`：构建生产版本，产物位于 `web/dist/`（已在 `.gitignore` 中排除）。
- `npm run preview`：在本地预览构建后的站点。
- `npm run test`：当前占位脚本，输出 `no tests yet (TODO: add Vitest suite)`，可在后续扩展为组件测试。

## 开发端口与 API 地址
- 开发服务器默认监听 `5173` 端口，可通过 `npm run dev -- --port 5174` 覆盖。
- 若后端部署在其他主机，可在启动前设置 `VITE_API_BASE=http://后端地址:端口`，前端会使用该值作为 API 基础路径。

## 文件结构
```
web/
├─ src/
│  ├─ App.tsx              # 页面骨架，组织主布局与上下文
│  ├─ main.tsx             # 入口文件，挂载 React 应用并引入全局样式
│  ├─ api.ts               # 封装与 FastAPI 通信的请求函数
│  ├─ styles.css           # TailwindCSS 扩展样式
│  └─ components/
│     ├─ PromptPanel.tsx   # Prompt 输入、生成按钮与参数预设
│     ├─ ParamsPanel.tsx   # Tempo、Meter、Key、Mode、Instrumentation、Harmony 控件
│     ├─ FormTable.tsx     # 表格形式的段落编辑、局部再生成与动机冻结
│     ├─ Player.tsx        # 基于 Tone.js 的播放器与音量控制
│     └─ DownloadBar.tsx   # 下载 JSON/MIDI 与保存工程的入口
├─ index.html              # Vite HTML 模板
├─ vite.config.ts          # Vite 配置
└─ tailwind.config.cjs     # TailwindCSS 配置
```

## 使用示例
1. 在 Prompt 输入框填写描述（例如“城市夜景 Lo-Fi”），点击“生成”。
2. 在左侧参数面板调整 Tempo、拍号、调性、配器或和声选项，必要时触发重新渲染。
3. 在 FormTable 中修改段落小节数、张力，或选择局部再生成 / 冻结动机。
4. 使用播放器试听生成结果，确认后点击下载获取 MIDI/JSON，或保存工程以便日后加载。

## 部署提示
构建完成后，可将 `dist/` 上传至任意静态托管平台（如 Vercel、Netlify），并通过 `VITE_API_BASE` 指向线上 FastAPI 服务。
