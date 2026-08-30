param(
    [ValidateSet("ili9341", "st7789", "ili9341-safe", "st7789-safe")]
    [string]$Variant = "ili9341",
    [string]$Port = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Installing/checking the ESP32 flash tool..."
py -m pip install --disable-pip-version-check --user "esptool>=4.5,<6"

$Arguments = @("$ScriptDir\flash_cyd.py", "--variant", $Variant)
if ($Port) {
    $Arguments += @("--port", $Port)
}

Write-Host "Connect the CYD directly to this computer with a data USB cable."
py @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Flashing failed. Hold BOOT, tap RST, retry, then release BOOT when Connecting appears."
}
Write-Host "Firmware installed. Disconnect the CYD and connect it to the Pi OTG cable."
