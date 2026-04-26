# -*- coding: utf-8 -*-
"""
OCR文档解析器模块

支持从各类证件和文档中提取结构化信息
"""

# 身份证件类解析器
from src.core.ocr.parsers.id_card_parser import (
    IDCardFrontParser,
    IDCardBackParser,
)

from src.core.ocr.parsers.household_parser import (
    HouseholdParser,
)

from src.core.ocr.parsers.passport_parser import (
    PassportParser,
)

from src.core.ocr.parsers.license_parser import (
    LicenseParser,
)

from src.core.ocr.parsers.business_license_parser import (
    BusinessLicenseParser,
)

__all__ = [
    # 身份证件类
    'IDCardFrontParser',
    'IDCardBackParser',
    'HouseholdParser',
    'PassportParser',
    'LicenseParser',
    'BusinessLicenseParser',
]
