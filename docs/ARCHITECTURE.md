# How it works

The Pi Zero 2 W is the decoder. The ESP32 is a display/audio/control terminal.
That split is necessary because an original ESP32 cannot directly decode the
H.264/AAC streams normally found in IPTV playlists.

## Stream pipeline

1. The Pi reads an M3U playlist.
2. FFmpeg opens the selected non-DRM stream once.
3. Video becomes 320x240 MJPEG at the configured frame rate and quality.
4. Audio becomes unsigned 8-bit mono PCM at 16 kHz.
5. The Pi interleaves CRC-protected video, audio, and state packets over the
   CYD's USB-to-UART bridge.
6. The ESP32 decodes each JPEG to the TFT and feeds PCM into its DMA-driven
   built-in DAC on GPIO26, which is connected to the CYD speaker amplifier.
7. Touchscreen commands travel in the opposite USB-serial direction.

## Why USB instead of loose GPIO wires

The USB link powers the CYD, carries data both directions, and avoids soldering.
It also leaves the Pi's Wi-Fi radio dedicated to the phone hotspot. The Pi must
use a Micro-USB **OTG host** adapter in its port labeled `USB`.

## Packet format

All Pi-to-screen packets begin with this 20-byte little-endian header:

| Offset | Size | Field |
| ---: | ---: | --- |
| 0 | 4 | Magic bytes `PIPF` |
| 4 | 1 | Protocol version, currently `1` |
| 5 | 1 | Type: JPEG `1`, PCM `2`, state `3`, heartbeat `4` |
| 6 | 2 | Flags |
| 8 | 4 | Sequence number |
| 12 | 4 | Payload byte length |
| 16 | 4 | Standard CRC-32 of payload |

Touch commands are short return lines beginning `!PIPCMD:`. Bootloader text or
USB noise that does not use that prefix is ignored by the Pi.

## Performance target

The default 2,000,000 baud link has a practical one-way ceiling below 200 kB/s.
The default target stays comfortably below that:

- video: about 70-130 kB/s depending on scene complexity;
- audio: 16 kB/s;
- packet overhead: small.

If the USB bridge is unreliable at 2,000,000 baud, both sides can use 921,600
baud with 5 fps and JPEG quality 16.
