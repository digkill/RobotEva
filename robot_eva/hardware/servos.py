"""
Управление сервоприводами через PCA9685
"""
import logging
from typing import Optional
from adafruit_servokit import ServoKit


class ServoController:
    """Контроллер сервоприводов через PCA9685"""
    
    # Определение сервоприводов
    SERVO_HEAD_PITCH = 0      # Наклон головы (вверх/вниз)
    SERVO_HEAD_YAW = 1        # Поворот головы (влево/вправо)
    SERVO_NECK_PITCH = 2      # Наклон шеи
    SERVO_LEFT_ARM = 3        # Левая рука
    SERVO_RIGHT_ARM = 4       # Правая рука
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.kit: Optional[ServoKit] = None
        self.i2c_address = config.get("hardware.servos.i2c_address", 0x40)
        self.frequency = config.get("hardware.servos.frequency", 50)
        
        # Ограничения углов для каждого сервопривода
        self.angle_limits = {
            self.SERVO_HEAD_PITCH: (0, 180),
            self.SERVO_HEAD_YAW: (0, 180),
            self.SERVO_NECK_PITCH: (0, 180),
            self.SERVO_LEFT_ARM: (0, 180),
            self.SERVO_RIGHT_ARM: (0, 180),
        }
        
        # Текущие позиции
        self.current_positions = {
            self.SERVO_HEAD_PITCH: 90,
            self.SERVO_HEAD_YAW: 90,
            self.SERVO_NECK_PITCH: 90,
            self.SERVO_LEFT_ARM: 90,
            self.SERVO_RIGHT_ARM: 90,
        }
    
    async def initialize(self):
        """Инициализация контроллера сервоприводов"""
        try:
            self.kit = ServoKit(channels=16, address=self.i2c_address, frequency=self.frequency)
            self.logger.info("Сервоконтроллер PCA9685 инициализирован")
            
            # Установка начальных позиций
            await self.reset_to_center()
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации сервоконтроллера: {e}")
            raise
    
    async def move(self, servo_id: int, angle: float, duration: float = 0.5):
        """
        Перемещение сервопривода на заданный угол
        
        Args:
            servo_id: ID сервопривода
            angle: Угол в градусах (0-180)
            duration: Время движения в секундах
        """
        if self.kit is None:
            self.logger.warning("Сервоконтроллер не инициализирован")
            return
        
        # Ограничение угла
        min_angle, max_angle = self.angle_limits.get(servo_id, (0, 180))
        angle = max(min_angle, min(max_angle, angle))
        
        try:
            self.kit.servo[servo_id].angle = angle
            self.current_positions[servo_id] = angle
            self.logger.debug(f"Сервопривод {servo_id} перемещен на угол {angle}°")
        except Exception as e:
            self.logger.error(f"Ошибка перемещения сервопривода {servo_id}: {e}")
    
    async def move_smooth(self, servo_id: int, target_angle: float, steps: int = 10, delay: float = 0.05):
        """Плавное перемещение сервопривода"""
        import asyncio
        
        current_angle = self.current_positions.get(servo_id, 90)
        step_size = (target_angle - current_angle) / steps
        
        for i in range(steps):
            angle = current_angle + step_size * (i + 1)
            await self.move(servo_id, angle)
            await asyncio.sleep(delay)
    
    async def nod_head(self, times: int = 1):
        """Кивание головой"""
        import asyncio
        
        for _ in range(times):
            await self.move_smooth(self.SERVO_HEAD_PITCH, 110, steps=5)
            await asyncio.sleep(0.3)
            await self.move_smooth(self.SERVO_HEAD_PITCH, 70, steps=5)
            await asyncio.sleep(0.3)
            await self.move_smooth(self.SERVO_HEAD_PITCH, 90, steps=5)
            await asyncio.sleep(0.5)
    
    async def shake_head(self, times: int = 1):
        """Покачивание головой (нет)"""
        import asyncio
        
        for _ in range(times):
            await self.move_smooth(self.SERVO_HEAD_YAW, 120, steps=5)
            await asyncio.sleep(0.2)
            await self.move_smooth(self.SERVO_HEAD_YAW, 60, steps=5)
            await asyncio.sleep(0.2)
            await self.move_smooth(self.SERVO_HEAD_YAW, 90, steps=5)
            await asyncio.sleep(0.3)
    
    async def wave_arms(self, times: int = 1):
        """Махание руками"""
        import asyncio
        
        for _ in range(times):
            await self.move_smooth(self.SERVO_LEFT_ARM, 150, steps=8)
            await self.move_smooth(self.SERVO_RIGHT_ARM, 30, steps=8)
            await asyncio.sleep(0.3)
            await self.move_smooth(self.SERVO_LEFT_ARM, 30, steps=8)
            await self.move_smooth(self.SERVO_RIGHT_ARM, 150, steps=8)
            await asyncio.sleep(0.3)
            await self.move_smooth(self.SERVO_LEFT_ARM, 90, steps=8)
            await self.move_smooth(self.SERVO_RIGHT_ARM, 90, steps=8)
            await asyncio.sleep(0.5)
    
    async def reset_to_center(self):
        """Сброс всех сервоприводов в центральное положение"""
        for servo_id in self.current_positions.keys():
            await self.move(servo_id, 90)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.kit:
            await self.reset_to_center()
            self.logger.info("Сервоконтроллер остановлен")

