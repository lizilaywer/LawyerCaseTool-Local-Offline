# -*- coding: utf-8 -*-
"""配置管理器模块"""

import copy
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.path_manager import PathManager, get_path_manager
from src.config.default_templates import (
    DEFAULT_TEMPLATES,
    DEFAULT_PINNED_CONFIG,
    DEFAULT_APP_CONFIG,
    DEFAULT_GENERATION_CONFIG,
    DEFAULT_UI_CONFIG,
)
from src.utils.logger import get_logger
from src.utils.exceptions import ConfigError
from src.utils.migration import (
    migrate_templates,
    is_template_v1,
    has_legacy_template_paths,
    migrate_template_paths,
)
from src.utils.platform_utils import get_default_output_dir


def safe_write_json(path: Path, data: Any, indent: int = 2) -> bool:
    """原子写入 JSON 文件

    使用临时文件 + 原子替换的方式写入，确保：
    1. 写入过程中断不会损坏原文件
    2. 要么完全成功，要么完全失败

    Args:
        path: 目标文件路径
        data: 要写入的数据
        indent: JSON 缩进

    Returns:
        是否成功

    Raises:
        IOError: 写入失败时抛出
    """
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)

    # 创建临时文件（在同一目录下，确保同一文件系统）
    temp_fd = None
    temp_path = None

    try:
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(
            suffix='.tmp',
            prefix='.config_',
            dir=path.parent
        )

        # 写入数据
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            temp_fd = None  # 已由 fdopen 接管
            json.dump(data, f, indent=indent, ensure_ascii=False)

        # 原子替换（在同一个文件系统上，这是原子操作）
        shutil.move(temp_path, path)
        temp_path = None  # 标记已成功

        return True

    except Exception as e:
        # 清理临时文件
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path is not None and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise IOError(f"写入文件失败: {e}")


