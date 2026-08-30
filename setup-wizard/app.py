"""Local Gradio setup wizard for Pocket IPTV."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gradio as gr

from core import build_bundle, inspect_playlist


def _playlist_text(uploaded: str | None, pasted: str) -> str:
    if pasted.strip():
        return pasted
    if uploaded:
        return Path(uploaded).read_text(encoding="utf-8-sig", errors="replace")
    raise ValueError("Upload an M3U file or paste its text.")


def preview(uploaded: str | None, pasted: str):
    text = _playlist_text(uploaded, pasted)
    report = inspect_playlist(text)
    rows = [
        [index + 1, item.name, item.group, item.scheme.upper(), "Yes" if item.drm_hint else "No"]
        for index, item in enumerate(report.channels[:100])
    ]
    warning_text = "\n".join(f"- {item}" for item in report.warnings)
    status = f"### Found {len(report.channels)} supported channel(s)"
    if warning_text:
        status += f"\n\n{warning_text}"
    if len(report.channels) > 100:
        status += "\n\nPreview shows the first 100 channels."
    return status, rows


def create_bundle(uploaded, pasted, pin, speed, fps, quality, volume):
    text = _playlist_text(uploaded, pasted)
    baud = 2_000_000 if speed.startswith("Fast") else 921_600
    path, resolved_pin, report = build_bundle(
        text,
        pin=pin,
        baud=baud,
        fps=int(fps),
        jpeg_quality=int(quality),
        volume=int(volume),
    )
    status = (
        f"### Private bundle ready\n\n"
        f"Channels: **{len(report.channels)}**  \n"
        f"Control-page PIN: **{resolved_pin}**  \n"
        "Download the ZIP and keep it private."
    )
    return status, str(path)


CSS = """
.gradio-container{max-width:980px!important}
.privacy{border-left:5px solid #ffcc33;padding-left:14px}
"""

with gr.Blocks(title="Pocket IPTV Setup Wizard", analytics_enabled=False) as demo:
    gr.Markdown(
        "# Pocket IPTV — local setup wizard\n"
        "Build a private playlist/config ZIP for your Pi Zero 2 W + CYD player."
    )
    gr.Markdown(
        "**Run this on your own computer for paid/private IPTV playlists.** "
        "Do not paste subscription links into a public Space.",
        elem_classes="privacy",
    )
    with gr.Row():
        uploaded = gr.File(
            label="Upload .m3u or .m3u8",
            file_types=[".m3u", ".m3u8", ".txt"],
            type="filepath",
        )
        pasted = gr.Textbox(
            label="Or paste playlist text",
            lines=9,
            placeholder="#EXTM3U\n#EXTINF:-1,My authorized channel\nhttps://...",
        )
    preview_button = gr.Button("Check playlist", variant="secondary")
    preview_status = gr.Markdown()
    preview_table = gr.Dataframe(
        headers=["#", "Channel", "Group", "Protocol", "DRM hint"],
        datatype=["number", "str", "str", "str", "str"],
        interactive=False,
        wrap=True,
    )
    with gr.Accordion("Player settings", open=True):
        with gr.Row():
            speed = gr.Radio(
                ["Fast — 2,000,000 baud", "Safe — 921,600 baud"],
                value="Fast — 2,000,000 baud",
                label="USB serial speed",
            )
            pin = gr.Textbox(
                label="Control PIN (blank = random)",
                type="password",
                max_length=12,
                placeholder="6 digits",
            )
        with gr.Row():
            fps = gr.Slider(3, 12, value=8, step=1, label="Frames per second")
            quality = gr.Slider(
                6,
                20,
                value=12,
                step=1,
                label="JPEG size/quality (larger = smaller image)",
            )
            volume = gr.Slider(0, 100, value=65, step=5, label="Starting volume")
    build_button = gr.Button("Build private configuration ZIP", variant="primary")
    build_status = gr.Markdown()
    download = gr.File(label="Download", interactive=False)

    preview_button.click(
        fn=preview,
        inputs=[uploaded, pasted],
        outputs=[preview_status, preview_table],
        api_visibility="private",
    )
    build_button.click(
        fn=create_bundle,
        inputs=[uploaded, pasted, pin, speed, fps, quality, volume],
        outputs=[build_status, download],
        api_visibility="private",
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        inbrowser=True,
        show_error=True,
        css=CSS,
    )
