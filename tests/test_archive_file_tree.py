# -*- coding: utf-8 -*-
"""案卷文件树交互测试"""

import shutil
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QAbstractItemView

from src.gui.widgets.archive_file_tree import ArchiveFileTree


class TestArchiveFileTree:
    """文件树最小回归测试。"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.root = self.temp_dir / "案件目录"
        self.root.mkdir()
        self.folder_a = self.root / "证据材料"
        self.folder_b = self.root / "庭审文书"
        self.folder_a.mkdir()
        self.folder_b.mkdir()
        self.root_file = self.root / "起诉状.pdf"
        self.root_file.write_text("pdf placeholder", encoding="utf-8")
        self.source_file = self.folder_a / "银行流水.txt"
        self.source_file.write_text("content", encoding="utf-8")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_folder_double_click_emits_folder_path(self, qapp):
        widget = ArchiveFileTree()
        widget.set_lazy_mode(False)
        widget.load_folder(self.root)

        emitted = []
        widget.folder_double_clicked.connect(emitted.append)

        folder_item = widget._find_item_by_path(widget.invisibleRootItem(), str(self.folder_a))
        assert folder_item is not None

        widget._on_item_double_clicked(folder_item, 0)

        assert emitted == [self.folder_a]

    def test_drop_rejects_putting_file_under_file_item(self, qapp):
        widget = ArchiveFileTree()
        widget.set_lazy_mode(False)
        widget.load_folder(self.root)

        file_item = widget._find_item_by_path(widget.invisibleRootItem(), str(self.root_file))
        assert file_item is not None

        destination, error = widget._resolve_drop_directory(
            self.source_file,
            "file",
            file_item,
            QAbstractItemView.DropIndicatorPosition.OnItem,
        )

        assert destination is None
        assert "文件不能作为子级容器" in error

    def test_drop_accepts_putting_file_into_folder(self, qapp):
        widget = ArchiveFileTree()
        widget.set_lazy_mode(False)
        widget.load_folder(self.root)

        folder_item = widget._find_item_by_path(widget.invisibleRootItem(), str(self.folder_b))
        assert folder_item is not None

        destination, error = widget._resolve_drop_directory(
            self.source_file,
            "file",
            folder_item,
            QAbstractItemView.DropIndicatorPosition.OnItem,
        )

        assert error == ""
        assert destination == self.folder_b

    def test_lazy_mode_loads_nested_files_only_after_expanding(self, qapp):
        nested = self.folder_a / "二级目录"
        nested.mkdir()
        nested_file = nested / "补充证据.txt"
        nested_file.write_text("nested", encoding="utf-8")

        widget = ArchiveFileTree()
        widget.set_lazy_mode(True)
        widget.load_folder(self.root)

        loaded_files = widget.get_all_files()
        assert self.root_file in loaded_files
        assert self.source_file not in loaded_files
        assert nested_file not in loaded_files

        widget.expand_all()
        expanded_files = widget.get_all_files()

        assert self.source_file in expanded_files
        assert nested_file in expanded_files

    def test_lazy_item_expand_replaces_placeholder_with_files(self, qapp):
        """单独点击小三角展开时应加载子文件，而不是继续显示占位省略号。"""
        widget = ArchiveFileTree()
        widget.set_lazy_mode(True)
        widget.load_folder(self.root)

        folder_item = widget._find_item_by_path(widget.invisibleRootItem(), str(self.folder_a))
        assert folder_item is not None
        assert folder_item.childCount() == 1
        assert folder_item.child(0).text(0).strip() == "..."

        widget._on_item_expanded(folder_item)

        loaded_child_names = {
            folder_item.child(index).text(0)
            for index in range(folder_item.childCount())
        }
        assert "银行流水.txt" in loaded_child_names
        assert "..." not in loaded_child_names
