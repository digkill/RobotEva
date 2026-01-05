#!/usr/bin/env python3
"""
Тест отображения на DSI дисплее через framebuffer
"""
import os
import sys
import mmap
from PIL import Image, ImageDraw, ImageFont

def test_framebuffer():
    fbdev = "/dev/fb0"
    
    print(f"Проверка {fbdev}...")
    if not os.path.exists(fbdev):
        print(f"❌ {fbdev} не найден!")
        return False
    
    # Читаем параметры fb
    fb_name = os.path.basename(fbdev)
    sys_base = f"/sys/class/graphics/{fb_name}"
    
    try:
        vs = open(f"{sys_base}/virtual_size", "r").read().strip()
        w_str, h_str = vs.split(",")
        fb_width, fb_height = int(w_str), int(h_str)
        print(f"✓ Размер framebuffer: {fb_width}x{fb_height}")
    except Exception as e:
        print(f"❌ Ошибка чтения размера: {e}")
        return False
    
    try:
        bpp = int(open(f"{sys_base}/bits_per_pixel", "r").read().strip())
        print(f"✓ BPP: {bpp}")
    except Exception as e:
        print(f"❌ Ошибка чтения BPP: {e}")
        return False
    
    # Создаем тестовое изображение
    print("\nСоздаем тестовое изображение...")
    img = Image.new("RGB", (fb_width, fb_height), (0, 0, 128))  # Синий фон
    draw = ImageDraw.Draw(img)
    
    # Рисуем лицо
    # Глаза
    eye_size = 80
    eye_y = fb_height // 3
    draw.ellipse((fb_width // 3 - eye_size, eye_y - eye_size // 2, 
                  fb_width // 3 + eye_size, eye_y + eye_size // 2), 
                 fill=(255, 255, 255))
    draw.ellipse((2 * fb_width // 3 - eye_size, eye_y - eye_size // 2,
                  2 * fb_width // 3 + eye_size, eye_y + eye_size // 2),
                 fill=(255, 255, 255))
    
    # Зрачки
    pupil_size = 30
    draw.ellipse((fb_width // 3 - pupil_size // 2, eye_y - pupil_size // 2,
                  fb_width // 3 + pupil_size // 2, eye_y + pupil_size // 2),
                 fill=(0, 0, 0))
    draw.ellipse((2 * fb_width // 3 - pupil_size // 2, eye_y - pupil_size // 2,
                  2 * fb_width // 3 + pupil_size // 2, eye_y + pupil_size // 2),
                 fill=(0, 0, 0))
    
    # Рот (улыбка)
    mouth_y = 2 * fb_height // 3
    draw.arc((fb_width // 3, mouth_y - 40, 2 * fb_width // 3, mouth_y + 40),
             start=0, end=180, fill=(255, 255, 255), width=8)
    
    # Текст
    draw.text((fb_width // 2 - 100, fb_height - 80), "Eva Test Display", 
              fill=(255, 255, 255))
    
    print("✓ Тестовое изображение создано")
    
    # Записываем в framebuffer
    print("\nЗапись в framebuffer...")
    try:
        fd = os.open(fbdev, os.O_RDWR)
        bpp_bytes = bpp // 8
        length = fb_width * fb_height * bpp_bytes
        mm = mmap.mmap(fd, length, mmap.MAP_SHARED, mmap.PROT_WRITE | mmap.PROT_READ)
        
        # Конвертируем изображение
        if bpp == 32:
            raw = img.tobytes("raw", "BGRX")
        elif bpp == 24:
            raw = img.tobytes("raw", "BGR")
        elif bpp == 16:
            # RGB565
            r, g, b = img.split()
            r = r.point(lambda i: (i >> 3) & 0x1F)
            g = g.point(lambda i: (i >> 2) & 0x3F)
            b = b.point(lambda i: (i >> 3) & 0x1F)
            
            import array
            rr = array.array("B", r.tobytes())
            gg = array.array("B", g.tobytes())
            bb = array.array("B", b.tobytes())
            out = bytearray(fb_width * fb_height * 2)
            j = 0
            for i in range(fb_width * fb_height):
                v = (rr[i] << 11) | (gg[i] << 5) | bb[i]
                out[j] = v & 0xFF
                out[j + 1] = (v >> 8) & 0xFF
                j += 2
            raw = bytes(out)
        else:
            print(f"❌ Неподдерживаемый BPP: {bpp}")
            return False
        
        mm.seek(0)
        mm.write(raw)
        mm.close()
        os.close(fd)
        
        print("✅ Изображение записано в framebuffer!")
        print("\n🎨 Если вы видите лицо на дисплее - всё работает!")
        print("   Если экран черный/пустой - проблема с драйвером дисплея.")
        return True
        
    except PermissionError:
        print(f"❌ Нет доступа к {fbdev}. Запустите с sudo или добавьте пользователя в группу video")
        return False
    except Exception as e:
        print(f"❌ Ошибка записи: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Тест DSI дисплея Robot Eva")
    print("=" * 60)
    success = test_framebuffer()
    sys.exit(0 if success else 1)

