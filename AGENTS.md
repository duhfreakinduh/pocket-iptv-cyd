# AI / Contributor Guide

Keep this project focused on a reliable, legal, low-friction Raspberry Pi/embedded IPTV player. AI is optional and should improve discovery, setup, or troubleshooting without becoming a requirement for playback.

## Priorities
1. Playback must work without AI.
2. Never bundle pirated/private playlist credentials, stolen streams, or secrets.
3. Treat playlist URLs, credentials, and viewing history as private data.
4. If AI is added for channel search, playlist cleanup, or troubleshooting, use explicit user action and provide a deterministic fallback.
5. Avoid exposing API/model tokens in client-side or committed configuration.
6. Keep Raspberry Pi 4 resource use conservative and startup recovery simple.
7. Validate M3U input, reject malformed entries safely, and handle dead streams cleanly.
8. Preserve LEGAL_AND_SAFETY.md and document supported sources/protocols.

## Before merging
- Test startup with no network and with an invalid playlist.
- Test one known-good legal/public stream.
- Verify no credentials are logged.
- Confirm playback does not depend on AI.
- Check install/quick-start steps on a clean Pi image when practical.