class ConfigManager:
    """配置管理器"""

    _instance: Optional['ConfigManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # 双重检查锁定模式，在锁内完成全部初始化消除竞态窗口
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._path_manager = get_path_manager()
                    instance._logger = get_logger()

                    # 应用配置
                    instance._config: Dict[str, Any] = {}
                    # 模板配置
                    instance._templates: List[Dict[str, Any]] = []

                    # 批量更新模式标志
                    instance._batch_mode: bool = False
                    instance._batch_dirty: bool = False

                    # 初始化
                    instance._init_config()

                    instance._initialized = True  # 最后标记
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        # 所有初始化已在 __new__ 中完成，无需重复
        pass

    def _init_config(self) -> None:
        """初始化配置"""
        # 确保目录存在
        self._path_manager.ensure_directories()

        # 加载或创建应用配置
        self._load_or_create_config()

        # 加载或创建模板配置
        self._load_or_create_templates()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        default_generation = copy.deepcopy(DEFAULT_GENERATION_CONFIG)
        if not default_generation.get("default_output_dir"):
            default_generation["default_output_dir"] = str(get_default_output_dir())

        return {
            "app": copy.deepcopy(DEFAULT_APP_CONFIG),
            "generation": default_generation,
            "ui": copy.deepcopy(DEFAULT_UI_CONFIG),
            "pinned": copy.deepcopy(DEFAULT_PINNED_CONFIG),
        }

    def _backup_corrupt_file(self, path: Path, reason: str) -> Optional[Path]:
        """备份损坏的配置文件，避免静默覆盖用户数据。"""
        if not path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_name(f"{path.name}.corrupt-{timestamp}.bak")
        try:
            shutil.move(str(path), str(backup_path))
            self._logger.warning(f"{reason}，已备份到: {backup_path}")
            return backup_path
        except Exception as e:
            self._logger.error(f"{reason}，但备份失败: {e}")
            return None

    def _load_or_create_config(self) -> None:
        """加载或创建配置文件"""
        config_file = self._path_manager.config_file

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)

                # 验证配置结构
                if self._validate_config(loaded_config):
                    self._config = loaded_config
                    self._logger.info(f"配置文件加载成功: {config_file}")

                    # 修复空值的默认输出目录（迁移到桌面）
                    if not self._config.get("generation", {}).get("default_output_dir"):
                        default_dir = str(get_default_output_dir())
                        self._config.setdefault("generation", {})["default_output_dir"] = default_dir
                        self._save_config()
                        self._logger.info(f"已更新默认输出目录: {default_dir}")
                else:
                    self._backup_corrupt_file(config_file, "配置文件验证失败")
                    self._config = self._get_default_config()
                    self._save_config()
                    self._logger.warning("已创建新的默认配置文件")

            except json.JSONDecodeError as e:
                self._logger.error(f"配置文件 JSON 格式错误: {e}")
                self._backup_corrupt_file(config_file, "配置文件 JSON 格式错误")
                self._config = self._get_default_config()
                self._save_config()
            except Exception as e:
                self._logger.error(f"配置文件加载失败: {e}")
                self._backup_corrupt_file(config_file, "配置文件加载失败")
                self._config = self._get_default_config()
                self._save_config()
        else:
            self._config = self._get_default_config()
            self._save_config()
            self._logger.info(f"创建默认配置文件: {config_file}")

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置结构

        Args:
            config: 配置字典

        Returns:
            是否有效
        """
        if not isinstance(config, dict):
            return False

        # 验证必需的顶级键
        required_keys = ['app', 'generation', 'ui']
        for key in required_keys:
            if key not in config:
                self._logger.warning(f"配置缺少必需的键: {key}")
                return False
            if not isinstance(config[key], dict):
                self._logger.warning(f"配置键 {key} 必须是字典类型")
                return False

        return True

    def _load_or_create_templates(self) -> None:
        """加载或创建模板配置"""
        templates_file = self._path_manager.templates_config_file

        if templates_file.exists():
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    loaded_templates = json.load(f)

                # 验证模板配置结构
                if self._validate_templates(loaded_templates):
                    self._templates = loaded_templates
                else:
                    self._backup_corrupt_file(templates_file, "模板配置验证失败")
                    self._templates = copy.deepcopy(DEFAULT_TEMPLATES)
                    self._save_templates()
                    self._logger.warning("已创建新的默认模板配置")

                # 检查是否需要迁移数据结构（v1 -> v2）
                needs_migration = any(is_template_v1(t) for t in self._templates)
                if needs_migration:
                    self._logger.info("检测到旧版本模板格式，开始自动迁移...")
                    self._templates = migrate_templates(self._templates)
                    self._save_templates()
                    self._logger.info("模板迁移完成并已保存")

                # 检查是否需要迁移路径格式（templates/ 前缀）
                needs_path_migration = any(has_legacy_template_paths(t) for t in self._templates)
                if needs_path_migration:
                    self._logger.info("检测到旧版模板路径格式，开始自动迁移...")
                    self._templates = [migrate_template_paths(t) for t in self._templates]
                    self._save_templates()
                    self._logger.info("模板路径迁移完成并已保存")

                # 注意：不再自动合并默认模板
                # 用户删除的模板不会自动恢复
                # 只有通过"重置默认"按钮才会恢复默认模板

                self._logger.info(f"模板配置加载成功: {templates_file}")
            except json.JSONDecodeError as e:
                self._logger.error(f"模板配置 JSON 格式错误: {e}")
                self._backup_corrupt_file(templates_file, "模板配置 JSON 格式错误")
                self._templates = copy.deepcopy(DEFAULT_TEMPLATES)
                self._save_templates()
            except Exception as e:
                self._logger.error(f"模板配置加载失败: {e}")
                self._backup_corrupt_file(templates_file, "模板配置加载失败")
                self._templates = copy.deepcopy(DEFAULT_TEMPLATES)
                self._save_templates()
        else:
            # 首次创建配置文件时使用默认模板
            self._templates = copy.deepcopy(DEFAULT_TEMPLATES)
            self._save_templates()
            self._logger.info(f"创建默认模板配置: {templates_file}")

    def _validate_templates(self, templates: List[Dict[str, Any]]) -> bool:
        """验证模板配置结构

        Args:
            templates: 模板列表

        Returns:
            是否有效
        """
        if not isinstance(templates, list):
            return False

        for i, template in enumerate(templates):
            if not isinstance(template, dict):
                self._logger.warning(f"模板 {i} 不是字典类型")
                return False

            # 验证必需的字段
            if 'id' not in template:
                self._logger.warning(f"模板 {i} 缺少 'id' 字段")
                return False
            if 'name' not in template:
                self._logger.warning(f"模板 {i} 缺少 'name' 字段")
                return False
            if 'folder_structure' not in template:
                self._logger.warning(f"模板 {i} 缺少 'folder_structure' 字段")
                return False

        return True

    def _save_config(self) -> bool:
        """保存配置文件（原子写入）"""
        try:
            config_file = self._path_manager.config_file
            safe_write_json(config_file, self._config)
            # 设置文件权限为仅所有者可读写 (rw-------)
            try:
                config_file.chmod(0o600)
            except OSError as e:
                self._logger.warning(f"无法设置配置文件权限: {e}")
        except (IOError, OSError) as e:
            self._logger.error(f"配置文件保存失败: {e}")
            return False
        return True

    def _save_templates(self) -> bool:
        """保存模板配置（原子写入）"""
        try:
            templates_file = self._path_manager.templates_config_file
            safe_write_json(templates_file, self._templates)
            return True
        except IOError as e:
            self._logger.error(f"模板配置保存失败: {e}")
            return False
        except Exception as e:
            self._logger.error(f"模板配置保存失败: {e}")
            return False

    # ==================== 应用配置操作 ====================

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点分隔的嵌套键，如 "app.language"
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        设置配置值

        Args:
            key: 配置键，支持点分隔的嵌套键
            value: 配置值
            save: 是否立即保存
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

        if save and not self._batch_mode:
            self._save_config()
        elif self._batch_mode:
            self._batch_dirty = True

    def begin_batch(self) -> None:
        """开始批量更新模式（延迟保存）"""
        self._batch_mode = True
        self._batch_dirty = False

    def end_batch(self, save: bool = True) -> None:
        """结束批量更新模式

        Args:
            save: 是否保存累积的更改
        """
        self._batch_mode = False
        if save and self._batch_dirty:
            self._save_config()
            self._batch_dirty = False

    def batch_update(self) -> 'BatchUpdateContext':
        """获取批量更新上下文管理器

        Usage:
            with config_manager.batch_update():
                config_manager.set('key1', 'value1')
                config_manager.set('key2', 'value2')
        """
        return self.BatchUpdateContext(self)

    class BatchUpdateContext:
        """批量更新上下文管理器"""

        def __init__(self, config_manager: 'ConfigManager'):
            self._config_manager = config_manager

        def __enter__(self) -> 'ConfigManager':
            self._config_manager.begin_batch()
            return self._config_manager

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            # 只有在没有异常时才保存
            self._config_manager.end_batch(save=(exc_type is None))

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return copy.deepcopy(self._config)

    def reset_config(self) -> None:
        """重置配置为默认值（从default_templates.py恢复所有设置）"""
        from src.config.default_templates import (
            DEFAULT_TEMPLATES,
            DEFAULT_PINNED_CONFIG,
            DEFAULT_APP_CONFIG,
            DEFAULT_GENERATION_CONFIG,
            DEFAULT_UI_CONFIG,
        )
        
        # 重置主配置
        self._config = {
            "app": copy.deepcopy(DEFAULT_APP_CONFIG),
            "generation": copy.deepcopy(DEFAULT_GENERATION_CONFIG),
            "ui": copy.deepcopy(DEFAULT_UI_CONFIG),
            "pinned": copy.deepcopy(DEFAULT_PINNED_CONFIG),
        }
        self._save_config()
        
        # 重置模板配置
        self._templates = copy.deepcopy(DEFAULT_TEMPLATES)
        self._save_templates()
        
        self._logger.info("配置已重置为默认值（来自default_templates.py）")

    # ==================== 模板配置操作 ====================

    def get_templates(self) -> List[Dict[str, Any]]:
        """获取所有模板"""
        return copy.deepcopy(self._templates)

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模板

        Args:
            template_id: 模板 ID

        Returns:
            模板配置，未找到返回 None
        """
        for template in self._templates:
            if template["id"] == template_id:
                return copy.deepcopy(template)
        return None

    def add_template(self, template: Dict[str, Any]) -> bool:
        """
        添加模板

        Args:
            template: 模板配置

        Returns:
            是否成功
        """
        if not template.get("id"):
            self._logger.error("模板缺少 ID")
            return False

        # 检查 ID 是否已存在
        if self.get_template(template["id"]):
            self._logger.error(f"模板 ID 已存在: {template['id']}")
            return False

        self._templates.append(copy.deepcopy(template))
        return self._save_templates()

    def update_template(self, template_id: str, template: Dict[str, Any]) -> bool:
        """
        更新模板

        Args:
            template_id: 模板 ID
            template: 新的模板配置

        Returns:
            是否成功
        """
        for i, t in enumerate(self._templates):
            if t["id"] == template_id:
                stored_template = copy.deepcopy(template)
                stored_template["id"] = template_id  # 保持 ID 不变
                self._templates[i] = stored_template
                return self._save_templates()

        self._logger.error(f"模板未找到: {template_id}")
        return False

    def delete_template(self, template_id: str) -> bool:
        """
        删除模板

        Args:
            template_id: 模板 ID

        Returns:
            是否成功
        """
        for i, t in enumerate(self._templates):
            if t["id"] == template_id:
                del self._templates[i]
                return self._save_templates()

        self._logger.error(f"模板未找到: {template_id}")
        return False

    def reset_templates(self, include_settings: bool = True) -> None:
        """重置模板为默认值
        
        Args:
            include_settings: 是否同时重置置顶模板和应用设置，默认为 True
        """
        # 重置模板
        self._templates = copy.deepcopy(DEFAULT_TEMPLATES)
        self._save_templates()
        
        if include_settings:
            # 重置置顶模板配置
            self._config['pinned'] = copy.deepcopy(DEFAULT_PINNED_CONFIG)
            
            # 重置应用配置（保留语言、主题等）
            for key, value in DEFAULT_APP_CONFIG.items():
                self._config.setdefault('app', {})[key] = copy.deepcopy(value)
            
            # 重置生成配置（保留自动打开文件夹等设置）
            for key, value in DEFAULT_GENERATION_CONFIG.items():
                self._config.setdefault('generation', {})[key] = copy.deepcopy(value)
            
            # 重置UI配置
            for key, value in DEFAULT_UI_CONFIG.items():
                self._config.setdefault('ui', {})[key] = copy.deepcopy(value)
            
            self._save_config()
            self._logger.info("已重置所有模板和设置为默认值")

    # ==================== 置顶模板操作 ====================

    def get_pinned_templates(self) -> List[str]:
        """获取全局置顶模板ID列表"""
        return self._config.get("pinned", {}).get("global", [])

    def get_category_pinned(self, category: str) -> Optional[str]:
        """获取指定分类的置顶模板ID
        
        Args:
            category: 分类名称
            
        Returns:
            置顶模板ID，如果没有则返回None
        """
        return self._config.get("pinned", {}).get("by_category", {}).get(category)

    def pin_template_global(self, template_id: str) -> bool:
        """全局置顶模板（最多3个）
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否成功
        """
        pinned = self._config.setdefault("pinned", {}).setdefault("global", [])
        if template_id in pinned:
            return True  # 已置顶
        if len(pinned) >= 3:
            self._logger.warning("全局置顶数量已达上限（最多3个）")
            return False
        pinned.append(template_id)
        self._save_config()
        return True

    def unpin_template_global(self, template_id: str) -> bool:
        """取消全局置顶
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否成功
        """
        pinned = self._config.get("pinned", {}).get("global", [])
        if template_id in pinned:
            pinned.remove(template_id)
            self._save_config()
            return True
        return False

    def pin_template_in_category(self, template_id: str, category: str) -> bool:
        """在指定分类中置顶模板（每分类最多1个）
        
        Args:
            template_id: 模板ID
            category: 分类名称
            
        Returns:
            是否成功
        """
        by_category = self._config.setdefault("pinned", {}).setdefault("by_category", {})
        by_category[category] = template_id
        self._save_config()
        return True

    def unpin_template_in_category(self, category: str) -> bool:
        """取消分类置顶
        
        Args:
            category: 分类名称
            
        Returns:
            是否成功
        """
        by_category = self._config.get("pinned", {}).get("by_category", {})
        if category in by_category:
            del by_category[category]
            self._save_config()
            return True
        return False

    def is_template_pinned(self, template_id: str, category: Optional[str] = None) -> bool:
        """检查模板是否已置顶
        
        Args:
            template_id: 模板ID
            category: 如果指定，则同时检查是否在分类中置顶
            
        Returns:
            是否已置顶
        """
        pinned_global = self._config.get("pinned", {}).get("global", [])
        if template_id in pinned_global:
            return True
        if category:
            cat_pinned = self._config.get("pinned", {}).get("by_category", {}).get(category)
            if cat_pinned == template_id:
                return True
        return False


def get_config_manager() -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager()
