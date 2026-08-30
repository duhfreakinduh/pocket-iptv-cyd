#!/usr/bin/env python3
"""Build a browser-tested U.S. HLS channel list for Quick Launch TV.

This does not proxy or rebroadcast video. It checks public playlist URLs from
Free-TV and IPTV-org, keeps HTTPS HLS manifests that respond with browser CORS,
and writes static metadata for the GitHub Pages app.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ORIGIN = "https://duhfreakinduh.github.io"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Mobile Safari/537.36"
)
TIMEOUT = 7
MAX_READ = 768 * 1024
WORKERS = 48
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

SOURCES = [
    {
        "name": "Free-TV",
        "url": "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_usa.m3u8",
        "preferred": True,
    },
    {
        "name": "IPTV-org",
        "url": "https://iptv-org.github.io/iptv/countries/us.m3u",
        "preferred": False,
    },
]


def request_text(url: str) -> tuple[str, str, int]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Origin": ORIGIN,
            "Accept": "application/vnd.apple.mpegurl,application/x-mpegURL,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        status = int(getattr(response, "status", 200) or 200)
        body = response.read(MAX_READ).decode("utf-8", errors="replace")
        cors = response.headers.get("Access-Control-Allow-Origin", "")
        return body, cors, status


def cors_allows_browser(value: str) -> bool:
    value = (value or "").strip()
    return value == "*" or ORIGIN in value


def parse_m3u(text: str, source: dict) -> list[dict]:
    channels: list[dict] = []
    meta: dict | None = None
    for raw in text.replace("\r", "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(ATTR_RE.findall(line))
            comma = line.find(",")
            meta = {
                "name": line[comma + 1 :].strip() if comma >= 0 else "Channel",
                "group": attrs.get("group-title") or "Other",
                "logo": attrs.get("tvg-logo") or "",
                "id": attrs.get("tvg-id") or "",
                "source": source["name"],
                "preferred": bool(source.get("preferred")),
            }
            continue
        if line.startswith("#"):
            continue
        if line.lower().startswith("https://") and re.search(r"\.m3u8(?:[?#]|$)", line, re.I):
            item = meta or {
                "name": f"Channel {len(channels) + 1}",
                "group": "Other",
                "logo": "",
                "id": "",
                "source": source["name"],
                "preferred": bool(source.get("preferred")),
            }
            channels.append({**item, "url": line, "kind": "hls"})
            meta = None
    return channels


def normalized_key(channel: dict) -> str:
    raw = channel.get("id") or channel.get("name") or channel.get("url") or ""
    return re.sub(r"\s+", " ", raw).strip().lower()


def dedupe(channels: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    for channel in channels:
        key = normalized_key(channel)
        if not key:
            continue
        old = chosen.get(key)
        if old is None or (channel.get("preferred") and not old.get("preferred")):
            chosen[key] = channel
    return sorted(chosen.values(), key=lambda c: (c.get("name") or "").lower())


def first_uri(playlist: str) -> str | None:
    for raw in playlist.replace("\r", "").split("\n"):
        line = raw.strip()
        if line and not line.startswith("#"):
            return line
    return None


def validate(channel: dict) -> dict | None:
    url = channel["url"]
    try:
        body, cors, status = request_text(url)
        if status < 200 or status >= 400 or "#EXTM3U" not in body[:4096]:
            return None
        if not cors_allows_browser(cors):
            return None

        # For a master playlist, also test the first child playlist. This catches
        # many token/CORS failures before the channel reaches the phone.
        if "#EXT-X-STREAM-INF" in body:
            child = first_uri(body)
            if child:
                child_url = urllib.parse.urljoin(url, child)
                child_body, child_cors, child_status = request_text(child_url)
                if (
                    child_status < 200
                    or child_status >= 400
                    or "#EXTM3U" not in child_body[:4096]
                    or not cors_allows_browser(child_cors)
                ):
                    return None

        return {
            "name": channel.get("name") or "Channel",
            "group": channel.get("group") or "Other",
            "logo": channel.get("logo") or "",
            "id": channel.get("id") or "",
            "source": channel.get("source") or "Directory",
            "url": url,
            "kind": "hls",
            "tested": True,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return None


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "web/channels.json")
    candidates: list[dict] = []
    source_counts: dict[str, int] = {}

    for source in SOURCES:
        try:
            text, _, _ = request_text(source["url"])
            parsed = parse_m3u(text, source)
            candidates.extend(parsed)
            source_counts[source["name"]] = len(parsed)
            print(f"{source['name']}: {len(parsed)} HTTPS HLS candidates")
        except Exception as exc:  # Keep deploy alive if one directory is temporarily down.
            source_counts[source["name"]] = 0
            print(f"warning: could not load {source['name']}: {exc}")

    candidates = dedupe(candidates)
    print(f"Validating {len(candidates)} unique candidates with {WORKERS} workers...")
    started = time.time()
    working: list[dict] = []

    if candidates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for result in pool.map(validate, candidates):
                if result:
                    working.append(result)

    working.sort(key=lambda c: ((c.get("group") or "").lower(), (c.get("name") or "").lower()))
    payload = {
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "origin": ORIGIN,
        "candidate_count": len(candidates),
        "working_count": len(working),
        "sources": source_counts,
        "channels": working,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(working)} browser-tested channels to {output} in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
