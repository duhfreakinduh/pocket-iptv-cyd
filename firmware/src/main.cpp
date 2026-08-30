#include <Arduino.h>
#include <Preferences.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <TJpg_Decoder.h>
#include <driver/i2s.h>
#include <esp_heap_caps.h>
#include <freertos/FreeRTOS.h>
#include <freertos/stream_buffer.h>

#include "pip_protocol.h"

#ifndef PIP_BAUD
#define PIP_BAUD 2000000
#endif

namespace {

constexpr int SCREEN_WIDTH = 320;
constexpr int SCREEN_HEIGHT = 240;
constexpr int TOOLBAR_TOP = 198;
constexpr int INFO_TOP = 174;
constexpr int TOUCH_CLK = 25;
constexpr int TOUCH_MISO = 39;
constexpr int TOUCH_MOSI = 32;
constexpr int TOUCH_CS_PIN = 33;
constexpr int TOUCH_IRQ = 36;
constexpr uint32_t CALIBRATION_MAGIC = 0x50495043;  // PIPC
constexpr uint32_t OVERLAY_TIMEOUT_MS = 5000;
constexpr uint32_t FRAME_TIMEOUT_MS = 4500;
constexpr size_t AUDIO_BUFFER_BYTES = 16 * 1024;
constexpr i2s_port_t AUDIO_I2S = I2S_NUM_0;

TFT_eSPI tft;
SPIClass touchSpi(VSPI);
Preferences preferences;
StreamBufferHandle_t audioStream = nullptr;
uint8_t* packetBuffer = nullptr;

struct TouchCalibration {
  uint32_t magic;
  int32_t xLeft;
  int32_t xRight;
  int32_t yTop;
  int32_t yBottom;
  uint8_t displayXUsesRawX;
};

struct RawTouchPoint {
  int32_t x;
  int32_t y;
  int32_t z;
};

class CydTouch {
 public:
  void begin(SPIClass& bus) {
    bus_ = &bus;
    pinMode(TOUCH_CS_PIN, OUTPUT);
    digitalWrite(TOUCH_CS_PIN, HIGH);
    pinMode(TOUCH_IRQ, INPUT);
  }

  bool touched() const { return digitalRead(TOUCH_IRQ) == LOW; }

  RawTouchPoint point() {
    if (!bus_ || !touched()) {
      return {0, 0, 0};
    }
    int32_t samplesX[7];
    int32_t samplesY[7];
    bus_->beginTransaction(SPISettings(2000000, MSBFIRST, SPI_MODE0));
    digitalWrite(TOUCH_CS_PIN, LOW);
    for (int index = 0; index < 7; ++index) {
      samplesX[index] = read12(0xD0);
      samplesY[index] = read12(0x90);
    }
    read12(0xD0);  // Leave the controller in a known powered-down state.
    digitalWrite(TOUCH_CS_PIN, HIGH);
    bus_->endTransaction();
    sortSeven(samplesX);
    sortSeven(samplesY);
    return {samplesX[3], samplesY[3], 1000};
  }

 private:
  SPIClass* bus_ = nullptr;

  uint16_t read12(uint8_t command) {
    bus_->transfer(command);
    return (bus_->transfer16(0) >> 3) & 0x0FFF;
  }

