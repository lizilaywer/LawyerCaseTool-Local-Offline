# -*- coding: utf-8 -*-
"""Windows 运行时优化辅助测试。"""

from src.utils import windows_runtime


def test_windows_runtime_noop_on_non_windows(monkeypatch):
    """非 Windows 平台调用 Windows 调优应安全无副作用。"""
    monkeypatch.setattr(windows_runtime, "is_windows", lambda: False)

    windows_runtime.configure_windows_process()
    windows_runtime.apply_windows_window_tuning(object())  # type: ignore[arg-type]

    assert windows_runtime.windows_notification_available() is False
