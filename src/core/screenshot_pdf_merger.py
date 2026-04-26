# -*- coding: utf-8 -*-
"""截图合并 PDF 核心引擎

将图片（主要是微信聊天记录截图）合并为 PDF，支持多种布局、标签和排序选项。
"""

import io
import os
import platform
import re
from math import ceil
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from fpdf import FPDF
from PIL import Image

from src.utils.logger import get_logger

logger = get_logger()

# A4 尺寸（单位：mm）
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0

# 支持的图片扩展名
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


class ScreenshotPdfMerger:
    """将图片合并为 PDF 的核心引擎"""

    def __init__(self):
        self._font_name: Optional[str] = None
        self._font_path: Optional[str] = None

    # ------------------------------------------------------------------ #
    # 字体探测
    # ------------------------------------------------------------------ #
    @staticmethod
    def _detect_chinese_font() -> str:
        """探测系统中文字体路径

        Returns:
            可用字体文件的绝对路径

        Raises:
            RuntimeError: 找不到任何中文字体时抛出
        """
        system = platform.system()
        candidates: List[str] = []

        if system == "Windows":
            candidates = [
                r"C:\Windows\Fonts\simhei.ttf",
                r"C:\Windows\Fonts\msyh.ttc",
                r"C:\Windows\Fonts\msyhbd.ttc",
                r"C:\Windows\Fonts\simsun.ttc",
                r"C:\Windows\Fonts\simkai.ttf",
            ]
        elif system == "Darwin":  # macOS
            candidates = [
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
        else:  # Linux / 其他
            candidates = [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]

        for path in candidates:
            if os.path.isfile(path):
                logger.debug(f"找到中文字体: {path}")
                return path

        raise RuntimeError(
            f"未找到中文字体，PDF 标签中的中文将无法正确显示。"
            f"请安装中文字体后重试。已搜索路径：{candidates}"
        )

    def _get_font(self) -> Tuple[str, str]:
        """获取 fpdf2 可用的字体名称与路径（惰性加载）"""
        if self._font_path is None:
            self._font_path = self._detect_chinese_font()
            self._font_name = "ChineseFont"
        return self._font_name, self._font_path

    # ------------------------------------------------------------------ #
    # 图片收集
    # ------------------------------------------------------------------ #
    def collect_images(self, paths: List[Path]) -> List[Path]:
        """从文件或文件夹路径中收集所有支持的图片

        Args:
            paths: 文件或文件夹路径列表

        Returns:
            去重后的图片路径列表（按收集顺序）
        """
        images: List[Path] = []
        seen: set = set()

        for p in paths:
            p = Path(p)
            if not p.exists():
                logger.warning(f"路径不存在，跳过: {p}")
                continue

            if p.is_file():
                if p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
                    resolved = p.resolve()
                    if resolved not in seen:
                        seen.add(resolved)
                        images.append(resolved)
                else:
                    logger.warning(f"不支持的文件格式，跳过: {p}")
            elif p.is_dir():
                for ext in SUPPORTED_IMAGE_EXTENSIONS:
                    for file_path in p.rglob(f"*{ext}"):
                        resolved = file_path.resolve()
                        if resolved not in seen:
                            seen.add(resolved)
                            images.append(resolved)

        logger.info(f"共收集到 {len(images)} 张图片")
        return images

    # ------------------------------------------------------------------ #
    # 排序
    # ------------------------------------------------------------------ #
    @staticmethod
    def sort_key_numeric(filename: str) -> List[int]:
        """从文件名中提取所有连续数字段作为排序键

        例如 ``微信图片_20251216_637_15.jpg`` → ``[20251216, 637, 15]``

        Args:
            filename: 文件名（可含路径）

        Returns:
            提取到的整数列表；无数字时返回空列表
        """
        stem = Path(filename).stem
        numbers = re.findall(r"\d+", stem)
        return [int(n) for n in numbers]

    def sort_images(self, images: List[Path], order: str = "asc") -> List[Path]:
        """对图片列表进行排序

        Args:
            images: 图片路径列表
            order: ``"asc"`` 正序, ``"desc"`` 倒序, ``"manual"`` 保持原顺序

        Returns:
            排序后的图片路径列表
        """
        if order == "manual":
            return list(images)

        def _key(img: Path) -> tuple:
            nums = self.sort_key_numeric(str(img))
            name = img.stem.lower()
            # 有数字的排在前面，按数字序列比较；无数字的按文件名兜底
            return (0 if nums else 1, nums, name)

        sorted_images = sorted(images, key=_key)

        if order == "desc":
            sorted_images = list(reversed(sorted_images))

        return sorted_images

    # ------------------------------------------------------------------ #
    # 标签文字生成
    # ------------------------------------------------------------------ #
    @staticmethod
    def _get_label_text(
        index: int,
        img_path: Path,
        mode: str,
        prefix: str,
    ) -> str:
        """根据标签模式生成单张图片的标签文字"""
        if mode == "none":
            return ""
        if mode in ("auto", "custom"):
            return f"{prefix}{index + 1}"
        if mode == "filename":
            return img_path.stem
        return ""

    # ------------------------------------------------------------------ #
    # PDF 生成
    # ------------------------------------------------------------------ #
    def generate_pdf(
        self,
        images: List[Path],
        output_path: Path,
        *,
        per_page: int = 2,
        orientation: str = "L",
        margin_mm: float = 15.0,
        gap_mm: float = 8.0,
        label_position: str = "top",
        label_mode: str = "auto",
        label_prefix: str = "图",
        label_font_size: int = 12,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """将图片合并生成 PDF

        Args:
            images: 已排序的图片路径列表
            output_path: 输出 PDF 路径
            per_page: 每页放置图片数量（1/2/3）
            orientation: 页面方向，``"L"`` 横向，``"P"`` 纵向
            margin_mm: 页边距（mm）
            gap_mm: 图片间间距（mm）
            label_position: 标签位置，``"top"`` / ``"bottom"`` / ``"none"``
            label_mode: 标签模式，``"auto"`` / ``"custom"`` / ``"filename"`` / ``"none"``
            label_prefix: 自定义前缀（用于 ``"auto"`` / ``"custom"``）
            label_font_size: 标签字体大小（pt）
            progress_callback: 进度回调 ``callback(current_page, total_pages)``

        Returns:
            生成的 PDF 文件路径

        Raises:
            ValueError: 参数非法或可用空间不足
            RuntimeError: 找不到中文字体
        """
        if not images:
            raise ValueError("图片列表为空，无法生成 PDF")
        if per_page not in (1, 2, 3):
            raise ValueError("per_page 必须是 1、2 或 3")
        if orientation not in ("L", "P"):
            raise ValueError("orientation 必须是 'L'（横向）或 'P'（纵向）")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 字体
        font_name, font_path = self._get_font()

        # 初始化 PDF
        pdf = FPDF(orientation=orientation, unit="mm", format="A4")
        pdf.set_auto_page_break(False)
        pdf.add_font(font_name, "", font_path, uni=True)

        page_w = pdf.w
        page_h = pdf.h

        # 标签相关尺寸（单位：mm）
        has_label = label_position != "none" and label_mode != "none"
        # 1 pt ≈ 0.3528 mm，额外加 1 mm 边距
        label_height_mm = label_font_size * 0.3528 + 1.0 if has_label else 0.0
        label_gap_mm = 2.0 if has_label else 0.0

        # 内容可用尺寸
        content_w = page_w - 2 * margin_mm
        content_h = page_h - 2 * margin_mm

        if content_h <= 0 or content_w <= 0:
            raise ValueError(
                "当前边距设置导致可用空间不足，请调小 margin_mm"
            )

        total_pages = ceil(len(images) / per_page)
        logger.info(
            f"开始生成 PDF: {len(images)} 张图片, {per_page} 张/页, "
            f"共 {total_pages} 页, 方向={orientation}"
        )

        for page_idx in range(total_pages):
            pdf.add_page()
            page_images = images[page_idx * per_page : (page_idx + 1) * per_page]
            col_count = len(page_images)

            # 每列宽度
            col_w = (content_w - gap_mm * (col_count - 1)) / col_count if col_count > 0 else content_w

            # 先处理本页所有图片：读取、缩放、转码，然后立即关闭 Pillow 对象
            items: List[dict] = []
            for offset, img_path in enumerate(page_images):
                global_idx = page_idx * per_page + offset
                label_text = ""
                if has_label:
                    label_text = self._get_label_text(
                        global_idx, img_path, label_mode, label_prefix
                    )

                # 打开并缩放图片
                with Image.open(str(img_path)) as img:
                    orig_w, orig_h = img.size
                    aspect = orig_h / orig_w

                    # 先按列宽缩放
                    draw_w = col_w
                    draw_h = draw_w * aspect

                    # 可用高度（扣除标签）
                    usable_h = content_h - (label_height_mm + label_gap_mm if has_label else 0)

                    # 若高度超出上限，则按高度缩放
                    if draw_h > usable_h:
                        draw_h = usable_h
                        draw_w = draw_h / aspect

                    # 水平居中（在列内）
                    col_x = margin_mm + offset * (col_w + gap_mm)
                    x = col_x + (col_w - draw_w) / 2

                    # 统一转为 RGB 并写入 BytesIO，避免内存泄漏与格式兼容问题
                    img_rgb = img.convert("RGB") if img.mode != "RGB" else img.copy()

                img_bytes = io.BytesIO()
                img_rgb.save(img_bytes, format="JPEG", quality=95)
                img_bytes.seek(0)
                img_rgb.close()

                items.append(
                    {
                        "bytes": img_bytes,
                        "x": x,
                        "w": draw_w,
                        "h": draw_h,
                        "label": label_text,
                        "col_x": col_x,
                        "col_w": col_w,
                    }
                )

            # 绘制本页内容
            for item in items:
                if has_label and label_position == "top":
                    # 标签（在列内居中）
                    pdf.set_xy(item["col_x"], margin_mm)
                    pdf.set_font(font_name, "", label_font_size)
                    pdf.cell(item["col_w"], label_height_mm, item["label"], align="C")

                    # 图片
                    pdf.image(
                        item["bytes"],
                        x=item["x"],
                        y=margin_mm + label_height_mm + label_gap_mm,
                        w=item["w"],
                        h=item["h"],
                    )

                elif has_label and label_position == "bottom":
                    # 图片
                    pdf.image(
                        item["bytes"],
                        x=item["x"],
                        y=margin_mm,
                        w=item["w"],
                        h=item["h"],
                    )

                    # 标签（在列内居中）
                    pdf.set_xy(item["col_x"], margin_mm + item["h"] + label_gap_mm)
                    pdf.set_font(font_name, "", label_font_size)
                    pdf.cell(item["col_w"], label_height_mm, item["label"], align="C")

                else:
                    # 无标签
                    pdf.image(
                        item["bytes"],
                        x=item["x"],
                        y=margin_mm,
                        w=item["w"],
                        h=item["h"],
                    )

                # 关闭 BytesIO
                item["bytes"].close()

            # 进度回调（每处理一页调用一次）
            if progress_callback is not None:
                try:
                    progress_callback(page_idx + 1, total_pages)
                except Exception as exc:
                    logger.warning(f"进度回调执行失败: {exc}")

        pdf.output(str(output_path))
        logger.info(f"PDF 生成完成: {output_path}")
        return output_path
