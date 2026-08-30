# Pocket IPTV v2 — Raspberry Pi 4 + touchscreen

This is the easier build. The Raspberry Pi 4 does **everything**: network, decoding, touchscreen UI, audio, playlist management, and video output. There is no ESP32, no CYD firmware, no USB serial bridge, and no 320×240 low-frame-rate conversion.

## Recommended hardware

- Raspberry Pi 4 Model B, 2 GB RAM or better
- 5-inch or 7-inch HDMI touchscreen, ideally 800×480 or 1024×600
- 32 GB or larger A1/A2 microSD card
- Official-quality 5 V / 3 A USB-C power supply for setup
- 10,000 mAh USB power bank with a stable 5 V / 3 A output for portable use
- HDMI cable/adapter that matches the screen
- USB cable from the screen's touch controller to the Pi
- Audio through the screen's HDMI speakers, USB audio, Bluetooth, or the Pi 4 analog jack

## Why this version is better

- Full-motion video instead of the CYD's 6–10 FPS target
- Normal VLC hardware-assisted playback
- Larger capacitive touchscreen options
- 2.4 GHz and 5 GHz Wi-Fi
- Touch channel browser with search and groups
- Favorites
- Previous / play-pause / next controls
- Volume and mute
- M3U import from the touchscreen
- Automatic reconnect attempts
- Automatic startup after the desktop logs in
- No ESP32 flashing or serial troubleshooting

## Install

Use **Raspberry Pi OS with desktop, 64-bit**.

```bash
git clone https://github.com/duhfreakinduh/pocket-iptv-cyd.git
cd pocket-iptv-cyd
bash pi4/install.sh
```

Do **not** run the whole installer with `sudo`; it uses sudo only for the packages that require it.

Launch immediately with:

```bash
~/PocketIPTV/start-pocket-iptv.sh
```

The app also starts automatically the next time the Pi desktop logs in.

## Add your playlist

The installed playlist is:

```text
~/PocketIPTV/channels.m3u
```

The app includes an **Import M3U** button. Put your authorized `.m3u` file on a USB drive, open the button, choose the file, and the app copies it into the PocketIPTV folder.

The included sample contains only a public test stream so you can prove video and audio work before trying a provider playlist.

## Touch controls

- Tap a channel to play it.
- Use **Search channels** to filter by channel or group name.
- Use the group menu to show one category or only favorites.
- Tap **☆ Favorite** to save the current channel.
- Tap **☰ Channels** to hide/show the channel list and make the video area larger.
- Use Prev, Play/Pause, Next, Mute, and the volume slider along the bottom.

Keyboard shortcuts are also available: Space = play/pause, Left/Right = channel change, F11 = fullscreen, Esc = exit fullscreen.

## Hotspot use

The Pi 4 supports both 2.4 GHz and 5 GHz Wi-Fi. Add your phone hotspot in Raspberry Pi OS just like any other Wi-Fi network. Test your home Wi-Fi first, then test the hotspot before putting the player in an enclosure.

## Black video / Wayland fallback

The touchscreen app embeds VLC video in the Qt window. Most Pi 4 desktop installs work normally. If you get controls and audio but the video area stays black, use Raspberry Pi's configuration tool and switch the desktop session to **X11**, reboot, and launch Pocket IPTV again.

On Raspberry Pi OS this can be done with:

```bash
sudo raspi-config
```

Choose the display/window-system option for X11 if your image offers it, then reboot.

## Enclosure notes

Build the enclosure only after the setup works for at least 30 minutes on wall power. Leave ventilation around the Pi 4 and do not trap the power bank against the CPU. A small heatsink or low-profile fan is recommended for long playback sessions.

## Legal / stream support

Pocket IPTV does not provide channels, subscriptions, credentials, DRM bypassing, or piracy features. It is intended for non-DRM streams you are authorized to watch. VLC can play many HLS, HTTP, RTSP, and local media sources, but provider-specific authentication and DRM may still prevent playback.
