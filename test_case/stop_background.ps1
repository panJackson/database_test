# PowerShell 脚本：停止后台运行的 test_text2sql.py

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $scriptDir "test_text2sql.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "未找到 PID 文件，测试脚本可能未在运行"
    exit 1
}

$pid = Get-Content $pidFile

try {
    $process = Get-Process -Id $pid -ErrorAction Stop
    Write-Host "正在停止测试进程 (PID: $pid)..."
    
    # 停止进程
    Stop-Process -Id $pid -Force
    
    Write-Host "测试进程已停止"
    Remove-Item $pidFile -Force
} catch {
    Write-Host "进程 $pid 不存在，可能已经停止"
    Remove-Item $pidFile -Force
    exit 1
}

