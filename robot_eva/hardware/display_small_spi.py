"""
2.8" small display backend (SPI) for Raspberry Pi.

Uses Adafruit CircuitPython RGB Display if available.
If libraries are missing, backend stays disabled but does not crash the robot.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

from PIL import Image


class SmallDisplayBase:
    async def initialize(self) -> None:
        raise NotImplementedError

    async def display(self, img: Image.Image) -> None:
        raise NotImplementedError

    async def cleanup(self) -> None:
        return


class SmallSpiDisplay(SmallDisplayBase):
    def __init__(self, config, size: Tuple[int, int]):
        self.config = config
        self.size = (int(size[0]), int(size[1]))
        self.logger = logging.getLogger(__name__)

        self._disp = None
        self._enabled = False

    async def initialize(self) -> None:
        # Read GPIO mapping for SPI display if present
        spi_cfg = self.config.get_gpio_mapping("spi.small_display", {}) or {}
        hw_cfg = self.config.get("hardware.display.small", {}) or {}

        self._enabled = bool(hw_cfg.get("enabled", True)) and bool(spi_cfg.get("enabled", True))
        if not self._enabled:
            raise RuntimeError("small display disabled in config")

        # These pins are highly device-specific; provide defaults but allow override.
        # NOTE: Use BCM numbering as in most Pi guides (Blinka exposes board.Dxx for BCM).
        dc_pin = int(hw_cfg.get("dc_pin", 25))        # D/C (data/command)
        reset_pin = hw_cfg.get("reset_pin", 24)       # RST (optional)
        cs_pin = hw_cfg.get("cs_pin", 8)              # CS (SPI0 CE0 is BCM8)
        rotation = int(hw_cfg.get("rotation", 0))
        baudrate = int(spi_cfg.get("speed", 24000000))

        driver = str(hw_cfg.get("driver", "ili9341")).lower()

        try:
            import board
            import digitalio
        except Exception as e:
            raise RuntimeError(f"Missing Adafruit Blinka stack (board/digitalio): {e}") from e

        try:
            from adafruit_rgb_display import ili9341, st7789
        except Exception as e:
            raise RuntimeError(f"Missing adafruit_rgb_display library: {e}") from e

        spi = board.SPI()

        def _pin(name: str, pin: int):
            # Prefer dedicated SPI chip-select objects when applicable
            if name == "cs":
                if pin == 8 and hasattr(board, "CE0"):
                    return getattr(board, "CE0")
                if pin == 7 and hasattr(board, "CE1"):
                    return getattr(board, "CE1")
            attr = getattr(board, f"D{pin}", None)
            if attr is None:
                raise RuntimeError(f"Blinka board does not expose {name} pin D{pin}. Check pin mapping.")
            return attr

        # digitalio pins (Blinka)
        try:
            dc = digitalio.DigitalInOut(_pin("dc", dc_pin))
        except Exception as e:
            raise RuntimeError(
                f"Не удалось захватить DC pin (BCM{dc_pin}). Проверьте wiring и что пин свободен. Причина: {e}"
            ) from e

        try:
            cs = digitalio.DigitalInOut(_pin("cs", cs_pin))
        except Exception as e:
            raise RuntimeError(
                f"Не удалось захватить CS pin (BCM{cs_pin}) — GPIO busy. "
                "На Raspberry Pi линии CE0/CE1 часто заняты ядром (spidev). "
                "Решение: подключи CS дисплея на свободный GPIO (например BCM5/BCM6) и укажи его в `hardware.display.small.cs_pin`."
            ) from e
        rst = None
        if reset_pin is not None:
            rp = int(reset_pin)
            rst = digitalio.DigitalInOut(_pin("reset", rp))

        width, height = self.size

        # Instantiate display driver
        if driver == "st7789":
            self._disp = st7789.ST7789(
                spi,
                cs=cs,
                dc=dc,
                rst=rst,
                width=width,
                height=height,
                rotation=rotation,
                baudrate=baudrate,
            )
        else:
            # default: ili9341 (very common 2.8")
            self._disp = ili9341.ILI9341(
                spi,
                cs=cs,
                dc=dc,
                rst=rst,
                width=width,
                height=height,
                rotation=rotation,
                baudrate=baudrate,
            )

        # Clear once
        await self.display(Image.new("RGB", self.size, (0, 0, 0)))

    async def display(self, img: Image.Image) -> None:
        if not self._disp:
            return

        # Ensure correct mode/size
        if img.mode != "RGB":
            img = img.convert("RGB")
        if img.size != self.size:
            img = img.resize(self.size)

        # Driver call is sync; run in default loop without blocking too long
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._disp.image, img)

    async def cleanup(self) -> None:
        self._disp = None


