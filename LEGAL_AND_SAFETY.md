# Legal, privacy, and safety

## Content rights

This project is a player, not a source of television service. It includes no
commercial channels, stolen playlists, decryption keys, account bypasses, or
DRM circumvention. Use only:

- streams you own;
- a playlist supplied by a service you are authorized to use; or
- public/test streams whose publisher permits playback.

Do not publish a private M3U file. Provider URLs commonly contain usernames,
passwords, or bearer tokens. The Pi web page deliberately hides channel URLs
after upload. The Gradio setup wizard is intended to run on your own computer,
not as a public Space when using private credentials.

## Network privacy

- Use a strong phone-hotspot password.
- Change the Pi's default SSH password and disable password SSH after setup if
  you do not need it.
- Keep the six-digit player control PIN private.
- Plain `http://` streams are not encrypted. Prefer `https://` where supported.
- The local web controller is for a trusted home/hotspot network; do not expose
  port 8080 to the internet or add router port forwarding.

## Electrical and heat safety

- Use a protected, commercially made USB power bank.
- Do not connect a bare lithium cell directly to either board.
- Do not charge or operate a damaged, swollen, wet, or unusually hot battery.
- Keep the Pi and battery ventilated. Video decoding can warm the Pi.
- Power off before plugging or unplugging the CYD speaker.
- Connect the CYD to the Pi's `USB` port and power the Pi through `PWR IN`.
- Test for at least 20 minutes on a wall supply before using a battery.
- Do not leave an unfinished electronics build charging unattended.