  static void sortSeven(int32_t* values) {
    for (int i = 1; i < 7; ++i) {
      const int32_t value = values[i];
      int j = i - 1;
      while (j >= 0 && values[j] > value) {
        values[j + 1] = values[j];
        --j;
      }
      values[j + 1] = value;
    }
  }
};

CydTouch touch;

TouchCalibration calibration{};
volatile uint8_t currentVolume = 65;
volatile bool playbackPaused = false;
uint16_t currentChannel = 0;
uint16_t channelTotal = 0;
char channelName[121] = "Waiting for Pi";
bool overlayVisible = true;
uint32_t overlayUntil = 0;
uint32_t lastFrameAt = 0;
uint32_t lastTouchAt = 0;

uint16_t background = TFT_BLACK;
uint16_t panel = tft.color565(11, 31, 44);
uint16_t accent = tft.color565(255, 212, 59);
uint16_t muted = tft.color565(157, 180, 194);

bool jpegBlock(int16_t x, int16_t y, uint16_t width, uint16_t height,
               uint16_t* bitmap) {
  if (y >= SCREEN_HEIGHT || x >= SCREEN_WIDTH) {
    return false;
  }
  tft.pushImage(x, y, width, height, bitmap);
  return true;
}

void sendCommand(const char* command) {
  Serial.print("!PIPCMD:");
  Serial.print(command);
  Serial.print('\n');
}

void drawCentered(const String& text, int y, int font, uint16_t color) {
  tft.setTextDatum(TC_DATUM);
  tft.setTextColor(color, background);
  tft.drawString(text, SCREEN_WIDTH / 2, y, font);
}

void drawWaiting() {
  tft.fillScreen(background);
  drawCentered("POCKET IPTV", 55, 4, accent);
  drawCentered("Waiting for Pi / USB", 105, 2, TFT_WHITE);
  drawCentered("Open pocketiptv.local:8080", 134, 2, muted);
  drawCentered("Tap screen for controls", 157, 2, muted);
}

void drawButton(int index, const char* label, bool active = false) {
  const int x = index * 64;
  const uint16_t fill = active ? accent : panel;
  const uint16_t ink = active ? TFT_BLACK : TFT_WHITE;
  tft.fillRect(x + 1, TOOLBAR_TOP, 62, SCREEN_HEIGHT - TOOLBAR_TOP, fill);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(ink, fill);
  tft.drawString(label, x + 32, TOOLBAR_TOP + 20, 2);
}

void drawOverlay() {
  tft.fillRect(0, INFO_TOP, SCREEN_WIDTH, TOOLBAR_TOP - INFO_TOP, panel);
  tft.setTextDatum(ML_DATUM);
  tft.setTextColor(TFT_WHITE, panel);
  String title(channelName);
  if (title.length() > 29) {
    title = title.substring(0, 26) + "...";
  }
  tft.drawString(title, 5, INFO_TOP + 12, 2);
  tft.setTextDatum(MR_DATUM);
  tft.setTextColor(accent, panel);
  String status = String(currentChannel + (channelTotal ? 1 : 0)) + "/" +
                  String(channelTotal) + "  " + String(currentVolume) + "%";
  tft.drawString(status, SCREEN_WIDTH - 5, INFO_TOP + 12, 2);
  drawButton(0, "VOL-");
  drawButton(1, "PREV");
  drawButton(2, playbackPaused ? "LIVE" : "PAUSE", playbackPaused);
  drawButton(3, "NEXT");
  drawButton(4, "VOL+");
}

bool readTouchRaw(RawTouchPoint& point) {
  if (!touch.touched()) {
    return false;
  }
  point = touch.point();
  return point.z > 150;
}

RawTouchPoint averagedTouch() {
  int64_t sumX = 0;
  int64_t sumY = 0;
  int count = 0;
  const uint32_t deadline = millis() + 1500;
  while (millis() < deadline && count < 18) {
    RawTouchPoint point;
    if (readTouchRaw(point)) {
      sumX += point.x;
      sumY += point.y;
      ++count;
    }
    delay(12);
  }
  while (touch.touched()) {
    delay(10);
  }
  if (!count) {
    return {0, 0, 0};
  }
  return {static_cast<int32_t>(sumX / count),
          static_cast<int32_t>(sumY / count), 1000};
}

void drawCalibrationTarget(int x, int y, int number) {
  tft.fillScreen(background);
  drawCentered("TOUCH CALIBRATION", 18, 2, accent);
  drawCentered("Touch the crosshair with the stylus", 43, 2, muted);
  tft.drawCircle(x, y, 11, TFT_WHITE);
  tft.drawFastHLine(x - 16, y, 33, TFT_WHITE);
  tft.drawFastVLine(x, y - 16, 33, TFT_WHITE);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(accent, background);
  tft.drawNumber(number, x, y, 2);
}

bool calibrateTouch() {
  constexpr int targetX[4] = {22, 297, 297, 22};
  constexpr int targetY[4] = {68, 68, 217, 217};
  RawTouchPoint raw[4];
  for (int index = 0; index < 4; ++index) {
    drawCalibrationTarget(targetX[index], targetY[index], index + 1);
    const uint32_t deadline = millis() + 20000;
    while (!touch.touched() && millis() < deadline) {
      delay(10);
    }
    if (!touch.touched()) {
      drawCentered("Calibration timed out", 120, 2, TFT_RED);
      delay(1500);
      return false;
    }
    raw[index] = averagedTouch();
    delay(180);
  }

  const int32_t horizontalRawX =
      abs(raw[1].x - raw[0].x) + abs(raw[2].x - raw[3].x);
  const int32_t horizontalRawY =
      abs(raw[1].y - raw[0].y) + abs(raw[2].y - raw[3].y);
  calibration.magic = CALIBRATION_MAGIC;
  calibration.displayXUsesRawX = horizontalRawX >= horizontalRawY;

  auto axisX = [](const RawTouchPoint& value) {
    return calibration.displayXUsesRawX ? value.x : value.y;
  };
  auto axisY = [](const RawTouchPoint& value) {
    return calibration.displayXUsesRawX ? value.y : value.x;
  };
  calibration.xLeft = (axisX(raw[0]) + axisX(raw[3])) / 2;
  calibration.xRight = (axisX(raw[1]) + axisX(raw[2])) / 2;
  calibration.yTop = (axisY(raw[0]) + axisY(raw[1])) / 2;
  calibration.yBottom = (axisY(raw[2]) + axisY(raw[3])) / 2;

  if (abs(calibration.xRight - calibration.xLeft) < 500 ||
      abs(calibration.yBottom - calibration.yTop) < 500) {
    calibration.magic = 0;
    drawCentered("Calibration values invalid", 120, 2, TFT_RED);
    delay(1500);
    return false;
  }
  preferences.putBytes("touch", &calibration, sizeof(calibration));
  tft.fillScreen(background);
  drawCentered("Calibration saved", 105, 4, accent);
  delay(900);
  return true;
}

bool mapTouch(const RawTouchPoint& raw, int& screenX, int& screenY) {
  if (calibration.magic != CALIBRATION_MAGIC) {
    return false;
  }
  const int32_t rawX = calibration.displayXUsesRawX ? raw.x : raw.y;
  const int32_t rawY = calibration.displayXUsesRawX ? raw.y : raw.x;
  if (calibration.xRight == calibration.xLeft ||
      calibration.yBottom == calibration.yTop) {
    return false;
  }
  screenX = (rawX - calibration.xLeft) * (SCREEN_WIDTH - 1) /
            (calibration.xRight - calibration.xLeft);
  screenY = (rawY - calibration.yTop) * (SCREEN_HEIGHT - 1) /
            (calibration.yBottom - calibration.yTop);
  screenX = constrain(screenX, 0, SCREEN_WIDTH - 1);
  screenY = constrain(screenY, 0, SCREEN_HEIGHT - 1);
  return true;
}

void handleTouch() {
  if (!touch.touched() || millis() - lastTouchAt < 220) {
    return;
  }
  RawTouchPoint raw = averagedTouch();
  int x = 0;
  int y = 0;
  if (!mapTouch(raw, x, y)) {
    return;
  }
  lastTouchAt = millis();
  if (!overlayVisible) {
    overlayVisible = true;
    overlayUntil = millis() + OVERLAY_TIMEOUT_MS;
    drawOverlay();
    return;
  }
  overlayUntil = millis() + OVERLAY_TIMEOUT_MS;
  if (y < TOOLBAR_TOP) {
    overlayVisible = false;
    return;
  }
  switch (constrain(x / 64, 0, 4)) {
    case 0:
      sendCommand("vol_down");
      break;
    case 1:
      sendCommand("prev");
      break;
    case 2:
      sendCommand("toggle");
      break;
    case 3:
      sendCommand("next");
      break;
    case 4:
      sendCommand("vol_up");
      break;
  }
}

void configureAudio() {
  const i2s_config_t config = {
      .mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_TX |
                                      I2S_MODE_DAC_BUILT_IN),
      .sample_rate = 16000,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 8,
      .dma_buf_len = 256,
      .use_apll = false,
      .tx_desc_auto_clear = true,
      .fixed_mclk = 0,
  };
  i2s_driver_install(AUDIO_I2S, &config, 0, nullptr);
  i2s_set_dac_mode(I2S_DAC_CHANNEL_LEFT_EN);  // CYD amp is on GPIO26.
  i2s_zero_dma_buffer(AUDIO_I2S);
}

