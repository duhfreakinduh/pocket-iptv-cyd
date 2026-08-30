# Flash the CYD without compiling

The `prebuilt` folder contains complete ESP32 flash images generated from the
source in this repository. Each image includes the bootloader, partition table,
and application and is written at address `0x0`.

## Windows easy mode

1. Install current [Python for Windows](https://www.python.org/downloads/windows/)
   and check **Add Python to PATH** during setup.
2. Connect the CYD directly to the computer with a data-capable USB cable.
3. Open PowerShell in the downloaded project folder.
4. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\firmware\flash-cyd.ps1
```

That installs the small open-source `esptool` flasher and writes the normal
ILI9341 image. If the display remains white, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\firmware\flash-cyd.ps1 -Variant st7789
```

If automatic port detection chooses the wrong device, unplug other serial
boards or add `-Port COM3` with the COM number shown in Device Manager.

## macOS or Linux

```bash
bash firmware/flash-cyd.sh ili9341
```

Use `st7789`, `ili9341-safe`, or `st7789-safe` as the argument when needed.

## Boot-mode recovery

If the flasher repeats `Connecting...`:

1. Hold the CYD `BOOT` button.
2. Tap and release `RST`.
3. Start the flash command.
4. Release `BOOT` when connection begins.

## Verify the image before flashing

From the `firmware/prebuilt` directory:

```bash
sha256sum -c SHA256SUMS
```
