#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：run_uvicorn_dev.sh
# 功能：在本地虚拟环境中启动 Uvicorn 单进程，便于开发或临时验证。
# 风险提示：仅适用于开发环境；生产部署应使用 systemd + 反向代理确保高可用与安全。
# ===============================
set -euo pipefail

# shellcheck disable=SC1091 # 允许 source 虚拟环境激活脚本。
if [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "[错误] 未检测到 .venv 虚拟环境，请先执行 deploy/scripts/install_python_venv.sh" >&2
  exit 1
fi

HOST_VALUE="${HOST:-127.0.0.1}"
PORT_VALUE="${PORT:-8000}"

echo "[信息] 启动 Uvicorn，监听 ${HOST_VALUE}:${PORT_VALUE}，仅用于开发调试。"
exec uvicorn motifmaker.api:app --host "${HOST_VALUE}" --port "${PORT_VALUE}" --workers 1
