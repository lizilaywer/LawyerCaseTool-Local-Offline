# -*- coding: utf-8 -*-
"""OCR 状态检测测试"""

from src.core.ocr import paddle_engine


class TestOCRStatus:
    """OCR 状态检测测试类"""

    def test_reports_unsupported_python_when_dependency_missing(self, monkeypatch):
        """缺少依赖且 Python 过新时应提示版本不受支持"""
        monkeypatch.setattr(paddle_engine, "RapidOCR", None)
        monkeypatch.setattr(paddle_engine.sys, "version_info", (3, 14, 0, "final", 0))

        status = paddle_engine.get_ocr_dependency_status()

        assert status.available is False
        assert status.reason == "unsupported_python"
        assert "3.14" in status.summary
        assert "requirements-ocr.txt" in paddle_engine.format_ocr_setup_message(status)

    def test_reports_missing_dependency_on_supported_python(self, monkeypatch):
        """支持的 Python 版本下缺少依赖应提示安装依赖"""
        monkeypatch.setattr(paddle_engine, "RapidOCR", None)
        monkeypatch.setattr(paddle_engine.sys, "version_info", (3, 12, 2, "final", 0))

        status = paddle_engine.get_ocr_dependency_status()

        assert status.available is False
        assert status.reason == "missing_dependency"
        assert "安装 OCR 依赖" in status.detail

    def test_reports_ready_when_dependency_is_importable(self, monkeypatch):
        """依赖可导入时应报告为可用"""
        monkeypatch.setattr(paddle_engine, "RapidOCR", object)
        monkeypatch.setattr(paddle_engine.sys, "version_info", (3, 14, 0, "final", 0))

        status = paddle_engine.get_ocr_dependency_status()

        assert status.available is True
        assert status.reason == "ready"
