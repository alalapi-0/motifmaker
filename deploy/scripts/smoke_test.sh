#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：smoke_test.sh
# 功能：向 /generate 接口发送轻量提示词，验证核心链路（请求 -> 推理调度 -> 响应）。
# 注意：脚本仅检查响应字段，不会下载或保存产物，适合部署后的烟囱测试。
# ===============================
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
PROMPT="城市夜景 温暖而克制 约两分钟"

printf '[信息] 对 %s 发送烟囱测试请求。\n' "${BASE_URL}"

RESPONSE=$(curl -sf -X POST "${BASE_URL}/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"prompt\": \"${PROMPT}\"}") || {
  echo "[错误] 请求 /generate 失败，请检查后端日志。" >&2
  exit 1
}

printf '[信息] 返回 JSON：%s\n' "${RESPONSE}"

if echo "${RESPONSE}" | grep -q '"ok"\s*:\s*true' && \
   echo "${RESPONSE}" | grep -q '"mid_path"' && \
   echo "${RESPONSE}" | grep -q '"json_path"'; then
  echo "[成功] 检测到 ok=true 且包含 mid_path/json_path 字段，烟囱测试通过。"
else
  echo "[错误] 响应缺少关键字段，请检查后端业务逻辑。" >&2
  exit 1
fi
