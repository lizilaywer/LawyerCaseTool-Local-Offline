# -*- coding: utf-8 -*-
"""应用程序入口"""

import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer

_PROCESS_START_TIME = time.perf_counter()

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app import get_application
from src.utils.logger import get_logger
from src.utils.platform_utils import get_current_process_memory_bytes, get_platform_name


def parse_command_line():
    """解析命令行参数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="案件文件夹管理系统"
    )
    parser.add_argument(
        "--directory", "-d",
        type=str,
        help="指定输出目录"
    )
    parser.add_argument(
        "--template", "-t",
        type=str,
        help="指定模板 ID"
    )
    parser.add_argument(
        "--benchmark-startup",
        action="store_true",
        help="输出启动性能 JSON，并在短暂显示窗口后退出"
    )
    parser.add_argument(
        "--benchmark-exit-ms",
        type=int,
        default=1200,
        help="启动性能探针显示窗口后的自动退出延迟（毫秒）"
    )
    parser.add_argument(
        "--import-backup",
        type=str,
        help="导入指定的 LEXORA 备份文件（用于 Windows 文件关联）"
    )

    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_command_line()

    # 初始化应用程序
    app = get_application()
    qt_app = app.initialize(sys.argv)

    logger = get_logger()
    logger.info("应用程序启动")

    # 创建主窗口
    from src.gui.main_window import MainWindow

    window = MainWindow()

    # 处理命令行参数
    if args.directory:
        # 从右键菜单启动时，设置输出目录
        directory_path = Path(args.directory).resolve()
        if not directory_path.is_dir():
            logger.error(f"指定的输出目录不存在或不是有效目录: {directory_path}")
            print(f"错误: 指定的输出目录不存在或不是有效目录: {directory_path}", file=sys.stderr)
            sys.exit(1)
        from src.config.config_manager import get_config_manager
        config_manager = get_config_manager()
        config_manager.set(
            "generation.default_output_dir",
            str(directory_path)
        )
        logger.info(f"设置输出目录: {directory_path}")

    if args.template:
        # 选择指定模板
        window._select_template(args.template)
        logger.info(f"选择模板: {args.template}")

    # 显示主窗口（工作台首页）
    window.show()

    if args.import_backup:
        backup_path = Path(args.import_backup).expanduser()

        def _open_backup_import() -> None:
            if not backup_path.exists() or not backup_path.is_file():
                from PySide6.QtWidgets import QMessageBox

                QMessageBox.warning(
                    window,
                    "导入失败",
                    f"备份文件不存在或不可读取：\n{backup_path}",
                )
                return

            from src.gui.settings_dialog import SettingsDialog

            dialog = SettingsDialog(window)
            window._pending_backup_import_dialog = dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            dialog.import_backup_from_path(
                backup_path.resolve(),
                allow_restore_case_files=False,
            )

        QTimer.singleShot(250, _open_backup_import)

    if args.benchmark_startup:
        tick_times = []
        tick_timer = QTimer()
        tick_timer.setInterval(16)
        tick_timer.timeout.connect(lambda: tick_times.append(time.perf_counter()))
        tick_timer.start()

        def _finish_startup_benchmark():
            tick_timer.stop()
            memory_bytes = get_current_process_memory_bytes()
            tick_duration = (
                tick_times[-1] - tick_times[0]
                if len(tick_times) >= 2 else 0
            )
            tick_hz = (
                round((len(tick_times) - 1) / tick_duration, 2)
                if tick_duration > 0 else None
            )
            metrics = {
                "platform": get_platform_name(),
                "startup_ms": round((time.perf_counter() - _PROCESS_START_TIME) * 1000, 2),
                "memory_rss_mb": round(memory_bytes / 1024 / 1024, 2) if memory_bytes else None,
                "event_loop_tick_hz": tick_hz,
                "frame_tick_hz": tick_hz,
                "window_width": window.width(),
                "window_height": window.height(),
            }
            print("LEXORA_BENCHMARK " + json.dumps(metrics, ensure_ascii=False), flush=True)
            qt_app.quit()

        QTimer.singleShot(max(100, int(args.benchmark_exit_ms)), _finish_startup_benchmark)

    # 运行事件循环
    exit_code = app.run()
    logger.info(f"应用程序退出，代码: {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
