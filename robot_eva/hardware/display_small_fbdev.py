"""
Small display backend for Raspberry Pi DSI panels exposed as framebuffer (/dev/fbX).

Your DSI panel shows up as:
- /dev/fb0
- /sys/class/graphics/fb0/virtual_size = 480,640
- /sys/class/graphics/fb0/bits_per_pixel = 32

We write frames via mmap. Supports 32bpp (XRGB8888 / ARGB8888-like) best-effort.
"""

from __future__ import annotations

import asyncio
import logging
import mmap
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from PIL import Image

from .display_small_spi import SmallDisplayBase  # reuse interface


@dataclass
class FbInfo:
    size: Tuple[int, int]
    bpp: int


class SmallFbdevDisplay(SmallDisplayBase):
    def __init__(self, config, logical_size: Tuple[int, int]):
        self.config = config
        self.logical_size = (int(logical_size[0]), int(logical_size[1]))
        self.logger = logging.getLogger(__name__)

        self.fbdev = str(config.get("hardware.display.small.fbdev", "/dev/fb0"))
        self.rotation = int(config.get("hardware.display.small.rotation", 0))

        self._fd: Optional[int] = None
        self._mm: Optional[mmap.mmap] = None
        self._fb: Optional[FbInfo] = None

    async def initialize(self) -> None:
        if not os.path.exists(self.fbdev):
            raise RuntimeError(f"Framebuffer device not found: {self.fbdev}")

        # Read fb size/bpp from sysfs (match fbdev basename: fb0)
        fb_name = os.path.basename(self.fbdev)
        sys_base = f"/sys/class/graphics/{fb_name}"
        try:
            vs = open(f"{sys_base}/virtual_size", "r", encoding="utf-8").read().strip()
            w_s, h_s = vs.split(",")
            w, h = int(w_s), int(h_s)
        except Exception as e:
            raise RuntimeError(f"Failed to read virtual_size for {fb_name}: {e}") from e

        try:
            bpp = int(open(f"{sys_base}/bits_per_pixel", "r", encoding="utf-8").read().strip())
        except Exception as e:
            raise RuntimeError(f"Failed to read bits_per_pixel for {fb_name}: {e}") from e

        if bpp not in (16, 24, 32):
            raise RuntimeError(f"Unsupported framebuffer bpp={bpp} for {self.fbdev}")

        self._fb = FbInfo(size=(w, h), bpp=bpp)

        # Open and mmap framebuffer
        self._fd = os.open(self.fbdev, os.O_RDWR)
        # bytes per pixel
        bpp_bytes = bpp // 8
        length = w * h * bpp_bytes
        self._mm = mmap.mmap(self._fd, length, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)

    async def display(self, img: Image.Image) -> None:
        if not self._mm or not self._fb:
            return

        fb_w, fb_h = self._fb.size

        # Render at logical size first
        if img.mode != "RGB":
            img = img.convert("RGB")

        if img.size != self.logical_size:
            img = img.resize(self.logical_size)

        # Apply rotation (0/90/180/270)
        rot = self.rotation % 360
        if rot:
            # PIL rotate CCW by default; keep expand=True then fit into fb
            img = img.rotate(rot, expand=True)

        # Letterbox to framebuffer, centered
        canvas = Image.new("RGB", (fb_w, fb_h), (0, 0, 0))
        x = (fb_w - img.size[0]) // 2
        y = (fb_h - img.size[1]) // 2
        canvas.paste(img, (x, y))

        # Convert to framebuffer format
        bpp = self._fb.bpp
        if bpp == 32:
            # Best-effort: write as XRGB8888 (little-endian: B,G,R,X)
            raw = canvas.tobytes("raw", "BGRX")
        elif bpp == 24:
            raw = canvas.tobytes("raw", "BGR")
        else:  # 16bpp RGB565
            # Pillow can give RGB; pack to RGB565
            r, g, b = canvas.split()
            r = r.point(lambda i: (i >> 3) & 0x1F)
            g = g.point(lambda i: (i >> 2) & 0x3F)
            b = b.point(lambda i: (i >> 3) & 0x1F)
            # Combine: rrrrrggggggbbbbb
            # Build bytes little-endian
            import array

            rr = array.array("B", r.tobytes())
            gg = array.array("B", g.tobytes())
            bb = array.array("B", b.tobytes())
            out = bytearray(fb_w * fb_h * 2)
            j = 0
            for i in range(fb_w * fb_h):
                v = (rr[i] << 11) | (gg[i] << 5) | bb[i]
                out[j] = v & 0xFF
                out[j + 1] = (v >> 8) & 0xFF
                j += 2
            raw = bytes(out)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_raw, raw)

    def _write_raw(self, raw: bytes) -> None:
        if not self._mm:
            return
        self._mm.seek(0)
        self._mm.write(raw)
        self._mm.flush()

    async def cleanup(self) -> None:
        if self._mm:
            try:
                self._mm.close()
            except Exception:
                pass
            self._mm = None
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
        self._fb = None



