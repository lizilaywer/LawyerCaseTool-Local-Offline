# -*- coding: utf-8 -*-
"""RapidOCR 引擎封装模块（替代 PaddleOCR）"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from threading import Lock

from src.utils.logger import get_logger

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:
    RapidOCR = None

logger = get_logger()
OCR_INSTALL_COMMAND = "pip install -r requirements-ocr.txt"


@dataclass(frozen=True)
class OCRAvailability:
    """OCR 可用性状态"""
    available: bool
    reason: str
    summary: str
    detail: str
    install_command: str = OCR_INSTALL_COMMAND


def get_ocr_dependency_status() -> OCRAvailability:
    """获取 OCR 依赖层的可用性状态。"""
    major, minor = sys.version_info[:2]
    python_version = f"{major}.{minor}"

    if RapidOCR is not None:
        return OCRAvailability(
            available=True,
            reason="ready",
            summary="OCR 增强依赖已安装",
            detail="可以使用身份证、判决书等文件的信息识别能力。",
        )

    if (major, minor) >= (3, 13):
        return OCRAvailability(
            available=False,
            reason="unsupported_python",
            summary=f"当前 Python {python_version} 暂不支持 OCR 增强依赖",
            detail="请使用 Python 3.12 或更低版本创建虚拟环境，再安装 OCR 依赖。",
        )

    return OCRAvailability(
        available=False,
        reason="missing_dependency",
        summary="OCR 增强依赖未安装",
        detail="请在项目虚拟环境中安装 OCR 依赖后再使用信息识别功能。",
    )


def format_ocr_setup_message(status: Optional[OCRAvailability] = None) -> str:
    """格式化 OCR 安装/说明文本。"""
    status = status or get_ocr_dependency_status()

    lines = [status.summary, "", status.detail]
    if not status.available:
        lines.extend(["", "建议在项目目录执行：", status.install_command])

    return "\n".join(lines)


@dataclass
class OCRTextBlock:
    """OCR 文本块"""
    text: str
    confidence: float
    box: List[Tuple[int, int]]  # 四个角点坐标 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
    
    @property
    def is_low_confidence(self) -> bool:
        """是否低置信度"""
        return self.confidence < 0.8


class RapidOCREngine:
    """RapidOCR 引擎封装（单例模式）- 替代 PaddleOCR"""
    
    _instance: Optional['RapidOCREngine'] = None
    _lock: Lock = Lock()
    
    # 置信度阈值
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.8
    LOW_CONFIDENCE = 0.6
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化 OCR 引擎"""
        if self._initialized:
            return
        self._ocr: Optional[RapidOCR] = None
        self._last_error: Optional[str] = None
    
    def _initialize(self) -> None:
        """初始化 RapidOCR"""
        dependency_status = get_ocr_dependency_status()
        if not dependency_status.available:
            self._last_error = format_ocr_setup_message(dependency_status)
            logger.error(dependency_status.summary)
            return
            
        try:
            logger.info("正在初始化 RapidOCR 引擎...")
            # RapidOCR 初始化非常简单，模型已内置
            self._ocr = RapidOCR()
            self._last_error = None
            self._initialized = True
            logger.info("RapidOCR 引擎初始化成功")
        except Exception as e:
            logger.error(f"RapidOCR 初始化失败: {e}")
            self._last_error = str(e)
            self._ocr = None
    
    def is_ready(self) -> bool:
        """检查引擎是否就绪"""
        if not self._initialized:
            self._initialize()
        return self._initialized and self._ocr is not None

    def get_last_error(self) -> Optional[str]:
        """获取最近一次初始化/运行错误。"""
        return self._last_error
    
    def recognize(self, image_path: str) -> List[OCRTextBlock]:
        """
        识别图片中的文字
        
        Args:
            image_path: 图片路径
            
        Returns:
            OCRTextBlock 列表
        """
        if not self.is_ready():
            logger.error("OCR 引擎未就绪")
            return []
        
        image_path = str(Path(image_path).resolve())
        
        if not os.path.exists(image_path):
            logger.error(f"图片不存在: {image_path}")
            return []
        
        try:
            # RapidOCR 调用方式
            result, elapse = self._ocr(image_path)
            
            if result is None or len(result) == 0:
                return []
            
            text_blocks = []
            # RapidOCR 返回格式: [(box, text, confidence), ...]
            # box 格式: [x1, y1, x2, y2, x3, y3, x4, y4]
            for item in result:
                if item is None or len(item) < 3:
                    continue
                
                box_data = item[0]  # 坐标数据
                text = item[1]
                confidence = item[2]
                
                # 处理不同的坐标格式
                # 格式1: [x1, y1, x2, y2, x3, y3, x4, y4] (扁平列表)
                # 格式2: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]] (嵌套列表)
                if isinstance(box_data, list) and len(box_data) == 8:
                    # 扁平列表格式
                    box = [
                        (int(box_data[0]), int(box_data[1])),
                        (int(box_data[2]), int(box_data[3])),
                        (int(box_data[4]), int(box_data[5])),
                        (int(box_data[6]), int(box_data[7])),
                    ]
                elif isinstance(box_data, list) and len(box_data) == 4:
                    # 嵌套列表格式 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    box = [
                        (int(box_data[0][0]), int(box_data[0][1])),
                        (int(box_data[1][0]), int(box_data[1][1])),
                        (int(box_data[2][0]), int(box_data[2][1])),
                        (int(box_data[3][0]), int(box_data[3][1])),
                    ]
                else:
                    # 未知格式，跳过
                    logger.warning(f"未知的坐标格式: {box_data}")
                    continue
                
                text_blocks.append(OCRTextBlock(
                    text=text,
                    confidence=confidence,
                    box=box
                ))
            
            logger.debug(f"识别到 {len(text_blocks)} 个文本块")
            return text_blocks
            
        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")
            return []
    
    def recognize_batch(self, image_paths: List[str]) -> Dict[str, List[OCRTextBlock]]:
        """
        批量识别图片
        
        Args:
            image_paths: 图片路径列表
            
        Returns:
            {图片路径: OCRTextBlock列表} 的字典
        """
        results = {}
        for path in image_paths:
            results[path] = self.recognize(path)
        return results
    
    @staticmethod
    def get_confidence_level(confidence: float) -> str:
        """
        获取置信度等级
        
        Args:
            confidence: 置信度值 (0-1)
            
        Returns:
            'high', 'medium', 'low', 'very_low'
        """
        if confidence >= RapidOCREngine.HIGH_CONFIDENCE:
            return 'high'
        elif confidence >= RapidOCREngine.MEDIUM_CONFIDENCE:
            return 'medium'
        elif confidence >= RapidOCREngine.LOW_CONFIDENCE:
            return 'low'
        else:
            return 'very_low'
    
    @staticmethod
    def get_confidence_color(confidence: float) -> str:
        """
        获取置信度对应的颜色（用于 UI 显示）
        
        Args:
            confidence: 置信度值 (0-1)
            
        Returns:
            CSS 颜色值
        """
        level = RapidOCREngine.get_confidence_level(confidence)
        colors = {
            'high': '#4caf50',      # 绿色
            'medium': '#ff9800',    # 橙色
            'low': '#f44336',       # 红色
            'very_low': '#9e9e9e',  # 灰色
        }
        return colors.get(level, '#9e9e9e')


# 为了兼容旧代码，保留 PaddleOCREngine 别名
PaddleOCREngine = RapidOCREngine

# 全局 OCR 引擎实例
_ocr_engine: Optional[RapidOCREngine] = None
_engine_lock = Lock()


def get_ocr_engine() -> RapidOCREngine:
    """
    获取全局 OCR 引擎实例（懒加载）
    
    Returns:
        RapidOCREngine 实例
    """
    global _ocr_engine
    
    if _ocr_engine is None:
        with _engine_lock:
            if _ocr_engine is None:
                _ocr_engine = RapidOCREngine()
    
    return _ocr_engine


def get_ocr_runtime_status() -> OCRAvailability:
    """获取 OCR 运行时可用性状态。"""
    dependency_status = get_ocr_dependency_status()
    if not dependency_status.available:
        return dependency_status

    engine = get_ocr_engine()
    if engine.is_ready():
        return OCRAvailability(
            available=True,
            reason="ready",
            summary="OCR 引擎已就绪",
            detail="可以开始识别身份证、判决书等文件。",
        )

    return OCRAvailability(
        available=False,
        reason="init_failed",
        summary="OCR 引擎初始化失败",
        detail=engine.get_last_error() or "请重新安装 OCR 依赖后再试。",
    )
