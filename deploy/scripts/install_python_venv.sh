#!/usr/bin/env bash
# ===============================
# MotifMaker 部署脚本：install_python_venv.sh
# 功能：在当前仓库目录内创建 Python 虚拟环境，安装依赖并输出常见排障建议。
# 使用场景：VPS/裸机部署首次执行；重复运行会复用已有虚拟环境。
# 风险提示：脚本使用 set -euo pipefail，遇到错误会立即退出以避免部分操作成功造成脏环境。
# ===============================
set -euo pipefail

# 目录与文件定义，可根据需要修改但需同步 systemd 配置。
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"

cat <<'DESC'
[信息] 开始初始化 Python 虚拟环境。
- 若需要使用镜像源，请在执行前设置 PIP_INDEX_URL 或在下方命令中追加 -i 参数。
- 如果网络环境受限，可参考 deploy/README_DEPLOY.md 中的“常见问题”使用离线包。
DESC

# 检查 Python 是否可用，并提示版本。
if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 未找到 python3，请先安装 Python 3.10+。" >&2
  exit 1
fi
python3 --version

# 创建虚拟环境；若已存在则跳过创建。
if [ ! -d "${VENV_DIR}" ]; then
  echo "[信息] 创建虚拟环境目录 ${VENV_DIR}"
  python3 -m venv "${VENV_DIR}"
else
  echo "[信息] 检测到已有虚拟环境，直接复用 ${VENV_DIR}"
fi

# 激活虚拟环境并升级 pip。
# shellcheck disable=SC1091 # 允许 source 虚拟环境激活脚本。
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip

# 安装项目依赖，可根据需求切换为 requirements-dev.txt。
if [ -f "${REQUIREMENTS_FILE}" ]; then
  echo "[信息] 使用 ${REQUIREMENTS_FILE} 安装依赖"
  pip install -r "${REQUIREMENTS_FILE}"
else
  echo "[警告] 未找到 ${REQUIREMENTS_FILE}，请检查文件路径。" >&2
  exit 1
fi

cat <<'DESC'
[完成] 虚拟环境准备就绪。
- 如需启用 pre-commit，可以执行 "pip install pre-commit && pre-commit install"。
- 若安装速度缓慢，考虑使用如 https://mirrors.aliyun.com/pypi/simple 的镜像源。
DESC
