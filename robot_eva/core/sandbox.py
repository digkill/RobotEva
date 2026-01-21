"""
Безопасная песочница для выполнения кода, сгенерированного роботом
"""
import logging
import ast
import sys
import os
import tempfile
import subprocess
import asyncio
from typing import Dict, Any, Optional, List, Tuple
import importlib.util
import traceback


class CodeSandbox:
    """Безопасная песочница для выполнения Python кода"""
    
    # Запрещённые операции
    FORBIDDEN_IMPORTS = {
        'os', 'sys', 'subprocess', 'shutil', 'socket', 'multiprocessing',
        'threading', 'ctypes', 'cffi', '__builtin__', 'builtins',
        'importlib', 'imp', 'pkgutil', 'pydoc', 'doctest'
    }
    
    FORBIDDEN_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__', 'open', 'file',
        'input', 'raw_input', 'exit', 'quit', 'reload'
    }
    
    FORBIDDEN_ATTRIBUTES = {
        '__dict__', '__class__', '__bases__', '__subclasses__',
        '__globals__', '__code__', '__func__', '__self__'
    }
    
    def __init__(self, config, storage_path: str = "/home/pi/Projects/RobotEva/data/sandbox"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path
        
        # История выполнения кода
        self.execution_history: List[Dict] = []
        
        # Разрешённые модули для импорта
        self.allowed_imports = {
            'math', 'random', 'time', 'datetime', 'json', 'collections',
            'itertools', 'functools', 'operator', 'string', 're',
            'numpy', 'cv2', 'asyncio'
        }
        
        # Создаём директорию для песочницы
        os.makedirs(self.storage_path, exist_ok=True)
    
    def validate_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Валидация кода перед выполнением
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # Парсим код в AST
            tree = ast.parse(code)
            
            # Проверяем на запрещённые операции
            for node in ast.walk(tree):
                # Проверяем импорты
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.split('.')[0] in self.FORBIDDEN_IMPORTS:
                                return False, f"Запрещённый импорт: {alias.name}"
                    else:  # ImportFrom
                        if node.module and node.module.split('.')[0] in self.FORBIDDEN_IMPORTS:
                            return False, f"Запрещённый импорт: {node.module}"
                
                # Проверяем вызовы функций
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.FORBIDDEN_FUNCTIONS:
                            return False, f"Запрещённая функция: {node.func.id}"
                    elif isinstance(node.func, ast.Attribute):
                        if node.func.attr in self.FORBIDDEN_FUNCTIONS:
                            return False, f"Запрещённый атрибут: {node.func.attr}"
                
                # Проверяем доступ к атрибутам
                if isinstance(node, ast.Attribute):
                    if node.attr in self.FORBIDDEN_ATTRIBUTES:
                        return False, f"Запрещённый атрибут: {node.attr}"
            
            return True, None
            
        except SyntaxError as e:
            return False, f"Синтаксическая ошибка: {e}"
        except Exception as e:
            return False, f"Ошибка валидации: {e}"
    
    async def execute_code(
        self,
        code: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Выполнение кода в безопасной среде
        
        Args:
            code: Python код для выполнения
            context: Контекст (переменные, функции) доступные в коде
            timeout: Максимальное время выполнения (секунды)
        
        Returns:
            (success, result, error_message)
        """
        # Валидация кода
        is_valid, error = self.validate_code(code)
        if not is_valid:
            return False, None, error
        
        # Создаём безопасный контекст
        safe_context = {
            '__builtins__': {
                'len': len, 'str': str, 'int': int, 'float': float,
                'bool': bool, 'list': list, 'dict': dict, 'tuple': tuple,
                'set': set, 'range': range, 'enumerate': enumerate,
                'zip': zip, 'min': min, 'max': max, 'sum': sum,
                'abs': abs, 'round': round, 'print': print,
                'True': True, 'False': False, 'None': None
            },
            '__name__': '__sandbox__',
            '__file__': '<sandbox>'
        }
        
        # Добавляем разрешённые модули
        for module_name in self.allowed_imports:
            try:
                safe_context[module_name] = __import__(module_name)
            except ImportError:
                pass
        
        # Добавляем пользовательский контекст
        if context:
            safe_context.update(context)
        
        # Сохраняем код в файл для истории
        code_file = os.path.join(self.storage_path, f"code_{len(self.execution_history)}.py")
        try:
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            self.logger.warning(f"Не удалось сохранить код: {e}")
        
        # Выполняем код с таймаутом
        try:
            result = await asyncio.wait_for(
                self._execute_safe(code, safe_context),
                timeout=timeout
            )
            
            # Сохраняем в историю
            self.execution_history.append({
                "code": code,
                "success": True,
                "result": str(result),
                "timestamp": asyncio.get_event_loop().time()
            })
            
            return True, result, None
            
        except asyncio.TimeoutError:
            error_msg = f"Таймаут выполнения ({timeout}с)"
            self.execution_history.append({
                "code": code,
                "success": False,
                "error": error_msg,
                "timestamp": asyncio.get_event_loop().time()
            })
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Ошибка выполнения: {str(e)}"
            self.logger.warning(f"Ошибка выполнения кода: {e}")
            self.execution_history.append({
                "code": code,
                "success": False,
                "error": error_msg,
                "timestamp": asyncio.get_event_loop().time()
            })
            return False, None, error_msg
    
    async def _execute_safe(self, code: str, context: Dict) -> Any:
        """Безопасное выполнение кода"""
        # Компилируем код
        compiled = compile(code, '<sandbox>', 'exec')
        
        # Выполняем в отдельном потоке для безопасности
        def run_code():
            exec(compiled, context)
            return context.get('result', None)
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_code)
        return result
    
    def get_execution_history(self, limit: int = 50) -> List[Dict]:
        """Получить историю выполнения"""
        return self.execution_history[-limit:]
    
    def clear_history(self):
        """Очистить историю выполнения"""
        self.execution_history.clear()
        self.logger.info("История выполнения очищена")
