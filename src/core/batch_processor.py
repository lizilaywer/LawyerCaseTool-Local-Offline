# -*- coding: utf-8 -*-
"""批量处理器模块"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.core.folder_generator import FolderGenerator
from src.core.template_engine import TemplateEngine
from src.core.variable_parser import VariableParser
from src.utils.logger import get_logger
from src.utils.exceptions import LawyerToolError
from src.utils.template_path_manager import get_template_path_manager


class BatchProcessor:
    """批量处理器

    使用 threading.Event 实现线程安全的取消机制。
    """

    def __init__(self):
        self._folder_generator = FolderGenerator()
        self._template_engine = TemplateEngine()
        self._parser = VariableParser()
        self._logger = get_logger()

        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        # 使用线程安全的 Event 替代布尔标志
        self._cancel_event = threading.Event()
        self._folder_generator.set_cancel_checker(self.is_cancelled)

    def set_progress_callback(
        self,
        callback: Callable[[int, int, str], None]
    ) -> None:
        """
        设置进度回调函数

        Args:
            callback: 回调函数 (current, total, message)
        """
        self._progress_callback = callback
        self._folder_generator.set_progress_callback(callback)

    def cancel(self) -> None:
        """取消处理（线程安全）"""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """检查是否已取消（线程安全）"""
        return self._cancel_event.is_set()

    def reset_cancel(self) -> None:
        """重置取消状态（线程安全）"""
        self._cancel_event.clear()

    def _report_progress(
        self,
        current: int,
        total: int,
        message: str
    ) -> None:
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def process_single(
        self,
        template_config: Dict[str, Any],
        values: Dict[str, Any],
        output_dir: Path,
        process_template: bool = True
    ) -> Dict[str, Any]:
        """
        处理单个案卷

        Args:
            template_config: 模板配置
            values: 变量值字典
            output_dir: 输出目录
            process_template: 是否处理 Word 模板

        Returns:
            处理结果
        """
        result = {
            "success": False,
            "cancelled": False,
            "root_path": None,
            "template_path": None,
            "error": None
        }

        try:
            if self.is_cancelled():
                result["cancelled"] = True
                result["error"] = "已取消"
                return result

            # 应用默认值
            var_defs = template_config.get("variables", [])
            values = self._parser.apply_defaults(values, var_defs)

            # 验证变量
            is_valid, errors = self._parser.validate_values(values, var_defs)
            if not is_valid:
                result["error"] = "; ".join(errors)
                return result

            if self.is_cancelled():
                result["cancelled"] = True
                result["error"] = "已取消"
                return result

            # 生成文件夹结构
            structure = template_config.get("folder_structure", {})
            root_path = self._folder_generator.generate(
                structure, values, output_dir, exist_ok=False
            )
            result["root_path"] = str(root_path)
            self._logger.info(f"案卷文件夹生成成功: {root_path}")

            if self.is_cancelled():
                result["cancelled"] = True
                result["error"] = "已取消"
                return result

            # 处理 Word 模板
            if process_template:
                template_file = template_config.get("template_file")
                if template_file:
                    template_path_manager = get_template_path_manager()
                    template_path = template_path_manager.resolve_template_path(template_file)

                    if template_path and template_path.exists():
                        if self.is_cancelled():
                            result["cancelled"] = True
                            result["error"] = "已取消"
                            return result
                        output_docx = root_path / f"{root_path.name}.docx"
                        self._template_engine.process_template(
                            template_path, output_docx, values
                        )
                        result["template_path"] = str(output_docx)
                        self._logger.info(f"Word 文档生成成功: {output_docx}")
                    else:
                        self._logger.warning(f"模板文件不存在: {template_file}")

            result["success"] = True

        except LawyerToolError as e:
            if self.is_cancelled() or "取消" in str(e):
                result["cancelled"] = True
                result["error"] = "已取消"
                self._logger.info("案卷处理已取消")
            else:
                result["error"] = str(e)
                self._logger.error(f"案卷处理失败: {e}")
        except Exception as e:
            result["error"] = f"未知错误: {e}"
            self._logger.error(f"案卷处理失败: {e}")

        return result

    def _process_single_worker(
        self,
        template_config: Dict[str, Any],
        values: Dict[str, Any],
        output_dir: Path,
        process_template: bool,
        index: int,
        total: int,
        progress_lock: threading.Lock,
    ) -> Dict[str, Any]:
        """供线程池调用的单个案卷处理包装器。"""
        if self.is_cancelled():
            return {
                "success": False,
                "cancelled": True,
                "error": "已取消",
                "root_path": None,
                "template_path": None,
            }

        with progress_lock:
            self._report_progress(index + 1, total, f"处理第 {index + 1}/{total} 个案卷")

        # 每个 worker 使用独立的生成器和引擎实例，确保线程安全
        from src.core.folder_generator import FolderGenerator
        from src.core.template_engine import TemplateEngine

        folder_generator = FolderGenerator()
        folder_generator.set_cancel_checker(self.is_cancelled)
        template_engine = TemplateEngine()
        parser = VariableParser()

        result = {
            "success": False,
            "cancelled": False,
            "root_path": None,
            "template_path": None,
            "error": None,
        }

        try:
            if self.is_cancelled():
                result["cancelled"] = True
                result["error"] = "已取消"
                return result

            var_defs = template_config.get("variables", [])
            values = parser.apply_defaults(values, var_defs)
            is_valid, errors = parser.validate_values(values, var_defs)
            if not is_valid:
                result["error"] = "; ".join(errors)
                return result

            if self.is_cancelled():
                result["cancelled"] = True
                result["error"] = "已取消"
                return result

            structure = template_config.get("folder_structure", {})
            root_path = folder_generator.generate(structure, values, output_dir, exist_ok=False)
            result["root_path"] = str(root_path)

            if self.is_cancelled():
                result["cancelled"] = True
                result["error"] = "已取消"
                return result

            if process_template:
                template_file = template_config.get("template_file")
                if template_file:
                    template_path_manager = get_template_path_manager()
                    template_path = template_path_manager.resolve_template_path(template_file)
                    if template_path and template_path.exists():
                        if self.is_cancelled():
                            result["cancelled"] = True
                            result["error"] = "已取消"
                            return result
                        output_docx = root_path / f"{root_path.name}.docx"
                        template_engine.process_template(template_path, output_docx, values)
                        result["template_path"] = str(output_docx)
                    else:
                        self._logger.warning(f"模板文件不存在: {template_file}")

            result["success"] = True

        except LawyerToolError as e:
            if self.is_cancelled() or "取消" in str(e):
                result["cancelled"] = True
                result["error"] = "已取消"
            else:
                result["error"] = str(e)
        except Exception as e:
            result["error"] = f"未知错误: {e}"

        return result

    def process_batch(
        self,
        template_config: Dict[str, Any],
        records: List[Dict[str, Any]],
        output_dir: Path,
        process_template: bool = True,
        max_workers: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量处理案卷

        Args:
            template_config: 模板配置
            records: 变量值记录列表
            output_dir: 输出目录
            process_template: 是否处理 Word 模板
            max_workers: 并发线程数，默认根据 CPU 核心数自动决定

        Returns:
            处理结果列表
        """
        # 重置取消状态
        self.reset_cancel()
        total = len(records)
        if total == 0:
            return []

        # 单条记录直接串行处理，避免线程池开销
        if total == 1:
            return [
                self.process_single(
                    template_config, records[0], output_dir, process_template
                )
            ]

        if max_workers is None:
            max_workers = min(4, (os.cpu_count() or 2))

        results: List[Optional[Dict[str, Any]]] = [None] * total
        progress_lock = threading.Lock()

        def _worker(i: int, values: Dict[str, Any]) -> Dict[str, Any]:
            return self._process_single_worker(
                template_config,
                values,
                output_dir,
                process_template,
                i,
                total,
                progress_lock,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(_worker, i, values): i
                for i, values in enumerate(records)
                if not self.is_cancelled()
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    results[idx] = {
                        "success": False,
                        "cancelled": False,
                        "error": f"未知错误: {exc}",
                        "root_path": None,
                        "template_path": None,
                    }

        return [r for r in results if r is not None]

    def validate_batch(
        self,
        template_config: Dict[str, Any],
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证批量数据

        Args:
            template_config: 模板配置
            records: 变量值记录列表

        Returns:
            验证结果
        """
        var_defs = template_config.get("variables", [])
        errors = []

        for i, values in enumerate(records):
            is_valid, record_errors = self._parser.validate_values(
                values, var_defs
            )
            if not is_valid:
                errors.append({
                    "index": i + 1,
                    "errors": record_errors
                })

        return {
            "valid": len(errors) == 0,
            "total": len(records),
            "error_count": len(errors),
            "errors": errors
        }

    def get_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取处理结果摘要

        Args:
            results: 处理结果列表

        Returns:
            摘要信息
        """
        total = len(results)
        success = sum(1 for r in results if r.get("success"))
        failed = total - success

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": (success / total * 100) if total > 0 else 0
        }
