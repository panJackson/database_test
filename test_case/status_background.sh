#!/bin/bash
# 查看后台运行的 test_text2sql.py 状态

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/test_text2sql.pid"
LOG_DIR="$SCRIPT_DIR/logs"

if [ ! -f "$PID_FILE" ]; then
    echo "测试脚本未在运行"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "进程 $PID 不存在，测试脚本可能已停止"
    rm -f "$PID_FILE"
    exit 1
fi

printf "=%.0s" {1..60}
echo ""
echo "测试脚本运行状态"
printf "=%.0s" {1..60}
echo ""
echo "进程 ID (PID): $PID"
echo "运行时间: $(ps -p $PID -o etime= | xargs)"
echo "CPU 使用率: $(ps -p $PID -o %cpu= | xargs)%"
echo "内存使用: $(ps -p $PID -o rss= | xargs | awk '{printf "%.2f MB\n", $1/1024}')"
echo ""

# 查找最新的日志文件
LATEST_LOG=$(ls -t "$LOG_DIR"/test_text2sql_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo "最新日志文件: $LATEST_LOG"
    echo "日志文件大小: $(ls -lh "$LATEST_LOG" | awk '{print $5}')"
    echo ""
    echo "最后 10 行日志:"
    printf "-%.0s" {1..60}
    echo ""
    tail -n 10 "$LATEST_LOG"
else
    echo "未找到日志文件"
fi

