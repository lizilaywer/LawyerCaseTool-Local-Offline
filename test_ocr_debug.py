# -*- coding: utf-8 -*-
"""OCR调试脚本"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path

# 1. 测试PDF转换和OCR
from src.core.ocr import get_ocr_engine
from src.utils.pdf_utils import get_pdf_processor

pdf_path = "江兴祥判决书.pdf.pdf"  # 修改为你的PDF路径

print("=" * 60)
print("步骤1: PDF转图片")
print("=" * 60)

pdf_processor = get_pdf_processor()
if not pdf_processor.is_available():
    print("PDF处理器不可用")
    sys.exit(1)

temp_dir = Path("temp_ocr")
temp_dir.mkdir(exist_ok=True)

image_paths = pdf_processor.convert_to_images(
    pdf_path,
    str(temp_dir),
    page_range=(1, 1)  # 只处理第一页
)

print(f"生成的图片: {image_paths}")

print("\n" + "=" * 60)
print("步骤2: OCR识别")
print("=" * 60)

ocr_engine = get_ocr_engine()
if not ocr_engine.is_ready():
    print("OCR引擎未就绪")
    sys.exit(1)

if image_paths:
    ocr_results = ocr_engine.recognize(image_paths[0])
    print(f"识别到 {len(ocr_results)} 个文本块:")
    print()
    
    for i, block in enumerate(ocr_results):
        print(f"[{i:2d}] {block.text}")
    
    # 合并文本
    full_text = '\n'.join([block.text for block in ocr_results])
    
    print("\n" + "=" * 60)
    print("步骤3: 解析判决书")
    print("=" * 60)
    
    from src.core.ocr.parsers import JudgmentParser
    
    parser = JudgmentParser()
    result = parser.parse(ocr_results)
    
    if result:
        print(f"解析成功! 字段数: {len(result.fields)}")
        print("\n识别到的字段:")
        for name, field in result.fields.items():
            value = field.value[:100] + "..." if len(field.value) > 100 else field.value
            print(f"  - {name}: {value}")
    else:
        print("解析失败!")
        
        # 手动测试分段
        print("\n手动测试分段:")
        sections = parser._split_sections()
        print(f"分段数: {len(sections)}")
        for section, content in sections.items():
            content_preview = content[:200] + "..." if len(content) > 200 else content
            print(f"\n[{section.value}]:")
            print(f"  {content_preview}")

# 清理
import shutil
if temp_dir.exists():
    shutil.rmtree(temp_dir)
