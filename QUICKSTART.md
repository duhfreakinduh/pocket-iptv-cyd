# Easy-mode quick start

Do these steps in order. Test on a wall charger before putting the parts on a
battery.

## 1. Buy and identify the parts

Use [SHOPPING_LIST.md](SHOPPING_LIST.md). On the yellow board, confirm the
printed model says `ESP32-2432S028R`. Take a clear photo of both sides before
mounting it; the USB connector and display controller can vary by revision.

## 2. Prepare the Pi microSD card

On a Windows or Mac computer:

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Insert a 32 GB or larger microSD card.
3. Choose **Raspberry Pi Zero 2 W**.
4. Choose **Raspberry Pi OS Lite (64-bit)**.
5. In OS customization set:
   - Hostname: `pocketiptv`
   - A username and a strong password you will remember
   - Your home Wi-Fi now; add your phone hotspot later
   - Wi-Fi country: `US`
   - Enable SSH with password authentication for the first build
6. Write the card, eject it, and insert it into the Pi.

For watching away from home, set your Android hotspot to **2.4 GHz**. The Pi
Zero 2 W does not support a 5 GHz-only hotspot.

## 3. Flash the CYD firmware

Use the prebuilt one-file flasher in [firmware/FLASH_EASY.md](firmware/FLASH_EASY.md).
Start with `ili9341`; use `st7789` only if the screen stays white. Developers
who want to compile it themselves can use PlatformIO as described in
[firmware/README.md](firmware/README.md).

The first boot asks you to touch four crosshairs. Use the plastic stylus and be
precise. Calibration is saved on the ESP32.

## 4. Start and install the Pi software

Power the Pi from a reliable 5 V, 2.5 A wall supply. Wait about 90 seconds, then
find it in your router or use SSH:

```bash
ssh YOUR_USERNAME@pocketiptv.local
```

On the Pi, download this repository, enter it, and run the installer:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd pocket-iptv-cyd
sudo bash pi/install.sh
```

The installer prints a six-digit control-page PIN. Save it. You can show it
again later with:

```bash
sudo pocket-iptv-pin
```

## 5. Connect Pi to screen

1. Power off the Pi.
2. Put the Micro-USB OTG adapter in the Pi port marked **USB**, not `PWR IN`.
3. Connect the CYD's USB data cable to that adapter.
4. Plug the 8-ohm speaker into the CYD's two-pin `SPEAK` connector.
5. Power the Pi through `PWR IN`. The Pi powers the CYD through the data cable.

See [docs/WIRING.md](docs/WIRING.md) before powering it if the labels differ.

## 6. Add a legal playlist

Connect your phone to the same Wi-Fi and open:

```text
http://pocketiptv.local:8080
```

Enter the installer PIN. Paste or upload your authorized `.m3u` playlist. Do
not paste private subscription URLs into a public website or public issue.

The included playlist contains one public test video so you can prove the
hardware works before diagnosing a provider stream.

## 7. Make it portable

After it works for 20 minutes on wall power:

1. Shut the Pi down over SSH with `sudo shutdown -h now`.
2. Move the Pi power cable to a 5 V USB power bank.
3. Turn on your phone's 2.4 GHz hotspot.
4. Power the player and wait 60-90 seconds.
5. Use a vented temporary mount; do not seal the Pi or battery in a hot box.

Expected battery time from a decent 10,000 mAh bank is roughly **4-7 hours**,
depending on conversion losses, brightness, stream complexity, and battery
condition.
