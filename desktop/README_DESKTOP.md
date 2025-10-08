# MotifMaker Desktop 指南

> 中文注释：本文件说明 Electron 桌面端的目录结构、安全策略、构建流程与测试清单，避免二进制产物进入仓库。

## 目录结构

```
desktop/
├── package.json          # Electron 项目的 npm 配置与脚本
├── tsconfig.json         # TypeScript 编译配置，输出到 dist/
├── electron-builder.yml  # electron-builder 打包配置，输出 release/
├── src/
│   ├── main.ts           # Electron 主进程入口，负责窗口、安全策略与子进程编排
│   ├── preload.ts        # 预加载脚本，仅暴露受控 API 到渲染进程
│   ├── env.ts            # 环境探测与路径/端口配置（开发/生产）
│   ├── backend.ts        # FastAPI 子进程启动、探活与退出管理
│   └── csp.ts            # 内容安全策略（CSP）生成工具
└── README_DESKTOP.md     # 当前文件
```

- `dist/`：TypeScript 编译结果，随 `npm run build:electron` 生成，需在 `.gitignore` 中忽略。
- `../web/dist/`：Vite 构建产物，electron-builder 在打包时会复制到安装包内，请勿提交仓库。
- `../release/`：electron-builder 产出的安装包目录，务必保持为空或忽略。

## 安全策略

- **CSP**：`csp.ts` 生成的策略只允许 `default-src 'self'`，并限定 `connect-src` 到 `http://127.0.0.1:${port}`，防止桌面端访问任意外部站点。
- **Context Isolation**：`BrowserWindow` 强制 `contextIsolation: true`、`sandbox: true`、`nodeIntegration: false`，渲染进程无法直接访问 Node API。
- **Preload 最小暴露面**：`preload.ts` 仅透出 `getVersion`、`getProvider`、`openLogs`，所有调用都通过 IPC 洁白名单完成。
- **网络白名单**：主进程在 `onBeforeRequest` 阶段拦截非本地端口请求，阻止意外的外部 HTTP/WS 访问。
- **退出清理**：`backend.ts` 在 `before-quit` 阶段向子进程发送 `SIGTERM`（或 `taskkill`），确保后端不残留。

## 图标与签名

- **图标占位**：默认未配置应用图标。请在 `desktop/icons/` 放置 `app.icns`（macOS）与 `app.ico`（Windows），再在 `electron-builder.yml` 中补充 `icon` 字段。
- **代码签名**：打包为 macOS DMG/ZIP 或 Windows NSIS 时需根据团队证书配置签名。可参考 electron-builder 官方文档，或在 CI 中注入 `CSC_LINK`/`CSC_KEY_PASSWORD`。
- **勿包含大文件**：安装包不应携带音频样本、模型或项目输出，保持体积可控并符合版权要求。

## 开发与构建流程

1. **安装依赖**
   ```bash
   cd desktop
   npm install
   ```
2. **开发模式（热更新）**
   ```bash
   npm run dev
   ```
   - 脚本会同时启动 Vite、FastAPI（`--reload`）与 Electron 主进程。
   - Electron 检测到 `MM_ELECTRON_SKIP_BACKEND=1` 后不会重复启动后端，仅等待健康检查。
3. **单独运行 Electron（调试生产逻辑）**
   ```bash
   npm run build:web        # 在 web/ 目录生成 dist/
   npm run build:electron   # TypeScript -> dist/
   npm run start:electron   # 读取 dist/main.js，使用生产逻辑加载静态文件
   ```
4. **打包安装包**
   ```bash
   npm run build            # 等价于先构建 web，再编译 Electron
   npm run dist             # 通过 electron-builder 生成 release/ 下的安装包
   ```
   - 注意：`release/`、`dist/`、`web/dist/` 必须保持未提交状态。

## 常见问题排查

- **端口被占用**：默认使用 `5173`（前端）和 `8000`（后端）。若被占用，请结束冲突进程或通过环境变量 `MM_BACKEND_PORT` 覆盖。
- **Python 未安装**：若弹窗提示后端启动失败，请在仓库根安装依赖 `pip install -r requirements.txt`，确保 `uvicorn` 可用。
- **白屏或 404**：确认 `web/dist` 存在且 electron-builder 在打包时能读取到；必要时重新执行 `npm run build:web`。
- **离线环境**：桌面端只访问本地 FastAPI，断网仍可生成与试听 MIDI。

## 手工测试清单

| 场景 | 操作步骤 | 期望结果 |
| ---- | -------- | -------- |
| 开发模式热更新 | 运行 `npm run dev`，修改 `web/src` 或后端代码 | Electron 窗口实时热重载，uvicorn 热重启后仍可正常响应 |
| 生产模式本地安装包 | `npm run dist` 并在 release/ 目录手动安装 | 启动后自动拉起后端，UI 能完成生成/试听/下载 |
| 退出清理 | 打开应用后直接关闭窗口或退出菜单 | 后端子进程消失，无僵尸进程留存 |
| 离线模式 | 断开网络后启动应用 | UI 正常加载，后端仍在本机返回数据 |

> 提示：实际安装包体积较大，建议在 CI 中构建并上传至制品库，避免在 Git 仓库中提交任何二进制文件。
