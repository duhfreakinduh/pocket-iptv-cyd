"""Binary protocol shared by the Raspberry Pi service and CYD firmware."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
import zlib

MAGIC = b"PIPF"
VERSION = 1
HEADER_STRUCT = struct.Struct("<4sBBHIII")
HEADER_SIZE = HEADER_STRUCT.size
MAX_PAYLOAD = 64 * 1024
STATE_PREFIX = struct.Struct("<BBHH")


class PacketType(IntEnum):
    JPEG = 1
    PCM_U8 = 2
    STATE = 3
    HEARTBEAT = 4


@dataclass(frozen=True)
class Header:
    packet_type: PacketType
    flags: int
    sequence: int
    payload_length: int
    crc32: int


@dataclass(frozen=True)
class ScreenState:
    volume: int
    paused: bool
    channel_index: int
    channel_total: int
    channel_name: str


def build_packet(
    packet_type: PacketType | int,
    sequence: int,
    payload: bytes = b"",
    flags: int = 0,
) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload exceeds {MAX_PAYLOAD} bytes")
    packet_type = PacketType(packet_type)
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        int(packet_type),
        flags & 0xFFFF,
        sequence & 0xFFFFFFFF,
        len(payload),
        checksum,
    )
    return header + payload


def parse_header(data: bytes) -> Header:
    if len(data) != HEADER_SIZE:
        raise ValueError(f"header must be exactly {HEADER_SIZE} bytes")
    magic, version, packet_type, flags, sequence, length, checksum = (
        HEADER_STRUCT.unpack(data)
    )
    if magic != MAGIC:
        raise ValueError("bad packet magic")
    if version != VERSION:
        raise ValueError(f"unsupported protocol version {version}")
    if length > MAX_PAYLOAD:
        raise ValueError("declared payload is too large")
    return Header(PacketType(packet_type), flags, sequence, length, checksum)


def validate_payload(header: Header, payload: bytes) -> bool:
    return (
        len(payload) == header.payload_length
        and (zlib.crc32(payload) & 0xFFFFFFFF) == header.crc32
    )


def encode_state(state: ScreenState) -> bytes:
    if not 0 <= state.volume <= 100:
        raise ValueError("volume must be 0..100")
    name = state.channel_name.encode("utf-8", errors="replace")[:120]
    return STATE_PREFIX.pack(
        state.volume,
        1 if state.paused else 0,
        state.channel_index & 0xFFFF,
        state.channel_total & 0xFFFF,
    ) + name


def decode_state(payload: bytes) -> ScreenState:
    if len(payload) < STATE_PREFIX.size:
        raise ValueError("state payload is too short")
    volume, paused, index, total = STATE_PREFIX.unpack_from(payload)
    name = payload[STATE_PREFIX.size :].decode("utf-8", errors="replace")
    return ScreenState(volume, bool(paused), index, total, name)
