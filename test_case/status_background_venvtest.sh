#!/bin/bash
# 查看后台测试运行状态（venvtest 版本）

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/test_text2sql_venvtest.pid"
LOG_DIR="$SCRIPT_DIR/logs"

if [ ! -f "$PID_FILE" ]; then
    echo "测试脚本未在运行（未找到 PID 文件）"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "测试脚本正在运行中"
    echo "进程 ID (PID): $PID"
    echo ""
    
    # 显示进程信息
    echo "进程信息:"
    ps -p "$PID" -o pid,ppid,cmd,etime,pcpu,pmem
    
    # 显示最新的日志文件
    LATEST_LOG=$(ls -t "$LOG_DIR"/test_text2sql_venvtest_*.log 2>/dev/null | head -1)
    if [ -n "$LATEST_LOG" ]; then
        echo ""
        echo "最新日志文件: $LATEST_LOG"
        echo "日志文件大小: $(ls -lh "$LATEST_LOG" | awk '{print $5}')"
        echo ""
        echo "最近 10 行日志:"
        echo "----------------------------------------"
        tail -n 10 "$LATEST_LOG"
    fi
else
    echo "测试脚本未在运行（进程 $PID 不存在）"
    rm -f "$PID_FILE"
    exit 1
fi

