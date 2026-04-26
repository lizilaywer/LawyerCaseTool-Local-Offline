# -*- coding: utf-8 -*-
"""案卷预览控件测试"""

import shutil
import tempfile
from pathlib import Path

import pytest

from src.gui.widgets.archive_preview import ArchivePreview


class TestArchivePreview:
    """预览控件最小回归测试。"""

    def setup_method(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_preview_pdf_renders_with_pymupdf(self, qapp):
        fitz = pytest.importorskip("fitz")

        pdf_path = self.temp_dir / "sample.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PDF preview smoke")
        doc.save(str(pdf_path))
        doc.close()

        widget = ArchivePreview()
        widget.resize(720, 560)
        widget.show()
        qapp.processEvents()

        widget.preview_file(pdf_path)
        for _ in range(3):
            qapp.processEvents()

        pixmap = widget._image_label.pixmap()
        assert widget._current_type == "pdf"
        assert pixmap is not None
        assert not pixmap.isNull()
