# Shopping list — recommended Pi 4 touchscreen build

Prices change, so use the ranges below as a sanity check rather than a guaranteed price. The key upgrade is that you no longer need an ESP32/CYD, OTG adapter, serial data cable, or tiny CYD speaker.

## Required

| Qty | Part | Good target | Notes |
| ---: | --- | --- | --- |
| 1 | Raspberry Pi 4 Model B | 2 GB RAM or better | 2 GB is enough for the dedicated player; 4 GB is fine if the price is close |
| 1 | 5-inch or 7-inch HDMI touchscreen | 800×480 or 1024×600, capacitive touch | A 5-inch screen keeps the build genuinely portable; 7-inch is easier to use |
| 1 | microSD card | 32 GB or 64 GB, genuine A1/A2 | Buy from a reputable retailer |
| 1 | Pi 4 wall power supply | stable 5 V / 3 A USB-C | Use wall power for the entire first build |
| 1 | HDMI cable/adapter | micro-HDMI from Pi 4 to the screen's HDMI input | Match the exact connector on your display |
| 1 | USB touch cable | screen touch controller to a Pi USB port | Often included with the screen |

Official Pi 4 product page: https://www.raspberrypi.com/products/raspberry-pi-4-model-b/

## Portable-power add-ons

| Qty | Part | Good target | Why |
| ---: | --- | --- | --- |
| 1 | USB power bank | 10,000 mAh+, stable 5 V / 3 A output | Powers the Pi away from an outlet |
| 1 | Short USB-C power cable | low-resistance cable | Helps avoid undervoltage warnings |
| 1 | Small Pi 4 heatsink or fan | low-profile | Video playback can keep the SoC warm |

Some touchscreens need their own 5 V power input. If yours does, make sure the power bank has enough outputs and total current capacity for both the Pi and screen.

## Audio choices

Use whichever is easiest for your enclosure:

- speakers built into the HDMI display
- a small USB speaker
- Bluetooth speaker/headphones
- wired headphones or a small powered speaker from the Pi 4 analog jack

## Expected budget

A realistic new-parts target is roughly:

- Pi 4 board: **$35–$60** depending on RAM and seller
- 5–7 inch touchscreen: **$30–$70**
- microSD: **$8–$15**
- wall supply/cables: **$15–$25**
- portable power bank: **$20–$40** if you do not already own one
- cooling/enclosure extras: **$5–$20**

If you already own a Pi 4, card, power bank, or cables, the project gets much cheaper.

## Best-size recommendation

For the mini portable TV idea, the sweet spot is:

**Raspberry Pi 4 + 5-inch 800×480 or 1024×600 capacitive HDMI touchscreen + 10,000 mAh power bank.**

It is small enough to carry, but large enough that the on-screen channel list and controls are usable with a finger.

## Do not accidentally buy

- Raspberry Pi Pico/Pico W — it cannot run this Linux/VLC application.
- Original single-core Pi Zero W — too slow for this version.
- A display that is SPI-only unless you specifically want to configure Linux framebuffer drivers.
- A resistive touchscreen if you want phone-like finger control.
- A charge-only USB cable for the touchscreen's USB connection.
- A weak 5 V / 1 A or 2 A supply for the Pi 4.

## Legacy CYD hardware

The old Raspberry Pi Zero 2 W + ESP32-2432S028R parts are only needed for the legacy version in `pi/` and `firmware/`. They are **not** needed for the new recommended build.
