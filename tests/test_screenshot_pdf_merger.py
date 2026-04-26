# -*- coding: utf-8 -*-
"""截图合并 PDF 核心引擎测试"""

from pathlib import Path

import pytest
from PIL import Image

from src.core.screenshot_pdf_merger import ScreenshotPdfMerger


class TestScreenshotPdfMerger:
    """ScreenshotPdfMerger 测试类"""

    def setup_method(self):
        self.merger = ScreenshotPdfMerger()

    def test_sort_key_numeric_extracts_all_number_groups(self):
        """sort_key_numeric 应提取文件名中所有连续数字"""
        assert self.merger.sort_key_numeric("微信图片_20251216_637_15.jpg") == [20251216, 637, 15]
        assert self.merger.sort_key_numeric("screenshot_001.png") == [1]
        assert self.merger.sort_key_numeric("abc_def.png") == []

    def test_sort_images_ascending(self):
        """正序排序应按数字从小到大排列"""
        images = [
            Path("微信图片_638.jpg"),
            Path("微信图片_637.jpg"),
            Path("微信图片_639.jpg"),
        ]
        result = self.merger.sort_images(images, order="asc")
        assert [p.name for p in result] == ["微信图片_637.jpg", "微信图片_638.jpg", "微信图片_639.jpg"]

    def test_sort_images_descending(self):
        """倒序排序应按数字从大到小排列"""
        images = [
            Path("微信图片_638.jpg"),
            Path("微信图片_637.jpg"),
            Path("微信图片_639.jpg"),
        ]
        result = self.merger.sort_images(images, order="desc")
        assert [p.name for p in result] == ["微信图片_639.jpg", "微信图片_638.jpg", "微信图片_637.jpg"]

    def test_sort_images_manual(self):
        """手动排序应保持原顺序"""
        images = [
            Path("微信图片_639.jpg"),
            Path("微信图片_637.jpg"),
            Path("微信图片_638.jpg"),
        ]
        result = self.merger.sort_images(images, order="manual")
        assert [p.name for p in result] == ["微信图片_639.jpg", "微信图片_637.jpg", "微信图片_638.jpg"]

    def test_sort_images_no_numbers_fallback(self):
        """无数字的文件名应按字母顺序兜底"""
        images = [
            Path("b_screenshot.png"),
            Path("a_screenshot.png"),
            Path("c_screenshot.png"),
        ]
        result = self.merger.sort_images(images, order="asc")
        assert [p.name for p in result] == ["a_screenshot.png", "b_screenshot.png", "c_screenshot.png"]

    def test_collect_images_from_mixed_paths(self, tmp_path):
        """从混合路径（文件+文件夹）中收集图片"""
        # 创建文件夹和文件
        folder = tmp_path / "screenshots"
        folder.mkdir()
        (folder / "img1.jpg").write_bytes(b"")
        (folder / "img2.png").write_bytes(b"")
        (folder / "readme.txt").write_bytes(b"")  # 应被忽略

        single_file = tmp_path / "standalone.png"
        single_file.write_bytes(b"")

        result = self.merger.collect_images([folder, single_file])
        names = {p.name for p in result}
        assert names == {"img1.jpg", "img2.png", "standalone.png"}

    def test_generate_pdf_with_temp_images(self, tmp_path):
        """使用临时图片生成 PDF"""
        # 创建 2 张测试图片
        images = []
        for i in range(2):
            img_path = tmp_path / f"test_{i}.png"
            img = Image.new("RGB", (1080, 1920), color=(i * 50, i * 50, i * 50))
            img.save(img_path)
            images.append(img_path)

        output_pdf = tmp_path / "output.pdf"
        progress_calls = []

        def progress(current, total):
            progress_calls.append((current, total))

        result = self.merger.generate_pdf(
            images,
            output_pdf,
            per_page=2,
            orientation="L",
            margin_mm=15,
            gap_mm=8,
            label_position="top",
            label_mode="auto",
            label_prefix="图",
            progress_callback=progress,
        )

        assert result.exists()
        assert result.stat().st_size > 0
        assert progress_calls == [(1, 1)]

    def test_generate_pdf_invalid_per_page(self, tmp_path):
        """per_page 非法时应抛出 ValueError"""
        # 先创建一张假图片避免空列表检查
        img_path = tmp_path / "dummy.png"
        Image.new("RGB", (100, 100), color=(0, 0, 0)).save(img_path)
        with pytest.raises(ValueError, match="per_page 必须是"):
            self.merger.generate_pdf([img_path], tmp_path / "out.pdf", per_page=4)

    def test_generate_pdf_empty_images(self, tmp_path):
        """空图片列表时应抛出 ValueError"""
        with pytest.raises(ValueError, match="图片列表为空"):
            self.merger.generate_pdf([], tmp_path / "out.pdf")

    def test_get_label_text_various_modes(self):
        """测试不同标签模式下的文字生成"""
        path = Path("微信图片_637.jpg")
        assert self.merger._get_label_text(0, path, "auto", "图") == "图1"
        assert self.merger._get_label_text(2, path, "custom", "截图") == "截图3"
        assert self.merger._get_label_text(0, path, "filename", "") == "微信图片_637"
        assert self.merger._get_label_text(0, path, "none", "") == ""
