# CYD firmware

## Choose the correct build

| Environment | Use it when |
| --- | --- |
| `cyd_ili9341` | Normal ESP32-2432S028R, usually the single-USB revision |
| `cyd_st7789` | Newer two-USB revision that stays white with ILI9341 |
| `cyd_ili9341_safe` | Same ILI9341 board, but 921,600-baud fallback |
| `cyd_st7789_safe` | Same ST7789 board, but 921,600-baud fallback |

If a safe firmware profile is used, also set `baud = 921600`, `fps = 5`, and
`jpeg_quality = 16` in the Pi config.

## Build and upload in VS Code

1. Install VS Code and its PlatformIO IDE extension.
2. Open this `firmware` folder, not only `src/main.cpp`.
3. Connect the CYD directly to the computer with a data USB cable.
4. Select the environment in the PlatformIO status bar.
5. Click **Build**, then **Upload**.
6. Disconnect the CYD from the computer and reconnect it to the Pi OTG cable.

If upload cannot enter boot mode, hold the CYD `BOOT` button, tap `RST`, start
Upload, and release `BOOT` when PlatformIO begins connecting.

## First boot

The firmware stores a touchscreen calibration in ESP32 Preferences. Follow the
four targets with a stylus. To recalibrate later, hold the touchscreen while
powering on the CYD.

## Protocol and privacy

The firmware receives only rendered JPEG frames, mono PCM audio, and channel
names. It never receives or stores the original IPTV URL or playlist token.
