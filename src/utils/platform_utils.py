# -*- coding: utf-8 -*-
"""平台适配工具模块"""

import os
import subprocess
import sys
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Optional, Tuple, Union


PathLike = Union[str, Path]


def is_windows() -> bool:
    """是否为 Windows。"""
    return sys.platform == "win32"


def is_macos() -> bool:
    """是否为 macOS。"""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """是否为 Linux。"""
    return sys.platform.startswith("linux")


def get_platform_name() -> str:
    """获取平台名称。"""
    if is_windows():
        return "windows"
    if is_macos():
        return "macos"
    if is_linux():
        return "linux"
    return "unknown"


def get_app_data_dir(app_name: str = "LawyerCaseTool") -> Path:
    """获取当前平台推荐的应用数据目录。"""
    if is_windows():
        base_dir = os.environ.get("APPDATA")
        if base_dir:
            return Path(base_dir) / app_name
        return Path.home() / "AppData" / "Roaming" / app_name

    if is_macos():
        return Path.home() / "Library" / "Application Support" / app_name

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / app_name
    return Path.home() / ".local" / "share" / app_name


def get_documents_dir() -> Path:
    """获取当前平台默认文稿目录。"""
    home_dir = Path.home()
    candidates = []

    if is_windows():
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            return Path(str(PureWindowsPath(user_profile) / "Documents"))
        return home_dir / "Documents"
    elif is_macos():
        candidates.append(home_dir / "Documents")
    else:
        xdg_documents_dir = os.environ.get("XDG_DOCUMENTS_DIR")
        if xdg_documents_dir:
            candidates.append(Path(xdg_documents_dir).expanduser())
        candidates.append(home_dir / "Documents")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if candidates:
        return candidates[0]
    return home_dir


def get_desktop_dir() -> Path:
    """获取当前平台默认桌面目录。"""
    home_dir = Path.home()
    candidates = []

    if is_windows():
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            return Path(str(PureWindowsPath(user_profile) / "Desktop"))
        # 部分环境使用 OneDrive 桌面
        onedrive_desktop = os.environ.get("OneDrive") or os.environ.get("ONEDRIVE")
        if onedrive_desktop:
            return Path(str(PureWindowsPath(onedrive_desktop) / "Desktop"))
        return home_dir / "Desktop"
    elif is_macos():
        candidates.append(home_dir / "Desktop")
    else:
        xdg_desktop_dir = os.environ.get("XDG_DESKTOP_DIR")
        if xdg_desktop_dir:
            candidates.append(Path(xdg_desktop_dir).expanduser())
        candidates.append(home_dir / "Desktop")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if candidates:
        return candidates[0]
    return home_dir


def get_default_output_dir(folder_name: str = "案卷") -> Path:
    """获取默认案卷输出目录。"""
    if is_windows():
        return Path(str(PureWindowsPath(str(get_desktop_dir())) / folder_name))
    return get_desktop_dir() / folder_name


def get_default_ui_font_family() -> str:
    """获取平台默认 UI 字体。"""
    if is_windows():
        return "Microsoft YaHei UI"
    if is_macos():
        return "PingFang SC"
    return "Noto Sans CJK SC"


def get_default_monospace_font_family() -> str:
    """获取平台默认等宽字体。"""
    if is_windows():
        return "Consolas"
    if is_macos():
        return "Menlo"
    return "Noto Sans Mono"


def supports_context_menu_integration() -> bool:
    """当前平台是否支持现有右键菜单集成实现。"""
    return is_windows()


def open_path(target: PathLike) -> Tuple[bool, Optional[str]]:
    """使用系统默认方式打开文件或文件夹。"""
    path = Path(target)
    if not path.exists():
        return False, f"路径不存在: {path}"

    try:
        if is_windows():
            os.startfile(str(path))
        elif is_macos():
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True, None
    except Exception as e:
        return False, str(e)


def get_current_process_memory_bytes() -> Optional[int]:
    """获取当前进程工作集内存，无法获取时返回 None。"""
    if is_windows():
        try:
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS_EX()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(),
                ctypes.byref(counters),
                counters.cb,
            )
            if ok:
                return int(counters.WorkingSetSize)
        except Exception:
            return None
        return None

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS 返回字节，Linux 返回 KiB。
        if is_macos():
            return int(usage)
        return int(usage) * 1024
    except Exception:
        return None
