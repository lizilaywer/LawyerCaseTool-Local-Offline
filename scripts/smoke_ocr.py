# -*- coding: utf-8 -*-
"""OCR 冒烟测试脚本"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.ocr import get_ocr_engine


def _create_smoke_image(output_path: Path) -> None:
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]

    font = None
    for candidate in font_candidates:
        if Path(candidate).exists():
            try:
                font = ImageFont.truetype(candidate, 44)
                break
            except OSError:
                continue

    if font is None:
        font = ImageFont.load_default()

    image = Image.new("RGB", (1200, 320), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 60), "CASE 2026-001", fill="black", font=font)
    draw.text((60, 150), "Client Zhang San", fill="black", font=font)
    image.save(output_path)


def main() -> int:
    output_dir = Path(".tmp-ocr")
    output_dir.mkdir(exist_ok=True)
    image_path = output_dir / "ocr_smoke.png"

    _create_smoke_image(image_path)

    engine = get_ocr_engine()
    if not engine.is_ready():
        print("OCR_NOT_READY")
        return 1

    blocks = engine.recognize(str(image_path))
    print(f"BLOCKS {len(blocks)}")
    for block in blocks[:10]:
        print(f"{block.text}\t{block.confidence:.3f}")

    return 0 if blocks else 1


if __name__ == "__main__":
    raise SystemExit(main())
