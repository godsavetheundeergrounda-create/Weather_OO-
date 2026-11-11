$ErrorActionPreference = 'Stop'

try {
    $projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $launcherPath = Join-Path $projectDir 'start.bat'
    $iconPath = Join-Path $projectDir 'weather-sun.ico'

    if (-not (Test-Path -LiteralPath $launcherPath)) {
        throw "start.bat was not found in: $projectDir"
    }
    if (-not (Test-Path -LiteralPath $iconPath)) {
        throw "weather-sun.ico was not found in: $projectDir"
    }

    $desktopPath = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktopPath 'Weather Aggregator.lnk'

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $launcherPath
    $shortcut.WorkingDirectory = $projectDir
    $shortcut.IconLocation = "$iconPath,0"
    $shortcut.Description = 'Launch Weather Aggregator'
    $shortcut.WindowStyle = 1
    $shortcut.Save()

    Write-Host ''
    Write-Host 'Desktop shortcut created successfully:' -ForegroundColor Green
    Write-Host $shortcutPath
    Write-Host 'You can now launch Weather Aggregator using the sun icon.'
    $exitCode = 0
}
catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}

Write-Host ''
Read-Host 'Press Enter to close'
exit $exitCode
