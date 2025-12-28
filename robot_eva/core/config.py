"""
Конфигурация робота Eva
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Класс для управления конфигурацией робота"""
    
    def __init__(self, config_path: str = None, gpio_mapping_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config.yaml"
            )
        self.config_path = config_path
        
        if gpio_mapping_path is None:
            gpio_mapping_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "gpio_mapping.yaml"
            )
        self.gpio_mapping_path = gpio_mapping_path
        
        self._config = self._load_config()
        self._gpio_mapping = self._load_gpio_mapping()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из YAML файла"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def _load_gpio_mapping(self) -> Dict[str, Any]:
        """Загружает маппинг GPIO из YAML файла"""
        if os.path.exists(self.gpio_mapping_path):
            with open(self.gpio_mapping_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получает значение конфигурации по ключу (поддерживает вложенные ключи через точку)"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """Устанавливает значение конфигурации"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def save(self):
        """Сохраняет конфигурацию в файл"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
    
    def get_gpio_mapping(self, key: str = None, default: Any = None) -> Any:
        """
        Получает значение из маппинга GPIO
        
        Args:
            key: Ключ (поддерживает вложенные ключи через точку), если None - возвращает весь маппинг
            default: Значение по умолчанию
            
        Returns:
            Значение из маппинга GPIO
        """
        if key is None:
            return self._gpio_mapping
        
        keys = key.split('.')
        value = self._gpio_mapping
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default
    
    def get_i2c_device(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Получает конфигурацию I2C устройства"""
        return self.get_gpio_mapping(f"i2c.{device_name}")
    
    def get_servo_config(self, servo_name: str) -> Optional[Dict[str, Any]]:
        """Получает конфигурацию сервопривода"""
        return self.get_gpio_mapping(f"servos.{servo_name}")
    
    def get_serial_device(self, device_name: str) -> Optional[Dict[str, Any]]:
        """Получает конфигурацию последовательного устройства"""
        return self.get_gpio_mapping(f"serial.{device_name}")

