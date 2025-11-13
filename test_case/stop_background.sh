#!/bin/bash
# 停止后台运行的 test_text2sql.py

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/test_text2sql.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "未找到 PID 文件，测试脚本可能未在运行"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "进程 $PID 不存在，可能已经停止"
    rm -f "$PID_FILE"
    exit 1
fi

echo "正在停止测试进程 (PID: $PID)..."

# 发送 SIGTERM 信号
kill "$PID"

# 等待进程结束
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "测试进程已停止"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 如果还没停止，强制杀死
if ps -p "$PID" > /dev/null 2>&1; then
    echo "进程未响应，强制停止..."
    kill -9 "$PID"
    sleep 1
    rm -f "$PID_FILE"
    echo "测试进程已强制停止"
else
    rm -f "$PID_FILE"
    echo "测试进程已停止"
fi

