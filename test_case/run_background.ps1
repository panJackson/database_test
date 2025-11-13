# PowerShell 脚本：后台运行 test_text2sql.py 并保存日志

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$testScript = Join-Path $scriptDir "test_text2sql.py"
$logDir = Join-Path $scriptDir "logs"
$pidFile = Join-Path $scriptDir "test_text2sql.pid"

# 创建日志目录
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

# 生成日志文件名
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "test_text2sql_$timestamp.log"

# 检查是否已经在运行
if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile
    $process = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "测试脚本已经在运行中 (PID: $oldPid)"
        Write-Host "日志文件: $logDir\test_text2sql_*.log"
        exit 1
    } else {
        Remove-Item $pidFile -Force
    }
}

# 切换到项目根目录
Set-Location $projectRoot

# 启动后台作业
Write-Host "正在启动后台测试..."
Write-Host "日志文件: $logFile"
Write-Host "PID 文件: $pidFile"

# 使用 Start-Process 在后台运行
$process = Start-Process -FilePath "python" `
    -ArgumentList $testScript `
    -NoNewWindow `
    -PassThru `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $logFile

# 保存 PID
$process.Id | Out-File -FilePath $pidFile -Encoding utf8

Write-Host ""
Write-Host "测试已在后台启动"
Write-Host "进程 ID (PID): $($process.Id)"
Write-Host "日志文件: $logFile"
Write-Host ""
Write-Host "查看日志命令:"
Write-Host "  Get-Content $logFile -Wait -Tail 50"
Write-Host ""
Write-Host "停止测试命令:"
Write-Host "  .\stop_background.ps1"

