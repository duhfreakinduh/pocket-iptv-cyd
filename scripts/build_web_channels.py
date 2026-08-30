#!/usr/bin/env python3
"""Build a browser-tested U.S. HLS channel list for Quick Launch TV.

This does not proxy or rebroadcast video. It checks public playlist URLs from
Free-TV and IPTV-org, follows master playlists, verifies browser CORS on the
media playlist and actual media/key/init requests, and writes static metadata
for the GitHub Pages app.
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
PROBE_READ = 4096
WORKERS = 40
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
URI_RE = re.compile(r'URI="([^"]+)"', re.I)

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


def headers(accept: str = "*/*", referer: str | None = None) -> dict[str, str]:
    out = {
        "User-Agent": USER_AGENT,
        "Origin": ORIGIN,
        "Accept": accept,
        "Cache-Control": "no-cache",
    }
    if referer:
        out["Referer"] = referer
    return out


def request_text(url: str, referer: str | None = None) -> tuple[str, str, int, str]:
    req = urllib.request.Request(
        url,
        headers=headers(
            "application/vnd.apple.mpegurl,application/x-mpegURL,text/plain,*/*",
            referer,
        ),
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        status = int(getattr(response, "status", 200) or 200)
        body = response.read(MAX_READ).decode("utf-8", errors="replace")
        cors = response.headers.get("Access-Control-Allow-Origin", "")
        final_url = response.geturl() or url
        return body, cors, status, final_url


def request_probe(url: str, referer: str | None = None) -> tuple[str, int, str, int]:
    req = urllib.request.Request(url, headers=headers("*/*", referer))
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        status = int(getattr(response, "status", 200) or 200)
        chunk = response.read(PROBE_READ)
        cors = response.headers.get("Access-Control-Allow-Origin", "")
        final_url = response.geturl() or url
        return cors, status, final_url, len(chunk)


def cors_allows_browser(value: str) -> bool:
    value = (value or "").strip()
    return value == "*" or ORIGIN in value


def good_response(status: int) -> bool:
    return 200 <= status < 400


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


def lines(playlist: str) -> list[str]:
    return [raw.strip() for raw in playlist.replace("\r", "").split("\n") if raw.strip()]


def master_child(playlist: str) -> str | None:
    rows = lines(playlist)
    for i, line in enumerate(rows):
        if line.startswith("#EXT-X-STREAM-INF"):
            for candidate in rows[i + 1 :]:
                if not candidate.startswith("#"):
                    return candidate
    return None


def first_media_uri(playlist: str) -> str | None:
    for line in lines(playlist):
        if not line.startswith("#"):
            return line
    for line in lines(playlist):
        if line.startswith("#EXT-X-PART:") or line.startswith("#EXT-X-PRELOAD-HINT:"):
            match = URI_RE.search(line)
            if match:
                return match.group(1)
    return None


def tagged_uri(playlist: str, tag: str) -> str | None:
    for line in lines(playlist):
        if line.startswith(tag):
            if tag == "#EXT-X-KEY:" and "METHOD=NONE" in line.upper():
                continue
            match = URI_RE.search(line)
            if match:
                return match.group(1)
    return None


def probe_browser_resource(url: str, referer: str) -> bool:
    cors, status, _final, size = request_probe(url, referer)
    return good_response(status) and size > 0 and cors_allows_browser(cors)


def resolve_media_playlist(url: str) -> tuple[str, str] | None:
    """Return (media_playlist_body, final_media_playlist_url)."""
    current = url
    referer: str | None = None
    for _ in range(4):
        body, cors, status, final_url = request_text(current, referer)
        if not good_response(status) or "#EXTM3U" not in body[:4096]:
            return None
        if not cors_allows_browser(cors):
            return None
        child = master_child(body) if "#EXT-X-STREAM-INF" in body else None
        if not child:
            return body, final_url
        referer = final_url
        current = urllib.parse.urljoin(final_url, child)
    return None


def validate(channel: dict) -> dict | None:
    url = channel["url"]
    try:
        resolved = resolve_media_playlist(url)
        if not resolved:
            return None
        media_body, media_url = resolved

        # Hls.js has to fetch these cross-origin too. Testing only the .m3u8
        # produces lots of false positives, so verify the real media path.
        init_uri = tagged_uri(media_body, "#EXT-X-MAP:")
        if init_uri and not probe_browser_resource(urllib.parse.urljoin(media_url, init_uri), media_url):
            return None

        key_uri = tagged_uri(media_body, "#EXT-X-KEY:")
        if key_uri and not probe_browser_resource(urllib.parse.urljoin(media_url, key_uri), media_url):
            return None

        segment_uri = first_media_uri(media_body)
        if not segment_uri:
            return None
        if not probe_browser_resource(urllib.parse.urljoin(media_url, segment_uri), media_url):
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
            "media_tested": True,
        }
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        ValueError,
    ):
        return None


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "web/channels.json")
    candidates: list[dict] = []
    source_counts: dict[str, int] = {}

    for source in SOURCES:
        try:
            text, _, _, _ = request_text(source["url"])
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
        "version": 2,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "origin": ORIGIN,
        "validation": "manifest+media-playlist+first-segment+key/init-when-present",
        "candidate_count": len(candidates),
        "working_count": len(working),
        "sources": source_counts,
        "channels": working,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"Wrote {len(working)} media-tested browser channels to {output} "
        f"in {time.time() - started:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
