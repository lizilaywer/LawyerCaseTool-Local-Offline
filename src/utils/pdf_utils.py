# -*- coding: utf-8 -*-
"""PDF 处理工具模块"""

import os
import io
from src.utils.logger import get_logger
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = get_logger()


@dataclass
class PDFPageInfo:
    """PDF 页面信息"""
    page_number: int
    width: float
    height: float
    image_path: Optional[str] = None


class PDFProcessor:
    """PDF 处理器"""
    
    # 默认 DPI（影响转换图片的清晰度）
    DEFAULT_DPI = 300
    
    def __init__(self, dpi: int = DEFAULT_DPI):
        """
        初始化 PDF 处理器
        
        Args:
            dpi: 转换图片的 DPI，默认 300
        """
        self.dpi = dpi
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查依赖是否安装"""
        if fitz is None:
            logger.warning("PyMuPDF (fitz) 未安装，PDF 处理功能受限")
    
    def is_available(self) -> bool:
        """检查 PDF 处理功能是否可用"""
        return fitz is not None
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        获取 PDF 页数
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            页数，失败返回 0
        """
        if not self.is_available():
            return 0
        
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.error(f"获取 PDF 页数失败: {e}")
            return 0
    
    def get_page_info(self, pdf_path: str) -> List[PDFPageInfo]:
        """
        获取 PDF 所有页面的信息
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            PDFPageInfo 列表
        """
        if not self.is_available():
            return []
        
        try:
            doc = fitz.open(pdf_path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                rect = page.rect
                pages.append(PDFPageInfo(
                    page_number=page_num + 1,
                    width=rect.width,
                    height=rect.height
                ))
            
            doc.close()
            return pages
            
        except Exception as e:
            logger.error(f"获取 PDF 页面信息失败: {e}")
            return []
    
    def convert_to_images(self, pdf_path: str, output_dir: str,
                         page_range: Optional[Tuple[int, int]] = None) -> List[str]:
        """
        将 PDF 转换为图片
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
            page_range: 页面范围 (起始页, 结束页)，从1开始，None 表示全部
            
        Returns:
            生成的图片路径列表
        """
        if not self.is_available():
            logger.error("PDF 处理依赖未安装")
            return []
        
        pdf_path = str(Path(pdf_path).resolve())
        output_dir = str(Path(output_dir).resolve())
        
        if not os.path.exists(pdf_path):
            logger.error(f"PDF 文件不存在: {pdf_path}")
            return []
        
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = []
        
        try:
            doc = fitz.open(pdf_path)
            
            # 确定页面范围
            total_pages = len(doc)
            if page_range:
                start_page = max(0, page_range[0] - 1)
                end_page = min(total_pages, page_range[1])
            else:
                start_page = 0
                end_page = total_pages
            
            pdf_name = Path(pdf_path).stem
            
            for page_num in range(start_page, end_page):
                page = doc[page_num]
                
                # 设置缩放矩阵以提高分辨率
                zoom = self.dpi / 72  # 72 是 PDF 默认 DPI
                mat = fitz.Matrix(zoom, zoom)
                
                # 渲染页面为图片
                pix = page.get_pixmap(matrix=mat)
                
                # 保存图片
                image_path = os.path.join(
                    output_dir, 
                    f"{pdf_name}_page_{page_num + 1}.png"
                )
                pix.save(image_path)
                image_paths.append(image_path)
                
                logger.debug(f"已转换页面 {page_num + 1}: {image_path}")
            
            doc.close()
            logger.info(f"PDF 转换完成，共 {len(image_paths)} 页")
            
        except Exception as e:
            logger.error(f"PDF 转换失败: {e}")
        
        return image_paths
    
    def convert_first_page(self, pdf_path: str, output_path: str) -> bool:
        """
        将 PDF 第一页转换为图片
        
        Args:
            pdf_path: PDF 文件路径
            output_path: 输出图片路径
            
        Returns:
            是否成功
        """
        images = self.convert_to_images(pdf_path, str(Path(output_path).parent), (1, 1))
        if images:
            # 重命名为指定输出路径
            os.rename(images[0], output_path)
            return True
        return False
    
    def extract_text(self, pdf_path: str, page_num: Optional[int] = None) -> str:
        """
        提取 PDF 文本内容
        
        Args:
            pdf_path: PDF 文件路径
            page_num: 页码（从1开始），None 表示提取全部
            
        Returns:
            提取的文本
        """
        if not self.is_available():
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            if page_num is not None:
                # 提取指定页
                idx = page_num - 1
                if 0 <= idx < len(doc):
                    text_parts.append(doc[idx].get_text())
            else:
                # 提取全部
                for page in doc:
                    text_parts.append(page.get_text())
            
            doc.close()
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"提取 PDF 文本失败: {e}")
            return ""
    
    @staticmethod
    def is_pdf(file_path: str) -> bool:
        """
        检查文件是否为 PDF
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为 PDF 文件
        """
        path = Path(file_path)
        if not path.exists():
            return False
        return path.suffix.lower() == '.pdf'
    
    @staticmethod
    def compress_pdf(input_path: str, output_path: str, quality: int = 2) -> bool:
        """
        压缩 PDF 文件
        
        Args:
            input_path: 输入 PDF 路径
            output_path: 输出 PDF 路径
            quality: 压缩质量 0-4，0 最低，4 最高
            
        Returns:
            是否成功
        """
        if fitz is None:
            logger.error("PyMuPDF 未安装")
            return False
        
        try:
            doc = fitz.open(input_path)
            
            # 压缩图片
            for page in doc:
                images = page.get_images()
                for img_index, img in enumerate(images):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    if pix.n > 4:  # CMYK 转 RGB
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    # 压缩图片
                    pix.shrink(quality)

                    # 替换图片（保留而非删除）
                    doc._updateObject(xref, pix.tobytes("png"))
                    pix = None  # 释放内存
            
            # 保存
            doc.save(output_path, garbage=4, deflate=True)
            doc.close()
            
            return True
            
        except Exception as e:
            logger.error(f"压缩 PDF 失败: {e}")
            return False


# 全局 PDF 处理器实例
_pdf_processor: Optional[PDFProcessor] = None


def get_pdf_processor() -> PDFProcessor:
    """
    获取全局 PDF 处理器实例
    
    Returns:
        PDFProcessor 实例
    """
    global _pdf_processor
    
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    
    return _pdf_processor
