# PowerShell 脚本：从 .env 文件加载环境变量

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $scriptDir ".env"

if (Test-Path $envFile) {
    Write-Host "Loading environment variables from $envFile"
    
    Get-Content $envFile | ForEach-Object {
        # 跳过注释和空行
        if ($_ -match '^\s*#') { return }
        if ($_ -match '^\s*$') { return }
        
        # 解析 key=value
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            # 移除可能的引号
            $value = $value -replace '^["'']|["'']$', ''
            
            [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
            Write-Host "  Set $key"
        }
    }
    
    Write-Host "Environment variables loaded successfully!"
} else {
    Write-Host "Warning: .env file not found at $envFile"
}

