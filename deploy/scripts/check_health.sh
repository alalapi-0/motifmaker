#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：check_health.sh
# 功能：调用后端健康检查与版本接口，验证基础服务状态。
# 使用提示：部署后在反向代理或本机执行，失败时会返回非零退出码。
# ===============================
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

printf '[信息] 检查后端健康状态：%s\n' "${BASE_URL}"

if HEALTH_RESPONSE=$(curl -sf "${BASE_URL}/healthz"); then
  printf '[成功] /healthz 返回：%s\n' "${HEALTH_RESPONSE}"
else
  echo "[错误] /healthz 检查失败，请确认服务已启动。" >&2
  exit 1
fi

if VERSION_RESPONSE=$(curl -sf "${BASE_URL}/version"); then
  printf '[成功] /version 返回：%s\n' "${VERSION_RESPONSE}"
else
  echo "[错误] /version 检查失败，可能是应用未加载或路由变更。" >&2
  exit 1
fi
