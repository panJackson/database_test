#!/bin/bash
# 后台运行 test_text2sql.py 并保存日志（使用 venvtest 虚拟环境）

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
TEST_SCRIPT="$SCRIPT_DIR/test_text2sql.py"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/test_text2sql_venvtest.pid"
LOG_FILE="$LOG_DIR/test_text2sql_venvtest_$(date +%Y%m%d_%H%M%S).log"

# 虚拟环境配置
VENV_NAME="venvtest"
VENV_PATH="$PROJECT_ROOT/$VENV_NAME"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 检查虚拟环境是否存在
if [ ! -d "$VENV_PATH" ]; then
    echo "错误: 虚拟环境 '$VENV_NAME' 不存在于 $VENV_PATH"
    echo "请先创建虚拟环境或检查路径是否正确"
    exit 1
fi

# 检查虚拟环境的 Python 解释器
VENV_PYTHON="$VENV_PATH/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "错误: 虚拟环境中找不到 Python 解释器: $VENV_PYTHON"
    exit 1
fi

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "测试脚本已经在运行中 (PID: $OLD_PID)"
        echo "日志文件: $LOG_DIR/test_text2sql_venvtest_*.log"
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
echo "虚拟环境: $VENV_PATH"
echo "日志文件: $LOG_FILE"
echo "PID 文件: $PID_FILE"

# 使用 nohup 在后台运行，使用虚拟环境的 Python，并将所有输出重定向到日志文件
# 注意：nohup 不会自动激活虚拟环境，所以直接使用虚拟环境的 Python 解释器
nohup "$VENV_PYTHON" "$TEST_SCRIPT" "$@" > "$LOG_FILE" 2>&1 &
PID=$!

# 保存 PID
echo $PID > "$PID_FILE"

echo "测试已在后台启动"
echo "进程 ID (PID): $PID"
echo "日志文件: $LOG_FILE"
echo ""
echo "查看日志命令:"
echo "  tail -f $LOG_FILE"
echo "  或使用: $SCRIPT_DIR/view_log_venvtest.sh"
echo ""
echo "停止测试命令:"
echo "  $SCRIPT_DIR/stop_background_venvtest.sh"
echo ""
echo "查看运行状态:"
echo "  ps -p $PID"

