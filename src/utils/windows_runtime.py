# -*- coding: utf-8 -*-
"""Windows 运行时优化与系统集成辅助。"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget

from src.utils.platform_utils import is_windows


APP_USER_MODEL_ID = "WangLi.LEXORA.2"


def configure_windows_process(app_user_model_id: str = APP_USER_MODEL_ID) -> None:
    """在 QApplication 创建前配置 Windows 进程级参数。

    包含 per-monitor DPI、任务栏 AppUserModelID 与 Qt 高 DPI 策略。
    所有调用都只在 Windows 执行，失败时静默降级，避免影响 macOS。
    """
    if not is_windows():
        return

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

    try:
        # 高 DPI 位图策略用于老版本 Qt/Windows 组合；新版本下失败也可安全忽略。
        QGuiApplication.setAttribute(
            Qt.ApplicationAttribute.AA_UseHighDpiPixmaps,
            True,
        )
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    try:
        import ctypes

        # PROCESS_PER_MONITOR_DPI_AWARE，Windows 8.1+ 可用；Windows 10/11 更稳定。
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_user_model_id
        )
    except Exception:
        pass


def apply_windows_qt_tuning(app: QApplication) -> None:
    """应用级 Windows Qt 调优。"""
    if not is_windows():
        return

    try:
        # 减少部分控件动画开销，提升低配 Windows 机器滚动/下拉响应。
        app.setEffectEnabled(Qt.UIEffect.UI_AnimateCombo, False)
        app.setEffectEnabled(Qt.UIEffect.UI_AnimateMenu, False)
        app.setWheelScrollLines(3)
    except Exception:
        pass


def apply_windows_window_tuning(window: QWidget, *, dark_title_bar: bool = False) -> None:
    """窗口级 Windows 调优。

    当前应用以浅色 UI 为主，因此默认不启用深色标题栏；函数保留 dark_title_bar
    参数，便于后续接入深色模式。
    """
    if not is_windows():
        return

    try:
        import ctypes

        hwnd = int(window.winId())
        value = ctypes.c_int(1 if dark_title_bar else 0)
        # DWMWA_USE_IMMERSIVE_DARK_MODE: Windows 10 1903+ / Windows 11。
        for attribute in (20, 19):
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if result == 0:
                break
    except Exception:
        pass


def windows_notification_available() -> bool:
    """当前运行环境是否具备基础 Windows 通知条件。"""
    return is_windows()
