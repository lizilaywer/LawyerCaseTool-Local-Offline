# -*- coding: utf-8 -*-
"""OCR 工作线程 - 后台执行OCR识别"""

import tempfile
import os
import re
import hashlib
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QThread, Signal, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QPixmap

from src.core.ocr.paddle_engine import get_ocr_engine, OCRTextBlock
from src.utils.logger import get_logger

# 预编译正则：去除中文与任意字符之间的多余空格
_CJK = r'[\u4e00-\u9fa5]'
_CLEANUP_SPACES = re.compile(
    rf'({_CJK}) +([^{_CJK}])'   # 中文→非中文
    rf'|([^{_CJK}]) +({_CJK})'   # 非中文→中文
    rf'|({_CJK}) +({_CJK})'      # 中文→中文
)

_OCR_RESULT_CACHE: OrderedDict[str, tuple[str, list]] = OrderedDict()
_OCR_RESULT_CACHE_LIMIT = 24


class OcrWorker(QThread):
    """OCR 识别工作线程

    信号：
    - ocr_completed(str, list): 识别完成 (识别文本, OCRTextBlock列表)
    - clipboard_requested(str): 请求主线程复制文本到剪贴板
    - ocr_failed(str): 识别失败 (错误信息)
    """

    ocr_completed = Signal(str, list)      # (识别文本, OCRTextBlock列表)
    clipboard_requested = Signal(str)      # 主线程剪贴板操作
    ocr_failed = Signal(str)               # 错误信息

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._logger = get_logger()
        self._pixmap = pixmap
        self._temp_file: str = None

    def run(self) -> None:
        """执行OCR识别"""
        try:
            # 检查截图是否有效
            if self._pixmap.isNull():
                raise RuntimeError("截图无效（空图片）")

            self._logger.debug(f"截图尺寸: {self._pixmap.width()}x{self._pixmap.height()}")
            cache_key = self._pixmap_cache_key(self._pixmap)
            cached = _OCR_RESULT_CACHE.get(cache_key)
            if cached is not None:
                _OCR_RESULT_CACHE.move_to_end(cache_key)
                full_text, text_blocks = cached
                self._logger.debug("使用缓存的 OCR 结果")
                self.ocr_completed.emit(full_text, text_blocks)
                if full_text:
                    self.clipboard_requested.emit(full_text)
                return

            # 保存截图到临时文件
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                self._temp_file = f.name

            # 保存图片（高质量PNG）
            if not self._pixmap.save(self._temp_file, 'PNG', quality=100):
                raise RuntimeError(f"无法保存截图到临时文件: {self._temp_file}")

            self._logger.debug(f"截图已保存: {self._temp_file}，大小: {os.path.getsize(self._temp_file)} bytes")

            # 获取OCR引擎
            engine = get_ocr_engine()
            if not engine.is_ready():
                raise RuntimeError("OCR引擎未就绪，请检查RapidOCR是否已安装")

            # 执行识别
            text_blocks = engine.recognize(self._temp_file)

            if not text_blocks:
                _OCR_RESULT_CACHE[cache_key] = ("", [])
                _OCR_RESULT_CACHE.move_to_end(cache_key)
                self.ocr_completed.emit("", [])
                return

            # 按阅读顺序排序并合并为行（单次分组，避免重复）
            rows = self._group_into_rows(text_blocks)
            sorted_blocks = [b for row in rows for b in row]
            full_text = self._rows_to_text(rows)

            self._logger.debug(f"OCR识别完成: {len(text_blocks)} 个文本块 -> '{full_text[:50]}...'")
            _OCR_RESULT_CACHE[cache_key] = (full_text, sorted_blocks)
            _OCR_RESULT_CACHE.move_to_end(cache_key)
            while len(_OCR_RESULT_CACHE) > _OCR_RESULT_CACHE_LIMIT:
                _OCR_RESULT_CACHE.popitem(last=False)

            self.ocr_completed.emit(full_text, sorted_blocks)
            # 剪贴板操作必须在主线程，通过信号通知
            self.clipboard_requested.emit(full_text)

        except Exception as e:
            self._logger.error(f"OCR识别失败: {e}")
            self.ocr_failed.emit(str(e))

        finally:
            # 清理临时文件
            if self._temp_file and os.path.exists(self._temp_file):
                try:
                    os.unlink(self._temp_file)
                except Exception as e:
                    self._logger.warning(f"清理临时文件失败: {e}")

    # ── 行分组与文本合并 ──

    @staticmethod
    def _pixmap_cache_key(pixmap: QPixmap) -> str:
        """生成截图内容缓存键。"""
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG", quality=100)
        return hashlib.sha256(bytes(data)).hexdigest()

    @staticmethod
    def _block_center_y(block) -> float:
        y_coords = [p[1] for p in block.box]
        return sum(y_coords) / len(y_coords)

    @staticmethod
    def _block_center_x(block) -> float:
        x_coords = [p[0] for p in block.box]
        return sum(x_coords) / len(x_coords)

    @staticmethod
    def _block_height(block) -> float:
        y_coords = [p[1] for p in block.box]
        return max(y_coords) - min(y_coords)

    def _group_into_rows(self, text_blocks: list) -> list:
        """将文本块按阅读顺序分组为二维列表。

        先按中心 y 坐标排序，再用线性扫描合并邻近块为同一行，
        时间复杂度 O(n log n)。
        """
        if not text_blocks:
            return []

        avg_height = sum(self._block_height(b) for b in text_blocks) / len(text_blocks)
        threshold = avg_height * 0.8

        # 按 y 排序
        sorted_blocks = sorted(text_blocks, key=self._block_center_y)

        rows = []
        for block in sorted_blocks:
            cy = self._block_center_y(block)
            placed = False
            for row in rows:
                row_cy = sum(self._block_center_y(b) for b in row) / len(row)
                if abs(cy - row_cy) < threshold:
                    row.append(block)
                    placed = True
                    break
            if not placed:
                rows.append([block])

        # 行内按 x 排序
        for row in rows:
            row.sort(key=self._block_center_x)

        return rows

    def _rows_to_text(self, rows: list) -> str:
        """将行分组转换为清理后的文本。"""
        lines = []
        for row in rows:
            line_text = " ".join(b.text for b in row)
            lines.append(line_text)

        full_text = "\n".join(lines)

        # 清理文本
        full_text = full_text.strip()
        full_text = re.sub(r' +', ' ', full_text)
        full_text = _CLEANUP_SPACES.sub(
            lambda m: m.group(1) or m.group(3) or m.group(5) or ''
                     + (m.group(2) or m.group(4) or m.group(6) or ''),
            full_text,
        )

        return full_text
