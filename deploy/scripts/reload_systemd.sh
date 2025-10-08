#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：reload_systemd.sh
# 功能：快捷执行 daemon-reload 并重启 motifmaker 服务，适用于更新代码或配置后。
# 提示：脚本默认调用用户级 systemd，可根据需要添加 sudo 切换至系统级。
# ===============================
set -euo pipefail

SYSTEMCTL_CMD="systemctl --user"

cat <<'DESC'
[信息] 开始重新加载 systemd 并重启 motifmaker。
如需在系统级服务上操作，请将命令替换为 "sudo systemctl"。
DESC

${SYSTEMCTL_CMD} daemon-reload
${SYSTEMCTL_CMD} restart motifmaker

${SYSTEMCTL_CMD} status motifmaker --no-pager
