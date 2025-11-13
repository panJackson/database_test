#!/bin/bash
# 后台运行 test_text2sql.py 并保存日志

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
TEST_SCRIPT="$SCRIPT_DIR/test_text2sql.py"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/test_text2sql.pid"
LOG_FILE="$LOG_DIR/test_text2sql_$(date +%Y%m%d_%H%M%S).log"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "测试脚本已经在运行中 (PID: $OLD_PID)"
        echo "日志文件: $LOG_DIR/test_text2sql_*.log"
        exit 1
    else
        # PID 文件存在但进程不存在，删除旧的 PID 文件
        rm -f "$PID_FILE"
    fi
fi

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 启动后台进程
echo "正在启动后台测试..."
echo "日志文件: $LOG_FILE"
echo "PID 文件: $PID_FILE"

# 使用 nohup 在后台运行，并将所有输出重定向到日志文件
nohup python3 "$TEST_SCRIPT" "$@" > "$LOG_FILE" 2>&1 &
PID=$!

# 保存 PID
echo $PID > "$PID_FILE"

echo "测试已在后台启动"
echo "进程 ID (PID): $PID"
echo "日志文件: $LOG_FILE"
echo ""
echo "查看日志命令:"
echo "  tail -f $LOG_FILE"
echo ""
echo "停止测试命令:"
echo "  $SCRIPT_DIR/stop_background.sh"
echo ""
echo "查看运行状态:"
echo "  ps -p $PID"

