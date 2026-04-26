# -*- coding: utf-8 -*-
"""本地非加密备份与迁移服务。"""

import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.config.config_manager import safe_write_json
from src.config.path_manager import get_path_manager
from src.utils.logger import get_logger
from src.utils.version import get_version


BACKUP_EXTENSION = ".lexora-backup"
MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class BackupResult:
    """备份/导入操作结果。"""

    output_path: str
    files_written: int
    bytes_written: int
    snapshot_path: str = ""
    message: str = ""


def _safe_arcname(arcname: str) -> PurePosixPath:
    path = PurePosixPath(arcname)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"非法备份路径: {arcname}")
    return path


def _iter_regular_files(root: Path) -> Iterable[Path]:
    for item in root.rglob("*"):
        if item.is_symlink() or not item.is_file():
            continue
        yield item


class BackupService:
    """创建与导入本地迁移备份。"""

    def __init__(
        self,
        *,
        app_data_dir: Optional[Path] = None,
        config_dir: Optional[Path] = None,
        templates_dir: Optional[Path] = None,
    ):
        path_manager = get_path_manager()
        self._app_data_dir = Path(app_data_dir) if app_data_dir else path_manager.app_data_dir
        self._config_dir = Path(config_dir) if config_dir else path_manager.config_dir
        self._templates_dir = Path(templates_dir) if templates_dir else path_manager.templates_dir
        self._logger = get_logger()

    def create_backup(
        self,
        output_path: Path,
        *,
        cases: Optional[Iterable[Dict[str, Any]]] = None,
        include_case_files: bool = False,
    ) -> BackupResult:
        """创建本地备份包。"""
        output_path = Path(output_path)
        if output_path.suffix != BACKUP_EXTENSION:
            output_path = output_path.with_suffix(BACKUP_EXTENSION)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        case_list = list(cases or [])
        manifest = {
            "format": "lexora-local-backup",
            "format_version": 1,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "app_version": get_version(),
            "include_case_files": include_case_files,
            "case_count": len(case_list),
            "entries": [],
        }

        files_written = 0
        bytes_written = 0
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, arcname in self._collect_config_files():
                written = self._write_file(archive, path, arcname, manifest)
                files_written += 1
                bytes_written += written

            for path, arcname in self._collect_template_files():
                written = self._write_file(archive, path, arcname, manifest)
                files_written += 1
                bytes_written += written

            if include_case_files:
                for path, arcname in self._collect_case_files(case_list):
                    written = self._write_file(archive, path, arcname, manifest)
                    files_written += 1
                    bytes_written += written
            else:
                for path, arcname in self._collect_case_sidecars(case_list):
                    written = self._write_file(archive, path, arcname, manifest)
                    files_written += 1
                    bytes_written += written

            archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))

        return BackupResult(
            output_path=str(output_path),
            files_written=files_written,
            bytes_written=bytes_written,
            message="备份创建完成",
        )

    def import_backup(
        self,
        backup_path: Path,
        *,
        restore_case_files: bool = False,
        case_files_target: Optional[Path] = None,
    ) -> BackupResult:
        """导入备份包。

        配置与台账会恢复到当前应用数据目录；如选择恢复案件文件，
        文件会解压到用户指定目录，并更新 cases.json 中对应案件路径。
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        if restore_case_files and not case_files_target:
            raise ValueError("恢复案件文件时必须指定目标目录")

        snapshot_path = self._create_config_snapshot()
        files_written = 0
        bytes_written = 0
        restored_case_paths: Dict[str, str] = {}

        try:
            with zipfile.ZipFile(backup_path, "r") as archive:
                self._read_manifest(archive)
                for info in archive.infolist():
                    if info.is_dir() or info.filename == MANIFEST_NAME:
                        continue
                    arcpath = _safe_arcname(info.filename)
                    top = arcpath.parts[0]
                    if top == "config":
                        target = self._config_dir.joinpath(*arcpath.parts[1:])
                    elif top == "templates":
                        target = self._templates_dir.joinpath(*arcpath.parts[1:])
                    elif top == "case_files" and restore_case_files and case_files_target:
                        target, case_id, root_folder = self._case_file_target(
                            arcpath,
                            Path(case_files_target),
                        )
                        if case_id and root_folder:
                            restored_case_paths[case_id] = str(Path(case_files_target) / root_folder)
                    elif top == "case_sidecars":
                        continue
                    else:
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info, "r") as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                    files_written += 1
                    bytes_written += int(info.file_size)

            if restored_case_paths:
                self._rewrite_restored_case_paths(restored_case_paths)
        except Exception:
            self._logger.error("导入备份失败，已保留导入前配置快照")
            raise

        return BackupResult(
            output_path=str(backup_path),
            files_written=files_written,
            bytes_written=bytes_written,
            snapshot_path=str(snapshot_path),
            message="备份导入完成",
        )

    def _collect_config_files(self) -> Iterable[Tuple[Path, str]]:
        if not self._config_dir.exists():
            return []
        return [
            (path, f"config/{path.relative_to(self._config_dir).as_posix()}")
            for path in _iter_regular_files(self._config_dir)
        ]

    def _collect_template_files(self) -> Iterable[Tuple[Path, str]]:
        if not self._templates_dir.exists():
            return []
        return [
            (path, f"templates/{path.relative_to(self._templates_dir).as_posix()}")
            for path in _iter_regular_files(self._templates_dir)
        ]

    def _collect_case_sidecars(self, cases: Iterable[Dict[str, Any]]) -> Iterable[Tuple[Path, str]]:
        result: List[Tuple[Path, str]] = []
        for case in cases:
            case_id = str(case.get("id", "")).strip()
            root = Path(str(case.get("path", "")).strip())
            sidecar = root / ".case"
            if not case_id or not sidecar.exists():
                continue
            for path in _iter_regular_files(sidecar):
                rel = path.relative_to(sidecar).as_posix()
                result.append((path, f"case_sidecars/{case_id}/{rel}"))
        return result

    def _collect_case_files(self, cases: Iterable[Dict[str, Any]]) -> Iterable[Tuple[Path, str]]:
        result: List[Tuple[Path, str]] = []
        for case in cases:
            case_id = str(case.get("id", "")).strip()
            root = Path(str(case.get("path", "")).strip())
            if not case_id or not root.exists() or not root.is_dir():
                continue
            for path in _iter_regular_files(root):
                rel = path.relative_to(root).as_posix()
                result.append((path, f"case_files/{case_id}/{root.name}/{rel}"))
        return result

    def _write_file(
        self,
        archive: zipfile.ZipFile,
        path: Path,
        arcname: str,
        manifest: Dict[str, Any],
    ) -> int:
        _safe_arcname(arcname)
        size = path.stat().st_size
        archive.write(path, arcname)
        manifest["entries"].append({"path": arcname, "size": size})
        return int(size)

    def _read_manifest(self, archive: zipfile.ZipFile) -> Dict[str, Any]:
        try:
            raw = archive.read(MANIFEST_NAME).decode("utf-8")
        except KeyError as exc:
            raise ValueError("备份包缺少 manifest.json") from exc
        data = json.loads(raw)
        if data.get("format") != "lexora-local-backup":
            raise ValueError("不是有效的 LEXORA 本地备份包")
        return data

    def _create_config_snapshot(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = self._app_data_dir / "import_snapshots" / f"before_import_{timestamp}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        if self._config_dir.exists():
            target = snapshot_dir / "config"
            shutil.copytree(self._config_dir, target, dirs_exist_ok=True)
        return snapshot_dir

    def _case_file_target(
        self,
        arcpath: PurePosixPath,
        case_files_target: Path,
    ) -> Tuple[Path, str, str]:
        if len(arcpath.parts) < 4:
            raise ValueError(f"非法案件文件路径: {arcpath}")
        _, case_id, root_folder, *relative_parts = arcpath.parts
        target = case_files_target / root_folder
        if relative_parts:
            target = target.joinpath(*relative_parts)
        return target, case_id, root_folder

    def _rewrite_restored_case_paths(self, restored_case_paths: Dict[str, str]) -> None:
        cases_file = self._config_dir / "cases.json"
        if not cases_file.exists():
            return

        data = json.loads(cases_file.read_text(encoding="utf-8"))
        cases = data.get("cases", {})
        if not isinstance(cases, dict):
            return

        changed = False
        for case_id, restored_path in restored_case_paths.items():
            case = cases.get(case_id)
            if not isinstance(case, dict):
                continue
            old_path = str(case.get("path", "")).strip()
            case["path"] = restored_path
            history = list(case.get("path_history", []) or [])
            for value in (old_path, restored_path):
                if value and value not in history:
                    history.append(value)
            case["path_history"] = history
            changed = True

        if changed:
            safe_write_json(cases_file, data)
