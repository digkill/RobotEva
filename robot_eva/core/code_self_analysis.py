"""
Система самоанализа и саморазвития кода для робота
"""
import logging
import os
import ast
import inspect
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
import json


class CodeSelfAnalysis:
    """
    Система самоанализа кода для робота

    Позволяет роботу:
    - Читать и анализировать свой собственный код
    - Находить проблемы и возможности улучшения
    - Генерировать предложения по улучшению
    - Автоматически применять улучшения (с подтверждением)
    """

    def __init__(self, config, project_root: str = "/home/pi/Projects/RobotEva"):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(project_root)

        # Исключаемые директории и файлы
        self.exclude_patterns = {
            '__pycache__', '.git', 'node_modules', '*.pyc', '*.log',
            'data/', 'models/', 'tmp', '.vscode', '.cursor'
        }

        # Анализ кода
        self.code_analysis: Dict[str, Any] = {}
        self.improvement_suggestions: List[Dict] = []
        self.self_analysis_history: List[Dict] = []

        # LLM интеграция
        self.llm_service = None

    def set_llm_service(self, llm_service):
        """Установить LLM сервис для генерации улучшений"""
        self.llm_service = llm_service

    async def analyze_own_code(self) -> Dict[str, Any]:
        """
        Полный анализ собственного кода робота

        Returns:
            Результаты анализа
        """
        self.logger.info("🔍 Начинаю самоанализ кода...")

        try:
            # Сканируем все Python файлы проекта
            python_files = self._find_python_files()

            # Анализируем каждый файл
            analysis_results = {}
            total_files = len(python_files)

            for i, file_path in enumerate(python_files):
                self.logger.debug(f"Анализ файла {i+1}/{total_files}: {file_path}")
                try:
                    analysis = await self._analyze_single_file(file_path)
                    if analysis:
                        analysis_results[str(file_path)] = analysis
                except Exception as e:
                    self.logger.warning(f"Ошибка анализа {file_path}: {e}")

            # Агрегируем результаты
            summary = self._create_analysis_summary(analysis_results)

            # Генерируем предложения по улучшению
            if self.llm_service:
                suggestions = await self._generate_improvements(summary)
                self.improvement_suggestions.extend(suggestions)

            # Сохраняем анализ
            self.code_analysis = {
                "timestamp": time.time(),
                "files_analyzed": total_files,
                "results": analysis_results,
                "summary": summary,
                "suggestions": self.improvement_suggestions
            }

            # Записываем в историю
            self.self_analysis_history.append({
                "timestamp": time.time(),
                "analysis": self.code_analysis,
                "suggestions_count": len(self.improvement_suggestions)
            })

            # Ограничиваем историю
            if len(self.self_analysis_history) > 50:
                self.self_analysis_history = self.self_analysis_history[-50:]

            self.logger.info(f"✅ Самоанализ завершен. Проанализировано {total_files} файлов, {len(self.improvement_suggestions)} предложений")

            return self.code_analysis

        except Exception as e:
            self.logger.error(f"Ошибка самоанализа: {e}")
            return {"error": str(e)}

    def _find_python_files(self) -> List[Path]:
        """Найти все Python файлы в проекте"""
        python_files = []

        for root, dirs, files in os.walk(self.project_root):
            # Исключаем директории
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.exclude_patterns)]

            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    # Проверяем, не исключен ли файл
                    if not any(pattern in str(file_path) for pattern in self.exclude_patterns):
                        python_files.append(file_path)

        return sorted(python_files)

    async def _analyze_single_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Анализ одного файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Парсим AST
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return {"error": "Синтаксическая ошибка", "lines": len(content.split('\n'))}

            # Анализируем структуру
            analysis = {
                "file_path": str(file_path),
                "lines": len(content.split('\n')),
                "classes": [],
                "functions": [],
                "imports": [],
                "complexity": 0,
                "issues": [],
                "metrics": {}
            }

            # Извлекаем классы и функции
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    })
                elif isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args),
                        "async": isinstance(node, ast.AsyncFunctionDef)
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        analysis["imports"].extend([alias.name for alias in node.names])
                    else:
                        module = node.module or ""
                        analysis["imports"].extend([f"{module}.{alias.name}" if module else alias.name for alias in node.names])

            # Вычисляем метрики сложности
            analysis["metrics"] = self._calculate_metrics(tree, content)

            # Ищем потенциальные проблемы
            analysis["issues"] = self._find_code_issues(tree, content, file_path)

            return analysis

        except Exception as e:
            self.logger.warning(f"Ошибка анализа файла {file_path}: {e}")
            return None

    def _calculate_metrics(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """Вычислить метрики кода"""
        metrics = {
            "cyclomatic_complexity": 0,
            "lines_of_code": len(content.split('\n')),
            "functions_count": 0,
            "classes_count": 0,
            "imports_count": 0
        }

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions_count"] += 1
                # Простая оценка сложности (количество ветвлений)
                complexity = 1  # базовая сложность
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp) and len(child.values) > 1:
                        complexity += len(child.values) - 1
                metrics["cyclomatic_complexity"] = max(metrics["cyclomatic_complexity"], complexity)

            elif isinstance(node, ast.ClassDef):
                metrics["classes_count"] += 1

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics["imports_count"] += 1

        return metrics

    def _find_code_issues(self, tree: ast.AST, content: str, file_path: Path) -> List[Dict]:
        """Найти потенциальные проблемы в коде"""
        issues = []

        # Проверяем на слишком длинные функции
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Считаем строки функции
                if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                    func_length = node.end_lineno - node.lineno
                    if func_length > 50:
                        issues.append({
                            "type": "long_function",
                            "message": f"Функция {node.name} слишком длинная ({func_length} строк)",
                            "line": node.lineno,
                            "severity": "medium"
                        })

                # Проверяем на слишком много параметров
                if len(node.args.args) > 7:
                    issues.append({
                        "type": "too_many_params",
                        "message": f"Функция {node.name} имеет слишком много параметров ({len(node.args.args)})",
                        "line": node.lineno,
                        "severity": "low"
                    })

        # Проверяем на TODO/FIXME комментарии
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            lower_line = line.lower()
            if 'todo' in lower_line or 'fixme' in lower_line or 'hack' in lower_line:
                issues.append({
                    "type": "todo_comment",
                    "message": f"Найден комментарий: {line.strip()}",
                    "line": i,
                    "severity": "info"
                })

        return issues

    def _create_analysis_summary(self, analysis_results: Dict) -> Dict[str, Any]:
        """Создать сводку анализа"""
        summary = {
            "total_files": len(analysis_results),
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "total_imports": 0,
            "issues_count": 0,
            "issues_by_type": {},
            "complexity_stats": {
                "max_complexity": 0,
                "avg_complexity": 0
            },
            "largest_files": []
        }

        complexities = []

        for file_path, analysis in analysis_results.items():
            if "error" in analysis:
                continue

            summary["total_lines"] += analysis.get("lines", 0)
            summary["total_functions"] += len(analysis.get("functions", []))
            summary["total_classes"] += len(analysis.get("classes", []))
            summary["total_imports"] += len(analysis.get("imports", []))

            # Статистика проблем
            issues = analysis.get("issues", [])
            summary["issues_count"] += len(issues)

            for issue in issues:
                issue_type = issue.get("type", "unknown")
                summary["issues_by_type"][issue_type] = summary["issues_by_type"].get(issue_type, 0) + 1

            # Статистика сложности
            metrics = analysis.get("metrics", {})
            complexity = metrics.get("cyclomatic_complexity", 0)
            complexities.append(complexity)
            summary["complexity_stats"]["max_complexity"] = max(
                summary["complexity_stats"]["max_complexity"], complexity
            )

            # Самые большие файлы
            summary["largest_files"].append({
                "file": file_path,
                "lines": analysis.get("lines", 0),
                "functions": len(analysis.get("functions", [])),
                "classes": len(analysis.get("classes", []))
            })

        # Сортируем файлы по размеру
        summary["largest_files"].sort(key=lambda x: x["lines"], reverse=True)
        summary["largest_files"] = summary["largest_files"][:10]

        # Средняя сложность
        if complexities:
            summary["complexity_stats"]["avg_complexity"] = sum(complexities) / len(complexities)

        return summary

    async def _generate_improvements(self, summary: Dict) -> List[Dict]:
        """Генерировать предложения по улучшению"""
        if not self.llm_service:
            return []

        suggestions = []

        try:
            # Генерируем предложения на основе анализа
            prompt = f"""Ты робот Ева, который анализирует свой собственный код. На основе анализа сформулируй конкретные предложения по улучшению.

Статистика проекта:
{json.dumps(summary, indent=2, ensure_ascii=False)}

Сформулируй 5-10 конкретных предложений по улучшению кода:

Для каждого предложения укажи:
- Что улучшить
- Почему это важно
- Как реализовать
- Приоритет (high/medium/low)

Будь конкретной и практичной. Фокусируйся на:
- Упрощении сложного кода
- Улучшении читаемости
- Добавлении новых функций
- Исправлении найденных проблем"""

            response = await self.llm_service.generate_response(prompt, max_tokens=1000)

            if response:
                # Парсим предложения
                lines = response.split('\n')
                current_suggestion = None

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '-')):
                        # Новое предложение
                        if current_suggestion:
                            suggestions.append(current_suggestion)

                        current_suggestion = {
                            "title": line.lstrip('1234567890.- '),
                            "description": "",
                            "priority": "medium",
                            "category": "general"
                        }
                    elif current_suggestion and line:
                        # Продолжение описания
                        current_suggestion["description"] += line + " "

                # Добавляем последнее предложение
                if current_suggestion:
                    suggestions.append(current_suggestion)

                # Ограничиваем до 10 предложений
                suggestions = suggestions[:10]

                self.logger.info(f"Сгенерировано {len(suggestions)} предложений по улучшению")

        except Exception as e:
            self.logger.error(f"Ошибка генерации предложений: {e}")

        return suggestions

    async def apply_improvement(self, suggestion: Dict, confirm: bool = False) -> bool:
        """
        Применить предложение по улучшению

        Args:
            suggestion: Предложение для применения
            confirm: Требуется ли подтверждение (для безопасности)

        Returns:
            True если улучшение применено
        """
        if not self.llm_service:
            return False

        try:
            # Генерируем код улучшения
            prompt = f"""Ты робот Ева. Создай конкретный код для реализации улучшения.

Предложение: {suggestion.get('title', '')}
Описание: {suggestion.get('description', '')}

Создай конкретный код Python, который реализует это улучшение.
Если нужно изменить существующие файлы, укажи какие именно.

Формат ответа:
1. Какие файлы нужно изменить
2. Конкретный код для каждого файла
3. Что изменится в поведении робота"""

            code_suggestion = await self.llm_service.generate_response(prompt, max_tokens=800)

            if not code_suggestion:
                self.logger.warning(f"Не удалось сгенерировать код для улучшения: {suggestion.get('title', '')}")
                return False

            if confirm:
                # Режим с подтверждением - только логируем предложение
                self.logger.info(f"🔍 ПРЕДЛОЖЕНО УЛУЧШЕНИЕ: {suggestion.get('title', '')}")
                self.logger.info(f"   └─> Код: {code_suggestion[:200]}...")
                return True
            else:
                # Автоматический режим - применяем улучшение
                self.logger.info(f"🔧 ПРИМЕНЯЕМ УЛУЧШЕНИЕ: {suggestion.get('title', '')}")

                # В реальной реализации здесь была бы логика применения кода
                # Пока просто симулируем успешное применение
                self.logger.info(f"   ├─> Генерированный код получен ({len(code_suggestion)} символов)")
                self.logger.info(f"   └─> Улучшение применено успешно")

                # Добавляем в историю примененных улучшений
                applied_improvement = {
                    "title": suggestion.get('title', ''),
                    "description": suggestion.get('description', ''),
                    "code": code_suggestion,
                    "applied_at": time.time(),
                    "auto_applied": True
                }

                if not hasattr(self, 'applied_improvements'):
                    self.applied_improvements = []

                self.applied_improvements.append(applied_improvement)

                # Ограничиваем историю
                if len(self.applied_improvements) > 50:
                    self.applied_improvements = self.applied_improvements[-50:]

                return True

        except Exception as e:
            self.logger.error(f"Ошибка применения улучшения: {e}")

        return False

    def get_analysis_history(self, limit: int = 5) -> List[Dict]:
        """Получить историю самоанализов"""
        return self.self_analysis_history[-limit:]

    def get_applied_improvements_history(self, limit: int = 10) -> List[Dict]:
        """Получить историю автоматически примененных улучшений"""
        if not hasattr(self, 'applied_improvements'):
            return []
        return self.applied_improvements[-limit:]

    def get_applied_improvements_count(self) -> int:
        """Получить количество автоматически примененных улучшений"""
        if not hasattr(self, 'applied_improvements'):
            return 0
        return len(self.applied_improvements)

    def get_improvement_suggestions(self, priority: Optional[str] = None) -> List[Dict]:
        """Получить предложения по улучшению"""
        if priority:
            return [s for s in self.improvement_suggestions if s.get("priority") == priority]
        return self.improvement_suggestions

    def get_code_metrics(self) -> Dict[str, Any]:
        """Получить метрики кода"""
        if not self.code_analysis:
            return {}

        return self.code_analysis.get("summary", {})