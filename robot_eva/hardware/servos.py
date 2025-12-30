"""
Управление сервоприводами через PCA9685
"""
import logging
from typing import Optional, Any
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

        # Read servo mapping/ranges from gpio_mapping.yaml (servos.*)
        # This matters for both PCA9685 and MQTT (ESP32) when wiring differs.
        head_yaw_cfg = config.get_servo_config("head_yaw") or {}
        head_pitch_cfg = config.get_servo_config("head_pitch") or {}
        neck_pitch_cfg = config.get_servo_config("neck_pitch") or {}
        left_arm_cfg = config.get_servo_config("left_arm") or {}
        right_arm_cfg = config.get_servo_config("right_arm") or {}

        try:
            self.SERVO_HEAD_YAW = int(head_yaw_cfg.get("channel", self.SERVO_HEAD_YAW))
        except Exception:
            pass
        try:
            self.SERVO_HEAD_PITCH = int(head_pitch_cfg.get("channel", self.SERVO_HEAD_PITCH))
        except Exception:
            pass
        try:
            self.SERVO_NECK_PITCH = int(neck_pitch_cfg.get("channel", self.SERVO_NECK_PITCH))
        except Exception:
            pass
        try:
            self.SERVO_LEFT_ARM = int(left_arm_cfg.get("channel", self.SERVO_LEFT_ARM))
        except Exception:
            pass
        try:
            self.SERVO_RIGHT_ARM = int(right_arm_cfg.get("channel", self.SERVO_RIGHT_ARM))
        except Exception:
            pass
        
        # Получение конфигурации из GPIO маппинга
        pca9685_config = config.get_i2c_device("pca9685")
        if pca9685_config:
            self.i2c_address = pca9685_config.get("address", 0x40)
            self.frequency = pca9685_config.get("frequency", 50)
        else:
            # Fallback на старую конфигурацию
            self.i2c_address = config.get("hardware.servos.i2c_address", 0x40)
            self.frequency = config.get("hardware.servos.frequency", 50)
        
        # Ограничения углов для каждого сервопривода
        def _limits(cfg, fallback=(0, 180)):
            try:
                return (float(cfg.get("min_angle", fallback[0])), float(cfg.get("max_angle", fallback[1])))
            except Exception:
                return fallback

        self.angle_limits = {
            self.SERVO_HEAD_PITCH: _limits(head_pitch_cfg),
            self.SERVO_HEAD_YAW: _limits(head_yaw_cfg),
            self.SERVO_NECK_PITCH: _limits(neck_pitch_cfg),
            self.SERVO_LEFT_ARM: _limits(left_arm_cfg),
            self.SERVO_RIGHT_ARM: _limits(right_arm_cfg),
        }
        
        # Текущие позиции
        def _default(cfg, fallback=90):
            try:
                return float(cfg.get("default_angle", fallback))
            except Exception:
                return float(fallback)

        self.current_positions = {
            self.SERVO_HEAD_PITCH: _default(head_pitch_cfg),
            self.SERVO_HEAD_YAW: _default(head_yaw_cfg),
            self.SERVO_NECK_PITCH: _default(neck_pitch_cfg),
            self.SERVO_LEFT_ARM: _default(left_arm_cfg),
            self.SERVO_RIGHT_ARM: _default(right_arm_cfg),
        }
    
    async def initialize(self):
        """Инициализация контроллера сервоприводов"""
        # Проверка доступности I2C устройства
        if not await self._check_i2c_device():
            self.logger.warning("PCA9685 не обнаружен на I2C шине. Продолжение без сервоприводов.")
            self.kit = None
            return
        
        try:
            self.kit = ServoKit(channels=16, address=self.i2c_address, frequency=self.frequency)
            self.logger.info(f"Сервоконтроллер PCA9685 инициализирован (адрес: 0x{self.i2c_address:02X})")
            
            # Установка начальных позиций
            await self.reset_to_center()
            
        except BlockingIOError as e:
            self.logger.warning(f"I2C шина занята или устройство недоступно: {e}")
            self.logger.warning("Продолжение без сервоприводов. Проверьте подключение PCA9685.")
            self.kit = None
        except Exception as e:
            self.logger.warning(f"Ошибка инициализации сервоконтроллера: {e}")
            self.logger.warning("Продолжение без сервоприводов.")
            self.kit = None
    
    async def _check_i2c_device(self) -> bool:
        """Проверка наличия устройства на I2C шине"""
        try:
            import subprocess
            result = subprocess.run(
                ["i2cdetect", "-y", "1"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Поиск адреса в выводе
                address_str = f"{self.i2c_address:02x}"
                return address_str in result.stdout.lower()
            return False
        except Exception as e:
            self.logger.debug(f"Не удалось проверить I2C устройство: {e}")
            return False
    
    async def move(self, servo_id: int, angle: float, duration: float = 0.5):
        """
        Перемещение сервопривода на заданный угол
        
        Args:
            servo_id: ID сервопривода
            angle: Угол в градусах (0-180)
            duration: Время движения в секундах
        """
        if self.kit is None:
            self.logger.debug("Сервоконтроллер не инициализирован, команда игнорируется")
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
        for servo_id, angle in list(self.current_positions.items()):
            await self.move(servo_id, angle)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.kit:
            await self.reset_to_center()
            self.logger.info("Сервоконтроллер остановлен")


class MqttServoController:
    """
    Контроллер сервоприводов через MQTT (команды выполняет ESP32).

    Topic: <topic_base>/set
    Payload (строка): "<servo_id>,<angle>"
      пример: "0,90"
    """

    # Те же ID, что и в ServoController
    SERVO_HEAD_PITCH = 0
    SERVO_HEAD_YAW = 1
    SERVO_NECK_PITCH = 2
    SERVO_LEFT_ARM = 3
    SERVO_RIGHT_ARM = 4

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Read servo mapping/ranges from gpio_mapping.yaml (servos.*)
        head_yaw_cfg = config.get_servo_config("head_yaw") or {}
        head_pitch_cfg = config.get_servo_config("head_pitch") or {}
        neck_pitch_cfg = config.get_servo_config("neck_pitch") or {}
        left_arm_cfg = config.get_servo_config("left_arm") or {}
        right_arm_cfg = config.get_servo_config("right_arm") or {}

        try:
            self.SERVO_HEAD_YAW = int(head_yaw_cfg.get("channel", self.SERVO_HEAD_YAW))
        except Exception:
            pass
        try:
            self.SERVO_HEAD_PITCH = int(head_pitch_cfg.get("channel", self.SERVO_HEAD_PITCH))
        except Exception:
            pass
        try:
            self.SERVO_NECK_PITCH = int(neck_pitch_cfg.get("channel", self.SERVO_NECK_PITCH))
        except Exception:
            pass
        try:
            self.SERVO_LEFT_ARM = int(left_arm_cfg.get("channel", self.SERVO_LEFT_ARM))
        except Exception:
            pass
        try:
            self.SERVO_RIGHT_ARM = int(right_arm_cfg.get("channel", self.SERVO_RIGHT_ARM))
        except Exception:
            pass

        # MQTT конфиг: сначала hardware.servos.mqtt, иначе fallback на services.smart_home.mqtt
        mqtt_cfg = config.get("hardware.servos.mqtt", {}) or {}
        if not mqtt_cfg:
            mqtt_cfg = config.get("services.smart_home.mqtt", {}) or {}

        self.mqtt_enabled: bool = bool(mqtt_cfg.get("enabled", True))
        self.mqtt_host: str = mqtt_cfg.get("host", "localhost")
        self.mqtt_port: int = int(mqtt_cfg.get("port", 1883))
        self.mqtt_username: str = mqtt_cfg.get("username") or ""
        self.mqtt_password: str = mqtt_cfg.get("password") or ""
        self.mqtt_client_id: str = mqtt_cfg.get("client_id", "eva-servo-publisher")
        self.topic_base: str = mqtt_cfg.get("topic_base", "robot_eva/servos")
        self.qos: int = int(mqtt_cfg.get("qos", 0))
        self.retain: bool = bool(mqtt_cfg.get("retain", False))

        self._client = None

        # Ограничения углов (совместимо с текущей логикой)
        def _limits(cfg, fallback=(0, 180)):
            try:
                return (float(cfg.get("min_angle", fallback[0])), float(cfg.get("max_angle", fallback[1])))
            except Exception:
                return fallback

        def _default(cfg, fallback=90):
            try:
                return float(cfg.get("default_angle", fallback))
            except Exception:
                return float(fallback)

        self.angle_limits = {
            self.SERVO_HEAD_PITCH: _limits(head_pitch_cfg),
            self.SERVO_HEAD_YAW: _limits(head_yaw_cfg),
            self.SERVO_NECK_PITCH: _limits(neck_pitch_cfg),
            self.SERVO_LEFT_ARM: _limits(left_arm_cfg),
            self.SERVO_RIGHT_ARM: _limits(right_arm_cfg),
        }
        self.current_positions = {
            self.SERVO_HEAD_PITCH: _default(head_pitch_cfg),
            self.SERVO_HEAD_YAW: _default(head_yaw_cfg),
            self.SERVO_NECK_PITCH: _default(neck_pitch_cfg),
            self.SERVO_LEFT_ARM: _default(left_arm_cfg),
            self.SERVO_RIGHT_ARM: _default(right_arm_cfg),
        }

    async def initialize(self):
        """Инициализация MQTT клиента (publish-only)"""
        if not self.mqtt_enabled:
            self.logger.info("MQTT сервоконтроллер отключён (hardware.servos.mqtt.enabled=false)")
            self._client = None
            return

        try:
            import paho.mqtt.client as mqtt

            self._client = mqtt.Client(client_id=self.mqtt_client_id)
            if self.mqtt_username:
                self._client.username_pw_set(self.mqtt_username, self.mqtt_password or None)

            self._client.connect(self.mqtt_host, self.mqtt_port)
            self._client.loop_start()

            self.logger.info(
                f"MQTT сервоконтроллер подключен ({self.mqtt_host}:{self.mqtt_port}), topic_base={self.topic_base}"
            )

            # Начальные позиции (как и у PCA9685)
            await self.reset_to_center()
        except Exception as e:
            self.logger.warning(f"Не удалось инициализировать MQTT сервоконтроллер: {e}")
            self._client = None

    async def move(self, servo_id: int, angle: float, duration: float = 0.5):
        """
        Публикация команды на перемещение сервопривода.
        duration сейчас игнорируется (плавность делаем на стороне Pi через move_smooth()).
        """
        if self._client is None:
            self.logger.debug("MQTT сервоконтроллер не инициализирован, команда игнорируется")
            return

        min_angle, max_angle = self.angle_limits.get(servo_id, (0, 180))
        angle = max(min_angle, min(max_angle, angle))

        topic = f"{self.topic_base}/set"
        payload = f"{int(servo_id)},{float(angle):.1f}"

        try:
            self._client.publish(topic, payload, qos=self.qos, retain=self.retain)
            self.current_positions[servo_id] = angle
            self.logger.debug(f"MQTT -> {topic} {payload}")
        except Exception as e:
            self.logger.error(f"Ошибка публикации команды сервопривода {servo_id}: {e}")

    async def move_smooth(self, servo_id: int, target_angle: float, steps: int = 10, delay: float = 0.05):
        """Плавное перемещение (выполняется на стороне Pi, шлём серию move())"""
        import asyncio

        current_angle = self.current_positions.get(servo_id, 90)
        step_size = (target_angle - current_angle) / steps if steps else 0

        for i in range(max(1, steps)):
            angle = current_angle + step_size * (i + 1)
            await self.move(servo_id, angle)
            await asyncio.sleep(delay)

    async def nod_head(self, times: int = 1):
        """Кивание головой"""
        import asyncio
        # If head_pitch is not mapped (or equals yaw), skip to avoid weird motion.
        if self.SERVO_HEAD_PITCH == self.SERVO_HEAD_YAW:
            return
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
        for servo_id, angle in list(self.current_positions.items()):
            await self.move(servo_id, angle)

    async def cleanup(self):
        """Очистка ресурсов"""
        if self._client:
            try:
                await self.reset_to_center()
            except Exception:
                pass

            try:
                self._client.loop_stop()
            except Exception:
                pass
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self.logger.info("MQTT сервоконтроллер остановлен")


def create_servo_controller(config) -> Any:
    """
    Фабрика контроллера сервоприводов.

    hardware.servos.backend:
      - "pca9685" (default)
      - "mqtt"
    """
    backend = (config.get("hardware.servos.backend", "pca9685") or "pca9685").lower()
    if backend == "mqtt":
        return MqttServoController(config)
    return ServoController(config)

