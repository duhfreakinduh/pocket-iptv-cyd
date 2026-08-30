#pragma once

#include <Arduino.h>

namespace pip {

constexpr uint8_t VERSION = 1;
constexpr char MAGIC[4] = {'P', 'I', 'P', 'F'};
constexpr size_t MAX_PAYLOAD = 64 * 1024;

enum PacketType : uint8_t {
  JPEG = 1,
  PCM_U8 = 2,
  STATE = 3,
  HEARTBEAT = 4,
};

struct __attribute__((packed)) PacketHeader {
  char magic[4];
  uint8_t version;
  uint8_t type;
  uint16_t flags;
  uint32_t sequence;
  uint32_t payloadLength;
  uint32_t crc32;
};

static_assert(sizeof(PacketHeader) == 20, "Packet header must stay wire-compatible");

inline uint32_t crc32(const uint8_t* data, size_t length) {
  uint32_t value = 0xFFFFFFFFU;
  for (size_t index = 0; index < length; ++index) {
    value ^= data[index];
    for (uint8_t bit = 0; bit < 8; ++bit) {
      const uint32_t mask = -(value & 1U);
      value = (value >> 1U) ^ (0xEDB88320U & mask);
    }
  }
  return ~value;
}

}  // namespace pip