void audioTask(void*) {
  uint8_t input[256];
  uint16_t output[256];
  for (;;) {
    const size_t count = xStreamBufferReceive(
        audioStream, input, sizeof(input), pdMS_TO_TICKS(80));
    const size_t samples = count ? count : sizeof(input);
    for (size_t index = 0; index < samples; ++index) {
      const int source = count ? input[index] : 128;
      const int centered = source - 128;
      int scaled = playbackPaused ? 128 : 128 + centered * currentVolume / 100;
      scaled = constrain(scaled, 0, 255);
      output[index] = static_cast<uint16_t>(scaled) << 8;
    }
    size_t written = 0;
    i2s_write(AUDIO_I2S, output, samples * sizeof(uint16_t), &written,
              portMAX_DELAY);
  }
}

void enqueueAudio(const uint8_t* data, size_t length) {
  size_t available = xStreamBufferSpacesAvailable(audioStream);
  uint8_t discard[256];
  while (available < length) {
    const size_t needed = min(sizeof(discard), length - available);
    const size_t removed = xStreamBufferReceive(audioStream, discard, needed, 0);
    if (!removed) {
      break;
    }
    available = xStreamBufferSpacesAvailable(audioStream);
  }
  xStreamBufferSend(audioStream, data, length, 0);
}

