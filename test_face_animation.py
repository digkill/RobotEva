#!/usr/bin/env python3
"""
Простой тест анимации лица на framebuffer (без зависимостей робота)
"""
import asyncio
import os
import mmap
import time
from PIL import Image, ImageDraw

class SimpleFbdevDisplay:
    def __init__(self, fbdev="/dev/fb0", width=480, height=640):
        self.fbdev = fbdev
        self.width = width
        self.height = height
        self._fd = None
        self._mm = None
        self._bpp = None
        
    def initialize(self):
        fb_name = os.path.basename(self.fbdev)
        sys_base = f"/sys/class/graphics/{fb_name}"
        
        # Читаем BPP
        self._bpp = int(open(f"{sys_base}/bits_per_pixel", "r").read().strip())
        print(f"✓ BPP: {self._bpp}")
        
        # Открываем framebuffer
        self._fd = os.open(self.fbdev, os.O_RDWR)
        bpp_bytes = self._bpp // 8
        length = self.width * self.height * bpp_bytes
        self._mm = mmap.mmap(self._fd, length, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
        print(f"✓ Framebuffer открыт: {self.width}x{self.height}")
        
    def display(self, img):
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        if img.size != (self.width, self.height):
            img = img.resize((self.width, self.height))
        
        # Конвертируем в формат framebuffer
        if self._bpp == 32:
            raw = img.tobytes("raw", "BGRX")
        elif self._bpp == 24:
            raw = img.tobytes("raw", "BGR")
        elif self._bpp == 16:
            # RGB565
            r, g, b = img.split()
            r = r.point(lambda i: (i >> 3) & 0x1F)
            g = g.point(lambda i: (i >> 2) & 0x3F)
            b = b.point(lambda i: (i >> 3) & 0x1F)
            
            import array
            rr = array.array("B", r.tobytes())
            gg = array.array("B", g.tobytes())
            bb = array.array("B", b.tobytes())
            out = bytearray(self.width * self.height * 2)
            j = 0
            for i in range(self.width * self.height):
                v = (rr[i] << 11) | (gg[i] << 5) | bb[i]
                out[j] = v & 0xFF
                out[j + 1] = (v >> 8) & 0xFF
                j += 2
            raw = bytes(out)
        else:
            raise ValueError(f"Unsupported BPP: {self._bpp}")
        
        self._mm.seek(0)
        self._mm.write(raw)
        
    def close(self):
        if self._mm:
            self._mm.close()
        if self._fd:
            os.close(self._fd)


def draw_face(width, height, frame_idx):
    """Рисует простое анимированное лицо"""
    import math
    
    # Создаем изображение
    img = Image.new("RGB", (width, height), (20, 20, 40))  # Темно-синий фон
    draw = ImageDraw.Draw(img)
    
    # Анимация: легкое движение
    progress = (frame_idx % 20) / 20.0  # 20 кадров цикл
    eye_offset_y = int(math.sin(progress * 2 * math.pi) * 5)
    pupil_offset_x = int(math.sin(progress * 2 * math.pi) * 8)
    
    # Центр лица
    center_x = width // 2
    center_y = height // 2
    
    # Левый глаз
    eye_left_x = center_x - 80
    eye_left_y = center_y - 60 + eye_offset_y
    draw.ellipse((eye_left_x - 50, eye_left_y - 40, 
                  eye_left_x + 50, eye_left_y + 40), 
                 fill=(255, 255, 255))
    # Зрачок
    draw.ellipse((eye_left_x - 20 + pupil_offset_x, eye_left_y - 20,
                  eye_left_x + 20 + pupil_offset_x, eye_left_y + 20),
                 fill=(50, 50, 255))
    
    # Правый глаз
    eye_right_x = center_x + 80
    eye_right_y = center_y - 60 + eye_offset_y
    draw.ellipse((eye_right_x - 50, eye_right_y - 40,
                  eye_right_x + 50, eye_right_y + 40),
                 fill=(255, 255, 255))
    # Зрачок
    draw.ellipse((eye_right_x - 20 + pupil_offset_x, eye_right_y - 20,
                  eye_right_x + 20 + pupil_offset_x, eye_right_y + 20),
                 fill=(50, 50, 255))
    
    # Рот (улыбка)
    mouth_y = center_y + 60
    draw.arc((center_x - 80, mouth_y - 40, center_x + 80, mouth_y + 40),
             start=0, end=180, fill=(255, 255, 255), width=8)
    
    # Текст
    draw.text((center_x - 100, height - 60), f"Eva Frame {frame_idx}", 
              fill=(255, 255, 255))
    
    return img


async def test_animation():
    print("=" * 60)
    print("Тест анимации лица на framebuffer")
    print("=" * 60)
    
    display = SimpleFbdevDisplay()
    display.initialize()
    
    print("\n🎬 Запуск анимации (5 секунд, ~12 FPS)...")
    print("   Смотрите на мини дисплей!")
    
    frame_idx = 0
    for _ in range(60):  # 60 кадров = ~5 секунд
        img = draw_face(480, 640, frame_idx)
        display.display(img)
        frame_idx += 1
        await asyncio.sleep(0.08)  # ~12.5 FPS
    
    print("\n✅ Анимация завершена!")
    print("   Если вы ВИДЕЛИ лицо - дисплей работает!")
    print("   Если НЕТ - проблема в драйвере/подключении дисплея.")
    
    display.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_animation())
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

