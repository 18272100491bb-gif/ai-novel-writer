#!/bin/bash
# SMTS + Kioku 一键启动脚本
# 用法: ./start.sh [storys_dir]
#
# 先起 Kioku sidecar（Python FastAPI，端口 49152），
# 等就绪后再启动 SMTS 主程序。

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="${1:-/home/admin/data/storys}"

# HuggingFace 国内镜像（用于 BGE Small 嵌入模型）
export HF_ENDPOINT=https://hf-mirror.com

# Kioku sidecar 启动
VENV_PYTHON=/home/admin/envs/kioku/bin/python3
if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: Python venv not found at $VENV_PYTHON"
    echo "Run: python3 -m venv /home/admin/envs/kioku && /home/admin/envs/kioku/bin/pip install ..."
    exit 1
fi

echo "=== Kioku Memory Engine - Starting ==="

mkdir -p "${DATA_DIR}"
export MEM0_DATA_DIR="${DATA_DIR}"
${VENV_PYTHON} "${BASE_DIR}/mem0/mem0_server.py" \
    --port 49152 \
    --data-dir "${DATA_DIR}" &

KIOCU_PID=$!
echo "Kioku PID: ${KIOCU_PID}"
for i in $(seq 1 10); do
    if curl -sf http://localhost:49152/health > /dev/null 2>&1; then
        echo "   Kioku ready on port 49152"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   WARNING: Kioku did not start within 10s, continuing anyway"
    fi
    sleep 1
done

echo "=== Show Me The Story - Starting ==="

# 访问密码验证（设了则前端需密码才能打开）
export AUTH_PASSWORD=01020817@qq.com

# 3. 启动 SMTS
cd "${BASE_DIR}"
"${BASE_DIR}/show-me-the-story" "${DATA_DIR}"
