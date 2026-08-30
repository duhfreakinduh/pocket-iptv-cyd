"""Small XMLTV/EPG helper used by Pocket IPTV v2.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional
import xml.etree.ElementTree as ET


@dataclass
class Programme:
    channel_id: str
    title: str
    start: datetime
    stop: datetime
    desc: str = ""


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _time(value: str) -> Optional[datetime]:
    value = value.strip()
    if not value:
        return None
    parts = value.split()
    stamp = parts[0]
    offset = parts[1] if len(parts) > 1 else "+0000"
    if offset == "Z":
        offset = "+0000"
    for fmt in ("%Y%m%d%H%M%S%z", "%Y%m%d%H%M%z"):
        try:
            return datetime.strptime(stamp + offset, fmt)
        except ValueError:
            pass
    return None


def parse_xmltv(path: Path) -> dict[str, list[Programme]]:
    """Parse XMLTV and index programmes by XMLTV id and display-name aliases."""
    if not path.exists():
        return {}

    aliases: dict[str, str] = {}
    programs: dict[str, list[Programme]] = {}

    for _event, elem in ET.iterparse(str(path), events=("end",)):
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "channel":
            channel_id = elem.attrib.get("id", "").strip()
            if channel_id:
                aliases[normalize_key(channel_id)] = channel_id
                for child in elem:
                    if child.tag.rsplit("}", 1)[-1] == "display-name" and child.text:
                        aliases[normalize_key(child.text)] = channel_id
            elem.clear()
            continue

        if tag != "programme":
            continue

        channel_id = elem.attrib.get("channel", "").strip()
        start = _time(elem.attrib.get("start", ""))
        stop = _time(elem.attrib.get("stop", ""))
        title = ""
        desc = ""
        for child in elem:
            child_tag = child.tag.rsplit("}", 1)[-1]
            if child_tag == "title" and child.text and not title:
                title = child.text.strip()
            elif child_tag == "desc" and child.text and not desc:
                desc = child.text.strip()

        if channel_id and start and stop:
            programs.setdefault(channel_id, []).append(
                Programme(channel_id, title or "Untitled", start, stop, desc)
            )
        elem.clear()

    for values in programs.values():
        values.sort(key=lambda p: p.start)

    expanded = dict(programs)
    for alias, channel_id in aliases.items():
        if channel_id in programs:
            expanded[alias] = programs[channel_id]
    return expanded


def now_and_next(
    guide: dict[str, list[Programme]],
    tvg_id: str,
    channel_name: str,
) -> tuple[Optional[Programme], Optional[Programme]]:
    values: list[Programme] = []
    for key in (tvg_id, normalize_key(tvg_id), normalize_key(channel_name), channel_name):
        if key and key in guide:
            values = guide[key]
            break

    now = datetime.now(timezone.utc)
    for index, program in enumerate(values):
        start = program.start.astimezone(timezone.utc)
        stop = program.stop.astimezone(timezone.utc)
        if start <= now < stop:
            following = values[index + 1] if index + 1 < len(values) else None
            return program, following
        if start > now:
            return None, program
    return None, None
