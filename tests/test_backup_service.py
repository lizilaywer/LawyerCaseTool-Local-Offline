# -*- coding: utf-8 -*-
"""本地备份与迁移服务测试。"""

import json
import zipfile
from pathlib import Path

from src.core.backup import BackupService


def test_create_backup_includes_config_templates_and_sidecar(tmp_path: Path):
    app_data = tmp_path / "app"
    config_dir = app_data / "config"
    templates_dir = tmp_path / "templates"
    case_root = tmp_path / "案件"
    (case_root / ".case").mkdir(parents=True)
    config_dir.mkdir(parents=True)
    templates_dir.mkdir()

    (config_dir / "config.json").write_text("{}", encoding="utf-8")
    (config_dir / "cases.json").write_text(
        json.dumps({"cases": {"case_1": {"path": str(case_root)}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (templates_dir / "template.docx").write_text("template", encoding="utf-8")
    (case_root / ".case" / "metadata.json").write_text("{}", encoding="utf-8")
    (case_root / "证据.pdf").write_text("pdf", encoding="utf-8")

    service = BackupService(
        app_data_dir=app_data,
        config_dir=config_dir,
        templates_dir=templates_dir,
    )
    backup_path = tmp_path / "backup.lexora-backup"
    result = service.create_backup(
        backup_path,
        cases=[{"id": "case_1", "name": "案件", "path": str(case_root)}],
        include_case_files=False,
    )

    assert Path(result.output_path).exists()
    with zipfile.ZipFile(result.output_path) as archive:
        names = set(archive.namelist())

    assert "config/config.json" in names
    assert "config/cases.json" in names
    assert "templates/template.docx" in names
    assert "case_sidecars/case_1/metadata.json" in names
    assert "case_files/case_1/案件/证据.pdf" not in names


def test_import_backup_restores_case_files_and_rewrites_paths(tmp_path: Path):
    source_app = tmp_path / "source_app"
    source_config = source_app / "config"
    source_templates = tmp_path / "source_templates"
    case_root = tmp_path / "原案件"
    source_config.mkdir(parents=True)
    source_templates.mkdir()
    case_root.mkdir()

    cases_payload = {
        "version": 2,
        "cases": {
            "case_1": {
                "id": "case_1",
                "name": "原案件",
                "path": str(case_root),
                "path_history": [str(case_root)],
            }
        },
    }
    (source_config / "cases.json").write_text(
        json.dumps(cases_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (source_templates / "template.docx").write_text("template", encoding="utf-8")
    (case_root / "证据.pdf").write_text("pdf", encoding="utf-8")

    backup_path = tmp_path / "backup.lexora-backup"
    BackupService(
        app_data_dir=source_app,
        config_dir=source_config,
        templates_dir=source_templates,
    ).create_backup(
        backup_path,
        cases=[{"id": "case_1", "name": "原案件", "path": str(case_root)}],
        include_case_files=True,
    )

    target_app = tmp_path / "target_app"
    target_config = target_app / "config"
    target_templates = tmp_path / "target_templates"
    restored_cases = tmp_path / "restored_cases"

    result = BackupService(
        app_data_dir=target_app,
        config_dir=target_config,
        templates_dir=target_templates,
    ).import_backup(
        backup_path,
        restore_case_files=True,
        case_files_target=restored_cases,
    )

    assert result.files_written >= 3
    restored_file = restored_cases / "原案件" / "证据.pdf"
    assert restored_file.exists()

    restored_cases_payload = json.loads((target_config / "cases.json").read_text(encoding="utf-8"))
    assert restored_cases_payload["cases"]["case_1"]["path"] == str(restored_cases / "原案件")
