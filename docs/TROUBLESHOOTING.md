# Troubleshooting

Work from the top. Change one thing at a time.

## Pi never appears on Wi-Fi

- Confirm you flashed **Raspberry Pi OS Lite 64-bit** for Zero 2 W.
- Reopen Raspberry Pi Imager and re-enter the SSID/password.
- Set an Android hotspot to **2.4 GHz**, WPA2/WPA3 compatibility mode if offered.
- Try home Wi-Fi before the phone hotspot.
- Use a strong 5 V supply and short power cable.

## Control page will not open

On the Pi:

```bash
systemctl status pocket-iptv --no-pager
journalctl -u pocket-iptv -n 100 --no-pager
hostname -I
```

Try `http://PI_IP_ADDRESS:8080`. Do not use `https://`.

## CYD has no power

- The OTG adapter must be in the Pi port labeled `USB`, not `PWR IN`.
- Use a known data cable.
- Test the CYD directly from a computer, then reconnect it to the Pi.
- Check for undervoltage: `vcgencmd get_throttled` should normally return
  `throttled=0x0`.

## Screen is white, mirrored, or scrambled

- Verify the board says `ESP32-2432S028R`.
- Flash `cyd_ili9341` first.
- If it remains white, flash `cyd_st7789`.
- Do not use firmware for a 3.2-inch/3.5-inch or capacitive-touch board.

## Pi cannot find the screen

On the Pi:

```bash
lsusb
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
sudo udevadm monitor
```

Reconnect the CYD. A common board appears as a CH340/CH341 USB serial device.
If nothing changes, replace the cable; many cheap cables are charge-only.

## Test video works but provider channels do not

- Confirm the subscription permits use in an external player.
- Try the same exact URL in VLC on a computer on the same network.
- Check whether the URL expired or is locked to a device/IP/user-agent.
- This build does not support Widevine, PlayReady, FairPlay, or app-only DRM.
- View logs without posting the private URL publicly:

```bash
journalctl -u pocket-iptv -f
```

## Picture freezes or audio breaks up

In `/etc/pocket-iptv/config.toml`, try:

```toml
[screen]
baud = 921600
fps = 5
jpeg_quality = 16
```

Then restart:

```bash
sudo systemctl restart pocket-iptv
```

Also add a Pi heatsink, improve ventilation, use wall power, and test a lower
resolution source. `jpeg_quality` uses FFmpeg's scale: a **larger** number means
smaller/lower-quality images.

## No sound

- Confirm the speaker is 8 ohms and plugged into the CYD speaker connector.
- Raise volume from the touchscreen.
- Test the included demo, which has audio.
- Reflash firmware after confirming you chose the original ESP32 profile.
- Tiny speakers are quiet; do not substitute a large 4-ohm speaker.

## Touch is backward or inaccurate

Hold the screen during power-on to force calibration. Touch the four targets
with a plastic stylus. Calibration values are stored in ESP32 preferences.

## Recover the web PIN

```bash
sudo pocket-iptv-pin
```

## Safe reset

Use SSH:

```bash
sudo shutdown -h now
```

Wait for disk activity to stop before removing power.