void processState(const uint8_t* payload, size_t length) {
  if (length < 6) {
    return;
  }
  currentVolume = constrain(payload[0], 0, 100);
  playbackPaused = payload[1] != 0;
  currentChannel = static_cast<uint16_t>(payload[2]) |
                   (static_cast<uint16_t>(payload[3]) << 8);
  channelTotal = static_cast<uint16_t>(payload[4]) |
                 (static_cast<uint16_t>(payload[5]) << 8);
  const size_t nameLength = min(length - 6, sizeof(channelName) - 1);
  memcpy(channelName, payload + 6, nameLength);
  channelName[nameLength] = '\0';
  overlayVisible = true;
  overlayUntil = millis() + OVERLAY_TIMEOUT_MS;
  drawOverlay();
}

void processPacket(const pip::PacketHeader& header, const uint8_t* payload) {
  if (pip::crc32(payload, header.payloadLength) != header.crc32) {
    return;
  }
  switch (header.type) {
    case pip::JPEG:
      TJpgDec.drawJpg(0, 0, payload, header.payloadLength);
      lastFrameAt = millis();
      if (overlayVisible) {
        drawOverlay();
      }
      break;
    case pip::PCM_U8:
      enqueueAudio(payload, header.payloadLength);
      break;
    case pip::STATE:
      processState(payload, header.payloadLength);
      break;
    case pip::HEARTBEAT:
      break;
    default:
      break;
  }
}

bool findMagic() {
  static uint8_t matched = 0;
  while (Serial.available()) {
    const char value = static_cast<char>(Serial.read());
    if (value == pip::MAGIC[matched]) {
      ++matched;
      if (matched == sizeof(pip::MAGIC)) {
        matched = 0;
        return true;
      }
    } else {
      matched = value == pip::MAGIC[0] ? 1 : 0;
    }
  }
  return false;
}

void pumpSerial() {
  if (!findMagic()) {
    return;
  }
  pip::PacketHeader header{};
  memcpy(header.magic, pip::MAGIC, sizeof(pip::MAGIC));
  uint8_t* remainder = reinterpret_cast<uint8_t*>(&header) + sizeof(pip::MAGIC);
  const size_t remainderLength = sizeof(header) - sizeof(pip::MAGIC);
  if (Serial.readBytes(remainder, remainderLength) != remainderLength) {
    return;
  }
  if (header.version != pip::VERSION || header.payloadLength > pip::MAX_PAYLOAD ||
      header.payloadLength == 0) {
    return;
  }
  if (Serial.readBytes(packetBuffer, header.payloadLength) != header.payloadLength) {
    return;
  }
  processPacket(header, packetBuffer);
}

void configureDisplayAndTouch() {
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, HIGH);
  tft.init();
  tft.setRotation(1);
  tft.setSwapBytes(true);
  tft.fillScreen(background);
  TJpgDec.setJpgScale(1);
  TJpgDec.setSwapBytes(true);
  TJpgDec.setCallback(jpegBlock);

  touchSpi.begin(TOUCH_CLK, TOUCH_MISO, TOUCH_MOSI, TOUCH_CS_PIN);
  touch.begin(touchSpi);
  preferences.begin("pocketiptv", false);
  if (preferences.getBytesLength("touch") == sizeof(calibration)) {
    preferences.getBytes("touch", &calibration, sizeof(calibration));
  }

  drawWaiting();
  bool forceCalibration = calibration.magic != CALIBRATION_MAGIC;
  const uint32_t holdDeadline = millis() + 1000;
  while (millis() < holdDeadline) {
    if (touch.touched()) {
      forceCalibration = true;
      break;
    }
    delay(10);
  }
  if (forceCalibration) {
    while (touch.touched()) {
      delay(10);
    }
    calibrateTouch();
    drawWaiting();
  }
}

}  // namespace

void setup() {
  packetBuffer = static_cast<uint8_t*>(heap_caps_malloc(
      pip::MAX_PAYLOAD, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL));
  if (!packetBuffer) {
    ESP.restart();
  }
  audioStream = xStreamBufferCreate(AUDIO_BUFFER_BYTES, 1);
  if (!audioStream) {
    ESP.restart();
  }
  configureDisplayAndTouch();
  configureAudio();
  xTaskCreatePinnedToCore(audioTask, "audio", 3072, nullptr, 2, nullptr, 0);

  Serial.setRxBufferSize(48 * 1024);
  Serial.setTimeout(300);
  Serial.begin(PIP_BAUD);
  delay(250);
  sendCommand("ready");
  overlayUntil = millis() + OVERLAY_TIMEOUT_MS;
}

void loop() {
  pumpSerial();
  handleTouch();
  const uint32_t now = millis();
  if (overlayVisible && static_cast<int32_t>(now - overlayUntil) >= 0) {
    overlayVisible = false;
  }
  if (lastFrameAt && now - lastFrameAt > FRAME_TIMEOUT_MS && !playbackPaused) {
    lastFrameAt = 0;
    drawWaiting();
    drawOverlay();
  }
  delay(1);
}
