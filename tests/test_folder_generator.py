# -*- coding: utf-8 -*-
"""文件夹生成器测试"""

import pytest
import tempfile
from pathlib import Path
import shutil

from src.core.folder_generator import FolderGenerator
from src.core.variable_parser import VariableParser
from src.utils.exceptions import FolderGenerationError


class TestFolderGenerator:
    """文件夹生成器测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.generator = FolderGenerator()
        self.parser = VariableParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """每个测试方法后执行"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_preview_structure(self):
        """测试预览文件夹结构"""
        structure = {
            "root_name": "{{case_number}}_{{client_name}}",
            "folders": [
                {
                    "name": "01_起诉材料",
                    "subfolders": ["起诉状", "证据材料"]
                }
            ]
        }
        values = {
            "case_number": "2024-001",
            "client_name": "张三"
        }

        preview = self.generator.preview(structure, values)

        assert len(preview) > 0
        assert preview[0]["name"] == "2024-001_张三"
        assert preview[0]["level"] == 0

    def test_generate_folder_structure(self):
        """测试生成文件夹结构"""
        structure = {
            "root_name": "测试案卷",
            "folders": [
                {
                    "name": "01_材料",
                    "subfolders": ["子文件夹1", "子文件夹2"]
                }
            ]
        }
        values = {}

        root_path = self.generator.generate(
            structure,
            values,
            self.temp_dir,
            exist_ok=False
        )

        assert root_path.exists()
        assert root_path.name == "测试案卷"
        assert (root_path / "01_材料").exists()
        assert (root_path / "01_材料" / "子文件夹1").exists()
        assert (root_path / "01_材料" / "子文件夹2").exists()

    def test_generate_with_variables(self):
        """测试带变量的文件夹生成"""
        structure = {
            "root_name": "{{case_number}}_{{client}}",
            "folders": [
                {
                    "name": "{{folder_name}}",
                    "subfolders": []
                }
            ]
        }
        values = {
            "case_number": "2024-001",
            "client": "李四",
            "folder_name": "起诉材料"
        }

        root_path = self.generator.generate(
            structure,
            values,
            self.temp_dir,
            exist_ok=False
        )

        assert root_path.name == "2024-001_李四"
        assert (root_path / "起诉材料").exists()

    def test_get_required_variables(self):
        """测试获取所需变量"""
        structure = {
            "root_name": "{{case_number}}_{{client_name}}",
            "folders": [
                {
                    "name": "{{folder_type}}",
                    "subfolders": ["{{subfolder}}"]
                }
            ]
        }

        variables = self.generator.get_required_variables(structure)

        assert "case_number" in variables
        assert "client_name" in variables
        assert "folder_type" in variables
        assert "subfolder" in variables

    def test_progress_callback(self):
        """测试进度回调"""
        progress_records = []

        def progress_callback(current, total, message):
            progress_records.append((current, total, message))

        self.generator.set_progress_callback(progress_callback)

        structure = {
            "root_name": "测试",
            "folders": [
                {"name": "文件夹1", "subfolders": ["子1", "子2"]}
            ]
        }

        self.generator.generate(structure, {}, self.temp_dir)

        assert len(progress_records) > 0

    def test_generate_with_files_new_format(self):
        """测试生成包含文件的新格式结构"""
        structure = {
            "root_name": "测试案卷",
            "folders": [
                {
                    "name": "0委托手续",
                    "subfolders": [
                        {
                            "name": "委托合同.docx",
                            "type": "file",
                            "template_path": ""
                        },
                        {
                            "name": "授权委托书.docx",
                            "type": "file",
                            "template_path": ""
                        }
                    ]
                },
                {
                    "name": "1文书材料",
                    "subfolders": []
                }
            ]
        }
        values = {}

        root_path = self.generator.generate(
            structure,
            values,
            self.temp_dir,
            exist_ok=False
        )

        assert root_path.exists()
        assert (root_path / "0委托手续").exists()
        # 检查文件是否创建
        assert (root_path / "0委托手续" / "委托合同.docx").exists()
        assert (root_path / "0委托手续" / "授权委托书.docx").exists()
        # 检查空文件夹是否创建
        assert (root_path / "1文书材料").exists()

    def test_generate_with_template_file(self):
        """测试从模板文件创建文件"""
        # 创建一个模板文件
        template_file = self.temp_dir / "template.docx"
        template_file.touch()

        structure = {
            "root_name": "测试案卷",
            "folders": [
                {
                    "name": "0委托手续",
                    "subfolders": [
                        {
                            "name": "委托合同.docx",
                            "type": "file",
                            "template_path": str(template_file)
                        }
                    ]
                }
            ]
        }
        values = {}

        root_path = self.generator.generate(
            structure,
            values,
            self.temp_dir / "output",
            exist_ok=False
        )

        target_file = root_path / "0委托手续" / "委托合同.docx"
        assert target_file.exists()
        assert target_file.is_file()

    def test_preview_with_files(self):
        """测试预览包含文件的结构"""
        structure = {
            "root_name": "测试案卷",
            "folders": [
                {
                    "name": "0委托手续",
                    "subfolders": [
                        {
                            "name": "委托合同.docx",
                            "type": "file",
                            "template_path": ""
                        },
                        {
                            "name": "其他材料",
                            "type": "folder",
                            "template_path": None
                        }
                    ]
                }
            ]
        }
        values = {}

        preview = self.generator.preview(structure, values)

        # 检查预览结果
        assert len(preview) == 4  # 根目录 + 文件夹 + 文件 + 子文件夹
        assert preview[0]["name"] == "测试案卷"
        assert preview[1]["name"] == "0委托手续"
        assert preview[1]["type"] == "folder"
        assert preview[2]["name"] == "委托合同.docx"
        assert preview[2]["type"] == "file"
        assert preview[3]["name"] == "其他材料"
        assert preview[3]["type"] == "folder"

    def test_backward_compatibility_string_subfolders(self):
        """测试向后兼容：字符串格式的子文件夹"""
        structure = {
            "root_name": "测试案卷",
            "folders": [
                {
                    "name": "0委托手续",
                    "subfolders": ["委托合同", "授权委托书"]
                }
            ]
        }
        values = {}

        root_path = self.generator.generate(
            structure,
            values,
            self.temp_dir,
            exist_ok=False
        )

        # 旧格式应该创建文件夹
        assert (root_path / "0委托手续" / "委托合同").exists()
        assert (root_path / "0委托手续" / "委托合同").is_dir()
        assert (root_path / "0委托手续" / "授权委托书").exists()
        assert (root_path / "0委托手续" / "授权委托书").is_dir()

    def test_generate_raises_when_template_is_required_but_missing(self):
        """use_template=True 且模板不可用时，应明确失败而不是静默创建空文件。"""
        structure = {
            "root_name": "测试案卷",
            "folders": [
                {
                    "name": "0委托手续",
                    "subfolders": [
                        {
                            "name": "委托合同.docx",
                            "type": "file",
                            "use_template": True,
                            "template_path": "non-existent/template.docx",
                        }
                    ],
                }
            ],
        }

        # 避免触发真实用户目录访问，直接模拟模板解析失败
        self.generator._template_path_manager.resolve_template_path = lambda _path: None

        with pytest.raises(FolderGenerationError):
            self.generator.generate(
                structure,
                {},
                self.temp_dir,
                exist_ok=False,
            )
