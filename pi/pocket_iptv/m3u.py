"""Small, dependency-free M3U parser for ordinary IPTV playlists."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
from urllib.parse import parse_qsl, unquote, urlparse

ATTRIBUTE_RE = re.compile(r"([A-Za-z0-9_-]+)=(?:\"([^\"]*)\"|([^\s,]+))")
SUPPORTED_SCHEMES = {"http", "https", "rtsp", "rtmp", "udp", "file"}


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    group: str = "Other"
    logo: str = ""
    tvg_id: str = ""
    user_agent: str = ""
    referrer: str = ""
    drm_hint: bool = False

    @property
    def scheme(self) -> str:
        return urlparse(self.url).scheme.lower()


def _attributes(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in ATTRIBUTE_RE.finditer(text):
        values[match.group(1).lower()] = match.group(2) or match.group(3) or ""
    return values


def _split_url_options(value: str) -> tuple[str, dict[str, str]]:
    """Handle the common URL|User-Agent=x&Referer=y playlist extension."""
    if "|" not in value:
        return value.strip(), {}
    url, raw_options = value.split("|", 1)
    options = {key.lower(): unquote(val) for key, val in parse_qsl(raw_options)}
    return url.strip(), options


def _fallback_name(url: str, number: int) -> str:
    parsed = urlparse(url)
    tail = Path(parsed.path).name
    return tail or parsed.hostname or f"Channel {number}"


def parse_m3u(text: str, *, allow_unsupported: bool = False) -> list[Channel]:
    channels: list[Channel] = []
    pending: Channel | None = None
    pending_group = ""
    pending_agent = ""
    pending_referrer = ""
    drm_hint = False

    for original in text.lstrip("\ufeff").splitlines():
        line = original.strip()
        if not line:
            continue

        upper = line.upper()
        if upper.startswith("#EXTINF:"):
            details = line.split(":", 1)[1]
            left, comma, display_name = details.partition(",")
            attrs = _attributes(left)
            pending = Channel(
                name=(display_name.strip() if comma else "") or attrs.get("tvg-name", ""),
                url="",
                group=attrs.get("group-title", "") or pending_group or "Other",
                logo=attrs.get("tvg-logo", ""),
                tvg_id=attrs.get("tvg-id", ""),
            )
            pending_group = ""
            pending_agent = ""
            pending_referrer = ""
            drm_hint = False
            continue

        if upper.startswith("#EXTGRP:"):
            pending_group = line.split(":", 1)[1].strip()
            if pending is not None:
                pending = replace(pending, group=pending_group or "Other")
            continue

        if upper.startswith("#EXTVLCOPT:"):
            option = line.split(":", 1)[1]
            key, _, value = option.partition("=")
            key = key.lower().strip()
            if key in {"http-user-agent", "user-agent"}:
                pending_agent = value.strip()
            elif key in {"http-referrer", "http-referer", "referer", "referrer"}:
                pending_referrer = value.strip()
            continue

        if upper.startswith("#KODIPROP:") or upper.startswith("#EXT-X-KEY:"):
            if "license" in line.lower() or "widevine" in line.lower():
                drm_hint = True
            continue

        if line.startswith("#"):
            continue

        url, options = _split_url_options(line)
        scheme = urlparse(url).scheme.lower()
        if scheme not in SUPPORTED_SCHEMES and not allow_unsupported:
            pending = None
            continue

        number = len(channels) + 1
        base = pending or Channel(name="", url="", group=pending_group or "Other")
        channel = replace(
            base,
            name=base.name or _fallback_name(url, number),
            url=url,
            user_agent=(
                pending_agent
                or options.get("user-agent", "")
                or options.get("http-user-agent", "")
            ),
            referrer=(
                pending_referrer
                or options.get("referer", "")
                or options.get("referrer", "")
            ),
            drm_hint=drm_hint,
        )
        channels.append(channel)
        pending = None
        pending_group = ""
        pending_agent = ""
        pending_referrer = ""
        drm_hint = False

    return channels


def load_playlist(path: str | Path) -> list[Channel]:
    return parse_m3u(Path(path).read_text(encoding="utf-8-sig"))
