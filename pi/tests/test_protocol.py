import unittest
import zlib

from pocket_iptv.protocol import (
    HEADER_SIZE,
    PacketType,
    ScreenState,
    build_packet,
    decode_state,
    encode_state,
    parse_header,
    validate_payload,
)


class ProtocolTests(unittest.TestCase):
    def test_packet_round_trip(self):
        payload = b"jpeg-ish-data"
        packet = build_packet(PacketType.JPEG, 42, payload, flags=3)
        header = parse_header(packet[:HEADER_SIZE])
        self.assertEqual(header.packet_type, PacketType.JPEG)
        self.assertEqual(header.sequence, 42)
        self.assertEqual(header.flags, 3)
        self.assertEqual(header.crc32, zlib.crc32(payload) & 0xFFFFFFFF)
        self.assertTrue(validate_payload(header, packet[HEADER_SIZE:]))

    def test_corruption_is_detected(self):
        packet = build_packet(PacketType.PCM_U8, 1, b"123")
        header = parse_header(packet[:HEADER_SIZE])
        self.assertFalse(validate_payload(header, b"124"))

    def test_state_round_trip_and_name_limit(self):
        state = ScreenState(65, False, 2, 12, "Test Channel " + "x" * 200)
        decoded = decode_state(encode_state(state))
        self.assertEqual(decoded.volume, 65)
        self.assertEqual(decoded.channel_index, 2)
        self.assertLessEqual(len(decoded.channel_name.encode()), 120)


if __name__ == "__main__":
    unittest.main()
