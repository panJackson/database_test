#!/bin/bash
# 从 .env 文件加载环境变量到当前 shell

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    # 读取 .env 文件并导出变量（忽略注释和空行）
    set -a
    source "$ENV_FILE"
    set +a
    echo "Environment variables loaded successfully!"
else
    echo "Warning: .env file not found at $ENV_FILE"
fi

