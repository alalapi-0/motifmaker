#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：tail_logs.sh
# 功能：实时查看 systemd 中 motifmaker 服务日志，辅助排障。
# 使用提示：默认监听用户级 journal，如需系统级请在命令前加 sudo 并移除 --user。
# ===============================
set -euo pipefail

SYSTEMCTL_SCOPE="--user"
UNIT_NAME="motifmaker"

cat <<'DESC'
[信息] 正在持续输出 motifmaker 日志。
- 退出可使用 Ctrl+C。
- 过滤关键字示例：journalctl --user -u motifmaker | grep "ERROR"。
DESC

journalctl ${SYSTEMCTL_SCOPE} -u "${UNIT_NAME}" -f
