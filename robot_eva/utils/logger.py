"""
Настройка логирования
"""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "robot_eva", level: int = logging.INFO) -> logging.Logger:
    """
    Настройка логгера
    
    Args:
        name: Имя логгера
        level: Уровень логирования
        
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    log_file = Path(__file__).parent.parent.parent / "robot_eva.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

