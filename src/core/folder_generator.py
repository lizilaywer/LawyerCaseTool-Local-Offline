# -*- coding: utf-8 -*-
"""文件夹结构生成器模块"""

from pathlib import Path
from shutil import copy2
from typing import Any, Callable, Dict, List, Optional, Union

from src.core.variable_parser import VariableParser
from src.core.template_engine import TemplateEngine
from src.utils.validators import validate_folder_name, sanitize_filename
from src.utils.exceptions import FolderGenerationError, LawyerToolError
from src.utils.logger import get_logger
from src.utils.template_path_manager import get_template_path_manager


class FolderGenerator:
    """文件夹结构生成器"""

    def __init__(self):
        self._parser = VariableParser()
        self._template_engine = TemplateEngine()
        self._template_path_manager = get_template_path_manager()
        self._logger = get_logger()
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._cancel_checker: Optional[Callable[[], bool]] = None

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

    def set_cancel_checker(self, checker: Callable[[], bool]) -> None:
        """设置取消检查函数。"""
        self._cancel_checker = checker

    def _ensure_not_cancelled(self) -> None:
        """在长操作之间检查是否已取消。"""
        if self._cancel_checker and self._cancel_checker():
            raise LawyerToolError("操作已取消")

    def _report_progress(
        self,
        current: int,
        total: int,
        message: str
    ) -> None:
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(current, total, message)

    def generate(
        self,
        structure: Dict[str, Any],
        values: Dict[str, Any],
        output_dir: Path,
        exist_ok: bool = False
    ) -> Path:
        """
        生成文件夹结构

        Args:
            structure: 文件夹结构配置
            values: 变量值字典
            output_dir: 输出目录
            exist_ok: 如果目标已存在是否继续

        Returns:
            生成的根目录路径

        Raises:
            FolderGenerationError: 生成失败
        """
        self._ensure_not_cancelled()

        # 解析根目录名称
        root_name_template = structure.get("root_name", "新建案卷")
        root_name = self._parser.replace_variables(
            root_name_template, values, sanitize=True
        )

        # 验证文件夹名称
        is_valid, error_msg = validate_folder_name(root_name)
        if not is_valid:
            raise FolderGenerationError(root_name, error_msg)

        # 创建根目录
        root_path = output_dir / root_name

        if root_path.exists():
            if not exist_ok:
                raise FolderGenerationError(
                    str(root_path),
                    "目标文件夹已存在"
                )
        else:
            root_path.mkdir(parents=True)
            self._logger.info(f"创建根目录: {root_path}")

        # 计算总文件夹数
        folders = structure.get("folders", [])
        total_count = self._count_items(folders)
        current_count = 0

        # 创建子文件夹和文件
        for folder_def in folders:
            self._ensure_not_cancelled()
            current_count = self._create_folder(
                root_path,
                folder_def,
                values,
                current_count,
                total_count
            )

        return root_path

    def _count_items(self, folders: List[Dict[str, Any]]) -> int:
        """
        计算文件夹和文件总数

        Args:
            folders: 文件夹列表

        Returns:
            总数（文件夹+文件）
        """
        count = 0
        for folder in folders:
            count += 1  # 父文件夹
            subfolders = folder.get("subfolders", [])
            for subfolder in subfolders:
                if self._is_file_item(subfolder):
                    count += 1  # 文件
                else:
                    count += 1  # 子文件夹
        return count

    def _is_file_item(self, item: Union[str, Dict[str, Any]]) -> bool:
        """
        判断项目是否为文件

        Args:
            item: 文件夹或文件项（字符串或字典）

        Returns:
            是否为文件
        """
        if isinstance(item, str):
            # 旧格式：字符串默认为文件夹（向后兼容）
            return False
        elif isinstance(item, dict):
            # 新格式：检查 type 字段
            return item.get("type") == "file"
        return False

    def _create_folder(
        self,
        parent: Path,
        folder_def: Dict[str, Any],
        values: Dict[str, Any],
        current: int,
        total: int
    ) -> int:
        """
        创建文件夹及其内容

        Args:
            parent: 父目录
            folder_def: 文件夹定义
            values: 变量值
            current: 当前进度
            total: 总数

        Returns:
            更新后的当前进度
        """
        self._ensure_not_cancelled()

        # 解析文件夹名称
        folder_name = self._parser.replace_variables(
            folder_def["name"], values, sanitize=True
        )

        # 创建文件夹
        folder_path = parent / folder_name
        folder_path.mkdir(exist_ok=True)
        current += 1
        self._report_progress(current, total, f"创建文件夹: {folder_name}")
        self._logger.debug(f"创建文件夹: {folder_path}")

        # 创建子文件夹和文件
        subfolders = folder_def.get("subfolders", [])
        for subfolder_item in subfolders:
            self._ensure_not_cancelled()
            if self._is_file_item(subfolder_item):
                # 创建文件
                current = self._create_file(
                    folder_path, subfolder_item, values, current, total
                )
            else:
                # 创建子文件夹
                current = self._create_subfolder(
                    folder_path, subfolder_item, values, current, total
                )

        return current

    def _create_subfolder(
        self,
        parent: Path,
        subfolder_item: Union[str, Dict[str, Any]],
        values: Dict[str, Any],
        current: int,
        total: int
    ) -> int:
        """
        创建子文件夹

        Args:
            parent: 父目录
            subfolder_item: 子文件夹项
            values: 变量值
            current: 当前进度
            total: 总数

        Returns:
            更新后的当前进度
        """
        self._ensure_not_cancelled()

        if isinstance(subfolder_item, str):
            # 旧格式
            subfolder_name = self._parser.replace_variables(
                subfolder_item, values, sanitize=True
            )
        elif isinstance(subfolder_item, dict) and "name" in subfolder_item:
            # 新格式（type="folder"）
            subfolder_name = self._parser.replace_variables(
                subfolder_item["name"], values, sanitize=True
            )
        else:
            # 无效的文件夹项（缺少 name 字段）
            self._logger.warning(f"文件夹项缺少 'name' 字段，跳过: {subfolder_item}")
            return current

        subfolder_path = parent / subfolder_name
        subfolder_path.mkdir(exist_ok=True)
        current += 1
        self._report_progress(
            current, total, f"创建子文件夹: {subfolder_name}"
        )
        self._logger.debug(f"创建子文件夹: {subfolder_path}")

        return current

    def _create_file(
        self,
        parent: Path,
        file_item: Dict[str, Any],
        values: Dict[str, Any],
        current: int,
        total: int
    ) -> int:
        """
        创建文件

        Args:
            parent: 父目录
            file_item: 文件项（dict格式）
            values: 变量值
            current: 当前进度
            total: 总数

        Returns:
            更新后的当前进度
        """
        self._ensure_not_cancelled()

        # 检查文件项是否有 name 字段
        if "name" not in file_item:
            self._logger.warning(f"文件项缺少 'name' 字段，跳过: {file_item}")
            return current

        file_name = self._parser.replace_variables(
            file_item["name"], values, sanitize=True
        )
        file_path = parent / file_name

        # 检查是否使用 Word 模板生成
        use_template = file_item.get("use_template", False)
        template_path = file_item.get("template_path", "")

        if use_template and template_path:
            # 解析模板路径
            resolved_template = self._template_path_manager.resolve_template_path(template_path)

            if resolved_template and resolved_template.exists():
                try:
                    # 使用模板引擎生成文档（替换变量）
                    self._template_engine.process_template(
                        resolved_template,
                        file_path,
                        values
                    )
                    self._logger.info(f"使用模板生成文件: {file_path}")
                except Exception as e:
                    self._logger.error(f"模板生成失败: {file_path} <- {resolved_template} ({e})")
                    raise FolderGenerationError(str(file_path), f"模板生成失败: {e}") from e
            else:
                self._logger.error(f"模板文件不存在或不可访问: {template_path}")
                raise FolderGenerationError(str(file_path), f"模板文件不存在或不可访问: {template_path}")
        else:
            # 创建空文件
            file_path.touch()
            self._logger.debug(f"创建空文件: {file_path}")

        current += 1
        self._report_progress(current, total, f"创建文件: {file_name}")

        return current

    def preview(
        self,
        structure: Dict[str, Any],
        values: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        预览文件夹结构

        Args:
            structure: 文件夹结构配置
            values: 变量值字典

        Returns:
            文件夹结构预览列表
        """
        result = []

        # 解析根目录名称
        root_name_template = structure.get("root_name", "新建案卷")
        root_name = self._parser.replace_variables(
            root_name_template, values, sanitize=True
        )

        result.append({
            "name": root_name,
            "level": 0,
            "type": "folder"
        })

        # 遍历子文件夹
        folders = structure.get("folders", [])
        for folder_def in folders:
            result.extend(self._preview_folder(folder_def, values, 1))

        return result

    def _preview_folder(
        self,
        folder_def: Dict[str, Any],
        values: Dict[str, Any],
        level: int
    ) -> List[Dict[str, Any]]:
        """
        预览单个文件夹

        Args:
            folder_def: 文件夹定义
            values: 变量值
            level: 层级

        Returns:
            预览列表
        """
        result = []

        folder_name = self._parser.replace_variables(
            folder_def["name"], values, sanitize=True
        )

        result.append({
            "name": folder_name,
            "level": level,
            "type": "folder"
        })

        # 处理子项（文件或文件夹）
        subfolders = folder_def.get("subfolders", [])
        for subfolder_item in subfolders:
            if self._is_file_item(subfolder_item):
                # 文件
                if "name" not in subfolder_item:
                    self._logger.warning(f"文件项缺少 'name' 字段: {subfolder_item}")
                    continue
                file_name = self._parser.replace_variables(
                    subfolder_item["name"], values, sanitize=True
                )
                result.append({
                    "name": file_name,
                    "level": level + 1,
                    "type": "file",
                    "template_path": subfolder_item.get("template_path", "")
                })
            else:
                # 子文件夹
                if isinstance(subfolder_item, str):
                    subfolder_name = self._parser.replace_variables(
                        subfolder_item, values, sanitize=True
                    )
                elif isinstance(subfolder_item, dict) and "name" in subfolder_item:
                    subfolder_name = self._parser.replace_variables(
                        subfolder_item["name"], values, sanitize=True
                    )
                else:
                    # 无效的文件夹项（缺少 name 字段）
                    self._logger.warning(f"文件夹项缺少 'name' 字段: {subfolder_item}")
                    continue
                result.append({
                    "name": subfolder_name,
                    "level": level + 1,
                    "type": "folder"
                })

        return result

    def get_required_variables(
        self,
        structure: Dict[str, Any]
    ) -> List[str]:
        """
        获取文件夹结构中使用的变量

        Args:
            structure: 文件夹结构配置

        Returns:
            变量名列表
        """
        return self._parser.extract_from_structure(structure)
