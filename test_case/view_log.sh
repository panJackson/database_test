#!/bin/bash
# 查看测试日志

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_DIR="$SCRIPT_DIR/logs"

# 如果没有指定日志文件，显示最新的
if [ -z "$1" ]; then
    LATEST_LOG=$(ls -t "$LOG_DIR"/test_text2sql_*.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        echo "未找到日志文件"
        exit 1
    fi
    LOG_FILE="$LATEST_LOG"
else
    LOG_FILE="$1"
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "日志文件不存在: $LOG_FILE"
    exit 1
fi

echo "查看日志: $LOG_FILE"
echo "文件大小: $(ls -lh "$LOG_FILE" | awk '{print $5}')"
echo ""
echo "按 Ctrl+C 退出"
printf "=%.0s" {1..80}
echo ""
echo ""

# 实时跟踪日志
tail -f "$LOG_FILE"

