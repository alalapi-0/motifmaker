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
│     ├─ PromptPanel.tsx   # Prompt 输入、生成按钮与参数预设（支持多语言与 Alt+Enter 快捷键）
│     ├─ ParamsPanel.tsx   # Tempo/Meter/Key/Mode/Instrumentation/Secondary Dominant 控件
│     ├─ FormTable.tsx     # 段落表格编辑、键盘导航、批量动机冻结与再生模式切换
│     ├─ Player.tsx        # 基于 Tone.js 的播放器，支持 seek/loop 与 Piano-Roll 联动
│     ├─ PianoRoll.tsx     # Canvas Piano-Roll 可视化，提供缩放、拖拽、hover 提示
│     ├─ DownloadBar.tsx   # 下载 JSON/MIDI、复制骨架、导出视图设置与工程保存
│     └─ TopStatusBar.tsx  # 顶部状态条，轮询健康检查、语言/主题切换
│  ├─ hooks/
│  │  └─ useI18n.ts        # 轻量 i18n Hook，封装上下文读取
│  └─ i18n.ts              # 中英文词典、Provider 与 localStorage 持久化逻辑
├─ index.html              # Vite HTML 模板
├─ vite.config.ts          # Vite 配置
└─ tailwind.config.cjs     # TailwindCSS 配置
```

## 使用示例
1. 在 Prompt 输入框填写描述（例如“城市夜景 Lo-Fi”），点击“生成”。
2. 在左侧参数面板调整 Tempo、拍号、调性、配器或和声选项，必要时触发重新渲染。
3. 在 FormTable 中使用方向键移动、Enter 编辑、Esc 取消，必要时勾选动机后点击“冻结选中的动机”。
4. Piano-Roll 中拖动滚动条或点击任意位置可与播放器同步，适合定位特定小节。
5. 使用播放器试听生成结果，确认后点击下载获取 MIDI/JSON，或保存工程以便日后加载。

## 部署提示
构建完成后，可将 `dist/` 上传至任意静态托管平台（如 Vercel、Netlify），并通过 `VITE_API_BASE` 指向线上 FastAPI 服务。仓库已忽略 `web/dist/`，请勿提交构建产物。

## i18n 使用方式
- 所有 UI 文案需通过 `useI18n()` 提供的 `t(key)` 获取；若需要插值，可传入字典 `t(key, { count: 4 })`。
- 当前实现为轻量级字典，后续若要接入 i18next，可在 `i18n.ts` 中替换 Provider 并保留 localStorage 存储约定。
- 语言切换会同步更新 `<html lang>` 属性，并在顶部状态条即时显示。

## 视图设置与主题
- 主题（浅色/深色）与 Piano-Roll 缩放倍率在用户操作时写入 `localStorage`，可通过下载栏的“导出当前视图设置”手动备份。
- `TopStatusBar` 会轮询 `/healthz`、`/version` 与 `/config-public`，每 30 秒刷新一次状态，组件卸载时会自动清理定时器与 AbortController。
- Player 在完成外部 seek 后会调用 `onSeekApplied` 通知上层清理状态，避免多次重复定位。
