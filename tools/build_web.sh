#!/usr/bin/env bash
# 中文注释：该脚本仅负责触发 Vite 前端的构建，供 CI 或桌面端构建流程复用。
# 使用 set -euo pipefail 保证任意一步失败都会立即退出，避免产出不完整的 dist/。
set -euo pipefail

# 中文注释：脚本位置在 tools/，需切换到 web/ 目录后执行 npm 命令。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/../web"

# 中文注释：安装依赖时关闭 npm 审计与基金提示，加快自动化流程；若已安装会自动跳过。
npm install --no-audit --no-fund

# 中文注释：构建产物输出到 web/dist/，该目录已在 .gitignore 中忽略。
npm run build
