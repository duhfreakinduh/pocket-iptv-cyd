"""Resilient USB-serial connection to the ESP32 screen."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # lets pure modules/tests load before dependencies are installed
    serial = None
    list_ports = None

LOGGER = logging.getLogger(__name__)
COMMAND_PREFIX = b"!PIPCMD:"
LIKELY_USB_UART_IDS = {
    (0x1A86, 0x7523),  # CH340/CH341
    (0x1A86, 0x55D4),  # CH9102/CH34x revision
    (0x10C4, 0xEA60),  # CP210x
    (0x0403, 0x6001),  # FTDI
}


def find_screen_port(requested: str = "auto") -> str | None:
    if requested and requested.lower() != "auto":
        return requested
    if list_ports is None:
        return None
    ports = list(list_ports.comports())
    for port in ports:
        if (port.vid, port.pid) in LIKELY_USB_UART_IDS:
            return port.device
    for port in ports:
        description = (port.description or "").lower()
        if any(word in description for word in ("usb serial", "ch340", "cp210")):
            return port.device
    return None


class SerialLink:
    def __init__(
        self,
        requested_port: str,
        baud: int,
        on_command: Callable[[str], None],
        on_connect: Callable[[], None] | None = None,
    ) -> None:
        self.requested_port = requested_port
        self.baud = baud
        self.on_command = on_command
        self.on_connect = on_connect
        self._serial = None
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._connection_lock = threading.Lock()
        self._manager: threading.Thread | None = None

    @property
    def connected(self) -> bool:
        return self._serial is not None and bool(self._serial.is_open)

    @property
    def port(self) -> str | None:
        return self._serial.port if self.connected else None

    def start(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed")
        if self._manager and self._manager.is_alive():
            return
        self._manager = threading.Thread(
            target=self._connection_manager,
            name="screen-serial",
            daemon=True,
        )
        self._manager.start()

    def stop(self) -> None:
        self._stop.set()
        self._disconnect()
        if self._manager:
            self._manager.join(timeout=2)

    def write(self, packet: bytes) -> bool:
        if not self.connected:
            return False
        with self._write_lock:
            target = self._serial
            if target is None:
                return False
            try:
                target.write(packet)
                return True
            except (OSError, serial.SerialException, serial.SerialTimeoutException):
                LOGGER.warning("CYD serial write failed; reconnecting")
                self._disconnect()
                return False

    def _connection_manager(self) -> None:
        while not self._stop.is_set():
            if not self.connected:
                port = find_screen_port(self.requested_port)
                if port:
                    self._connect(port)
                else:
                    self._stop.wait(2.0)
                    continue
            self._read_commands()

    def _connect(self, port: str) -> None:
        try:
            target = serial.Serial(
                port=port,
                baudrate=self.baud,
                timeout=0.2,
                write_timeout=3.0,
            )
            target.dtr = False
            target.rts = False
            target.reset_input_buffer()
            with self._connection_lock:
                self._serial = target
            LOGGER.info("CYD connected on %s at %d baud", port, self.baud)
            time.sleep(0.7)
            if self.on_connect:
                self.on_connect()
        except (OSError, serial.SerialException) as exc:
            LOGGER.warning("Could not open CYD serial port %s: %s", port, exc)
            self._stop.wait(2.0)

    def _read_commands(self) -> None:
        target = self._serial
        if target is None:
            return
        try:
            line = target.readline()
            if not line:
                return
            marker = line.find(COMMAND_PREFIX)
            if marker < 0:
                return
            command = line[marker + len(COMMAND_PREFIX) :].decode(
                "ascii", errors="ignore"
            ).strip()
            if command:
                self.on_command(command)
        except (OSError, serial.SerialException):
            LOGGER.info("CYD disconnected")
            self._disconnect()

    def _disconnect(self) -> None:
        with self._connection_lock:
            target, self._serial = self._serial, None
        if target is not None:
            try:
                target.close()
            except OSError:
                pass
