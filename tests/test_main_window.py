# -*- coding: utf-8 -*-
"""主窗口启动流测试"""

from PySide6.QtWidgets import QWidget

from src.gui.main_window import MainWindow


def _patch_main_window_bootstrap(monkeypatch):
    monkeypatch.setattr(MainWindow, "_setup_window_icon", lambda self: None)
    monkeypatch.setattr(MainWindow, "_setup_styles", lambda self: None)
    monkeypatch.setattr(MainWindow, "_refresh_ocr_ui_state", lambda self: None)
    monkeypatch.setattr(MainWindow, "_load_templates", lambda self: None)
    monkeypatch.setattr(MainWindow, "_restore_geometry", lambda self: None)

    def _minimal_setup_ui(self):
        self.setCentralWidget(QWidget())

    monkeypatch.setattr(MainWindow, "_setup_ui", _minimal_setup_ui)


def test_default_case_manager_home_quits_when_dialog_closed(qapp, monkeypatch):
    _patch_main_window_bootstrap(monkeypatch)

    captured = {}

    class DummyCaseManagerDialog:
        def __init__(self, parent=None):
            self.parent = parent

        def exec(self):
            captured["executed"] = True

    monkeypatch.setattr("src.gui.case_manager_dialog.CaseManagerDialog", DummyCaseManagerDialog)
    monkeypatch.setattr(qapp, "quit", lambda: captured.update({"quit_called": True}))

    window = MainWindow()
    window.hide()

    window.open_default_case_manager_home()
    qapp.processEvents()

    assert captured.get("executed") is True
    assert captured.get("quit_called") is True
    assert not window.isVisible()


def test_default_case_manager_home_shows_generation_page_when_new_case_selected(qapp, monkeypatch):
    _patch_main_window_bootstrap(monkeypatch)

    captured = {}

    class DummyCaseManagerDialog:
        def __init__(self, parent=None):
            self.parent = parent

        def exec(self):
            captured["executed"] = True
            if self.parent is not None:
                self.parent.show()

    monkeypatch.setattr("src.gui.case_manager_dialog.CaseManagerDialog", DummyCaseManagerDialog)
    monkeypatch.setattr(qapp, "quit", lambda: captured.update({"quit_called": True}))

    window = MainWindow()
    window.hide()

    window.open_default_case_manager_home()
    qapp.processEvents()

    assert captured.get("executed") is True
    assert captured.get("quit_called") is not True
    assert window.isVisible()
