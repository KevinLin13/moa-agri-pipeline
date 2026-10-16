# Windows Task Scheduler v1 - PowerShell wrapper
# 使用 -DryRun 時，只驗證路徑與交易日期，不啟動 Python 或 Pipeline。
[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

try {
    # 由此腳本所在的 scripts/ 資料夾推導專案根目錄。
    $projectRoot = Split-Path -Path $PSScriptRoot -Parent
    $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    $runDaily = Join-Path $projectRoot 'scripts\run_daily.py'

    # 不依賴 Windows 系統時區，以台灣時間的「當天」為交易日期。
    $taipeiZone = [System.TimeZoneInfo]::FindSystemTimeZoneById('Taipei Standard Time')
    $tradeDate = [System.TimeZoneInfo]::ConvertTime(
        [System.DateTimeOffset]::UtcNow,
        $taipeiZone
    ).ToString('yyyy-MM-dd')

    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        throw "找不到 Python 執行檔：$pythonExe"
    }
    if (-not (Test-Path -LiteralPath $runDaily -PathType Leaf)) {
        throw "找不到 Runtime 腳本：$runDaily"
    }

    Write-Output "Project root: $projectRoot"
    Write-Output "Trade date (Taipei): $tradeDate"
    Write-Output "Python exists: True"
    Write-Output "Script exists: True"

    if ($DryRun) {
        Write-Output "DRY RUN: & `"$pythonExe`" `"$runDaily`" --date $tradeDate"
        exit 0
    }

    # 真實執行時固定工作目錄，避免依賴 Task Scheduler 的預設目錄。
    Set-Location -LiteralPath $projectRoot
    & $pythonExe $runDaily --date $tradeDate

    # 直接把 Python 的退出碼交給排程器；不能把失敗誤報成成功。
    $exitCode = $LASTEXITCODE
    Write-Output "Python exit code: $exitCode"
    exit $exitCode
}
catch {
    [Console]::Error.WriteLine("Scheduled runner error: $($_.Exception.Message)")
    exit 1
}
