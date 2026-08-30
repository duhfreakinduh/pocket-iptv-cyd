# Easy-mode quick start — Raspberry Pi 4 + touchscreen

This is the recommended build. The Raspberry Pi 4 runs the screen, video, audio, playlist, and touch controls by itself.

## 1. Build the hardware

Connect:

1. Raspberry Pi 4 to the touchscreen with HDMI.
2. Touchscreen USB touch cable to a Pi USB port.
3. Pi to a reliable 5 V / 3 A USB-C wall supply.
4. Screen to its required power source.
5. Optional speakers/headphones through HDMI, USB, Bluetooth, or the Pi 4 analog jack.

Do the first setup on wall power, not a battery.

## 2. Prepare the microSD card

On a Windows or Mac computer:

1. Install Raspberry Pi Imager.
2. Insert a 32 GB or larger microSD card.
3. Choose **Raspberry Pi 4**.
4. Choose **Raspberry Pi OS with desktop, 64-bit**.
5. In OS customization set your username/password, home Wi-Fi, locale, and optionally enable SSH.
6. Write the card and boot the Pi.

Finish the normal Raspberry Pi desktop setup and confirm the touchscreen works before installing Pocket IPTV.

## 3. Install Pocket IPTV

Open Terminal on the Pi and run:

```bash
git clone https://github.com/duhfreakinduh/pocket-iptv-cyd.git
cd pocket-iptv-cyd
bash pi4/install.sh
```

The installer adds VLC, Python, PyQt5, the touchscreen app, a sample playlist, and an autostart launcher.

## 4. Launch it

Run:

```bash
~/PocketIPTV/start-pocket-iptv.sh
```

The app opens full-screen. It will also open automatically after the Pi desktop logs in on future boots.

## 5. Test video and audio

The included sample playlist has one public test stream. Tap it and make sure you have:

- moving video
- audio
- working touch controls
- working volume slider
- stable playback for at least 20–30 minutes

If you have audio but a black video box, see the X11 fallback in [pi4/README.md](pi4/README.md).

## 6. Add your own authorized M3U playlist

The easiest method is:

1. Put your `.m3u` playlist on a USB flash drive.
2. Tap **Import M3U** in Pocket IPTV.
3. Pick the file.
4. Pocket IPTV copies it to `~/PocketIPTV/channels.m3u` and reloads it.

You can then search channels, filter by group, and mark favorites.

## 7. Add your phone hotspot

The Pi 4 supports 2.4 GHz and 5 GHz Wi-Fi. Add your phone hotspot from Raspberry Pi OS Wi-Fi settings, disconnect home Wi-Fi, and prove the player works through the hotspot before calling the build portable.

## 8. Make it portable

Only after the wall-powered build is stable:

1. Shut the Pi down normally.
2. Move the Pi to a USB power bank capable of stable 5 V / 3 A output.
3. Power the touchscreen as required by its manufacturer.
4. Turn on your phone hotspot.
5. Boot and test again.

Do not seal the Pi 4 and battery into a hot, unvented enclosure. Add a heatsink or small fan for long playback sessions.

## Legacy version

The old Pi Zero 2 W + ESP32 Cheap Yellow Display instructions are still preserved in the repository, but they are no longer the recommended path. The Pi 4 touchscreen build removes the ESP32 flashing, serial link, low-frame-rate JPEG transport, and special speaker wiring.
