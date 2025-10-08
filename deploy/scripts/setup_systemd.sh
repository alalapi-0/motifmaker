#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：setup_systemd.sh
# 功能：生成 systemd 单元文件，指向当前仓库中的 Uvicorn 启动命令。
# 默认写入用户级服务目录 ~/.config/systemd/user/，如需系统级服务请按注释调整。
# 安全提示：脚本不会自动执行 systemctl 命令，需人工确认后再启用服务。
# ===============================
set -euo pipefail

REPO_DIR="$(pwd)"
SERVICE_NAME="motifmaker.service"
USER_SYSTEMD_DIR="${HOME}/.config/systemd/user"
VENV_PATH="${REPO_DIR}/.venv/bin/uvicorn"
ENV_FILE="${REPO_DIR}/.env"
HOST_VALUE="${HOST:-127.0.0.1}"
PORT_VALUE="${PORT:-8000}"

cat <<DESC
[信息] 准备生成 systemd 服务：${SERVICE_NAME}
- 仓库路径：${REPO_DIR}
- 虚拟环境 Uvicorn：${VENV_PATH}
- 环境变量文件：${ENV_FILE}
- 监听地址：${HOST_VALUE}:${PORT_VALUE}
DESC

mkdir -p "${USER_SYSTEMD_DIR}"
SERVICE_PATH="${USER_SYSTEMD_DIR}/${SERVICE_NAME}"

cat <<SERVICE > "${SERVICE_PATH}"
# MotifMaker systemd 单元文件
# 说明：此文件由 deploy/scripts/setup_systemd.sh 自动生成，用于用户级 systemd。
# 若需要写入 /etc/systemd/system/，请复制后由具有 sudo 权限的用户部署。
[Unit]
Description=MotifMaker FastAPI Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV_PATH} motifmaker.api:app --host ${HOST_VALUE} --port ${PORT_VALUE} --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
SERVICE

cat <<'DESC'
[完成] systemd 单元文件已写入。
接下来请手动执行以下命令完成启用：
  systemctl --user daemon-reload
  systemctl --user enable --now motifmaker

如需部署到系统级服务，可在 sudo 环境下将文件复制至 /etc/systemd/system/ 并运行：
  sudo systemctl daemon-reload
  sudo systemctl enable --now motifmaker

查看运行状态：
  systemctl --user status motifmaker
查看日志：
  journalctl --user -u motifmaker -f
DESC
