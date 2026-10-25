# Windows Task Scheduler v1 - PowerShell wrapper
# 使用 -DryRun 時，只驗證路徑與交易日期，不啟動 Python 或 Pipeline。
[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$RequestedTradeDate,
    [ValidateSet('moa_agri_sched_test')]
    [string]$TargetDatabase
)

$ErrorActionPreference = 'Stop'

try {
    # 由此腳本所在的 scripts/ 資料夾推導專案根目錄。
    $projectRoot = Split-Path -Path $PSScriptRoot -Parent
    $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    $runDaily = Join-Path $projectRoot 'scripts\run_daily.py'

    # 可指定測試交易日期；未指定時，仍使用台灣時間的當天。
    if ($PSBoundParameters.ContainsKey('RequestedTradeDate')) {
        try {
            $parsedTradeDate = [datetime]::ParseExact(
                $RequestedTradeDate,
                'yyyy-MM-dd',
                [System.Globalization.CultureInfo]::InvariantCulture
            )
        }
        catch {
            throw 'RequestedTradeDate 必須是有效的 YYYY-MM-DD 日期'
        }
        $tradeDate = $parsedTradeDate.ToString('yyyy-MM-dd')
        $dateSource = 'explicit'
    }
    else {
        $taipeiZone = [System.TimeZoneInfo]::FindSystemTimeZoneById('Taipei Standard Time')
        $tradeDate = [System.TimeZoneInfo]::ConvertTime(
            [System.DateTimeOffset]::UtcNow,
            $taipeiZone
        ).ToString('yyyy-MM-dd')
        $dateSource = 'Taipei today'
    }

    # 測試模式：只在這個 PowerShell 子程序及其 Python 子程序中指定資料庫。
    # 未指定 TargetDatabase 時維持原本的連線環境。
    if ($PSBoundParameters.ContainsKey('TargetDatabase')) {
        $env:PGHOST = 'localhost'
        $env:PGPORT = '5432'
        $env:PGUSER = 'postgres'
        $env:PGDATABASE = $TargetDatabase
    }

    # 本機真實排程 PoC 採用 fail-closed：未明確指定測試庫就拒絕。
    # 避免預設 PGDATABASE 指向原本的 moa_agri。
    if (-not $DryRun -and -not $PSBoundParameters.ContainsKey('TargetDatabase')) {
        throw '本機 PoC 真實執行必須明確提供 -TargetDatabase moa_agri_sched_test'
    }

    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        throw "找不到 Python 執行檔：$pythonExe"
    }
    if (-not (Test-Path -LiteralPath $runDaily -PathType Leaf)) {
        throw "找不到 Runtime 腳本：$runDaily"
    }

    Write-Output "Project root: $projectRoot"
    Write-Output "Trade date ($dateSource): $tradeDate"
    if ($PSBoundParameters.ContainsKey('TargetDatabase')) {
        Write-Output "Target database (explicit): $env:PGDATABASE"
    }
    else {
        Write-Output "Target database: inherited from PostgreSQL runtime configuration"
    }
    Write-Output "Python exists: True"
    Write-Output "Script exists: True"

    if ($DryRun) {
        $expectedDatabaseArg = ''
        if ($PSBoundParameters.ContainsKey('TargetDatabase')) {
            $expectedDatabaseArg = " --expected-database $TargetDatabase"
        }
        Write-Output "DRY RUN: & `"$pythonExe`" `"$runDaily`" --date $tradeDate$expectedDatabaseArg"
        exit 0
    }

    # 真實執行時固定工作目錄，避免依賴 Task Scheduler 的預設目錄。
    Set-Location -LiteralPath $projectRoot
    & $pythonExe $runDaily --date $tradeDate --expected-database $TargetDatabase

    # 直接把 Python 的退出碼交給排程器；不能把失敗誤報成成功。
    $exitCode = $LASTEXITCODE
    Write-Output "Python exit code: $exitCode"
    exit $exitCode
}
catch {
    [Console]::Error.WriteLine("Scheduled runner error: $($_.Exception.Message)")
    exit 1
}