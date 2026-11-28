$ErrorActionPreference = 'Stop'

$sourceExe = Join-Path $PSScriptRoot 'dist\GCodeLayerEditor.exe'
if (-not (Test-Path -LiteralPath $sourceExe)) {
    throw "Executable not found: $sourceExe. Build the application first."
}

$installDir = Join-Path $env:LOCALAPPDATA 'Programs\GCodeLayerEditor'
New-Item -ItemType Directory -Path $installDir -Force | Out-Null
$exeHash = (Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash.Substring(0, 12)
$installedExe = Join-Path $installDir "GCodeLayerEditor-$exeHash.exe"
Copy-Item -LiteralPath $sourceExe -Destination $installedExe -Force

$classes = 'HKCU:\Software\Classes'
$progId = 'GCodeLayerEditor.gcode'
$progIdKey = Join-Path $classes $progId
$openCommand = '"' + $installedExe + '" "%1"'

New-Item -Path $progIdKey -Force | Out-Null
Set-Item -Path $progIdKey -Value 'G-code Layer Editor file'
New-Item -Path (Join-Path $progIdKey 'DefaultIcon') -Force | Out-Null
Set-Item -Path (Join-Path $progIdKey 'DefaultIcon') -Value ('"' + $installedExe + '",0')
New-Item -Path (Join-Path $progIdKey 'shell\open\command') -Force | Out-Null
Set-Item -Path (Join-Path $progIdKey 'shell\open\command') -Value $openCommand

$extensionKey = Join-Path $classes '.gcode\OpenWithProgids'
New-Item -Path $extensionKey -Force | Out-Null
New-ItemProperty -Path $extensionKey -Name $progId -Value '' -PropertyType String -Force | Out-Null

$registeredAppKey = Join-Path $classes 'Applications\GCodeLayerEditor.exe\shell\open\command'
New-Item -Path $registeredAppKey -Force | Out-Null
Set-Item -Path $registeredAppKey -Value $openCommand
$supportedTypes = Join-Path $classes 'Applications\GCodeLayerEditor.exe\SupportedTypes'
New-Item -Path $supportedTypes -Force | Out-Null
New-ItemProperty -Path $supportedTypes -Name '.gcode' -Value '' -PropertyType String -Force | Out-Null

Write-Host "Installed to $installedExe"
Write-Host 'G-code Layer Editor is now available in Open with for .gcode files.'
