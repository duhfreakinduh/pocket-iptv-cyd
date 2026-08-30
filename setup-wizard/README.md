# Local Gradio setup wizard

This optional interface uses Hugging Face Gradio to inspect an M3U playlist and
create a private Pi configuration ZIP without exposing channel URLs in its
preview.

## Run locally

From the repository root:

```bash
python3 -m venv .venv-wizard
.venv-wizard/bin/pip install -r setup-wizard/requirements.txt
.venv-wizard/bin/python setup-wizard/app.py
```

On Windows PowerShell, activate/run the equivalent executables under
`.venv-wizard\Scripts\`.

The browser opens on `127.0.0.1`, which is accessible only from the computer
running it.

## Why this is not automatically published as a public Space

Paid IPTV M3U URLs often embed account credentials. A public hosted form would
send those URLs to another server. Keep the wizard local for private playlists.
The app is Gradio-compatible if you want to host a copy for non-secret public
test streams, but do not use that hosted copy for subscription credentials.
