# Shopping list

Prices and availability change. These were checked on **August 30, 2026**.
Choose the exact model numbers; look-alike boards are the biggest source of
failed builds.

## Required

| Qty | Part | Expected price | Buy/check |
| ---: | --- | ---: | --- |
| 1 | Raspberry Pi Zero 2 W | $15-$21 | [Official specs/buy links](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/), [CanaKit listing](https://www.canakit.com/raspberry-pi-zero-2-w.html), [PiShop pre-soldered option](https://www.pishop.us/product/raspberry-pi-zero-2w-with-headers/) |
| 1 | ESP32-2432S028R 2.8-inch resistive CYD, ILI9341 preferred | $14-$22 fast US shipping; $8-$15 slower marketplace | [Amazon DIYmalls listing](https://www.amazon.com/DIYmalls-ESP32-2432S028R-Resistive-ESP-WROOM-32-Development/dp/B0CG2WQGP9), [board buying guide](https://makeradvisor.com/tools/cyd-cheap-yellow-display-esp32-2432s028r/) |
| 1 | 32 GB or 64 GB genuine A1 microSD card | $8-$15 | Buy locally from a known retailer; avoid suspicious marketplace cards |
| 1 | Micro-USB OTG male to USB-A female adapter | $3-$10 | [PiShop $3.95 cable](https://www.pishop.us/product/usb-otg-host-cable-microb-otg-male-to-a-female/), [Adafruit tiny adapter](https://www.adafruit.com/product/2910) |
| 1 | USB data cable matching the CYD: USB-C or Micro-USB by revision | $0-$8 | Often included; it must carry data, not charge-only |
| 1 | 8-ohm, 0.5-1 W mini speaker with **2-pin 1.25 mm** plug | $3-$10 | [CYD speaker guidance](https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display/blob/main/ADDONS.md), [example speaker](https://www.amazon.com/AOICRIE-Full-Range-Advertising-JST-PH2-5mm-2-Electronic/dp/B0F48J1XFG) |
| 1 | 5 V USB power bank, 10,000 mAh, 2 A or better output | $15-$30 | A known-brand bank you already own is fine |
| 1 | Micro-USB power cable for the Pi | $0-$8 | Use a short, thicker cable to reduce voltage drop |

## Strongly recommended

| Qty | Part | Why |
| ---: | --- | --- |
| 1 | Small Pi Zero 2 W stick-on heatsink | FFmpeg keeps the CPU busy; a heatsink reduces throttling |
| 1 | 5 V, 2.5 A wall supply | Use wall power for the first build and troubleshooting |
| 1 | USB microSD reader | Needed if the computer has no card slot |
| 1 | Plastic CYD stylus | Resistive touch calibrates better with a point than a finger |
| 1 | Short hook-and-loop strap or removable mounting tape | Temporary enclosure for the first successful weekend |

## Budget

- If you own a card, battery, cables, and speaker: about **$35-$50**.
- Buying every required item new: about **$60-$95**.
- Do not pay Pi-scalper bundle prices. The Zero 2 W's official launch price was
  $15, and normal US board listings remain close to that range.

## Do not accidentally buy

- Original Raspberry Pi Zero W: it is too slow for this build.
- Raspberry Pi Pico/Pico W: it cannot run Linux or FFmpeg.
- ESP32-2432S032, 3.5-inch, capacitive, or ESP32-S3 display unless you are ready
  to create a new firmware profile.
- A charge-only USB cable.
- A bare Li-ion/LiPo cell without a protected charging/power circuit.
- A 4-ohm high-power speaker; use the small 8-ohm speaker specified above.
