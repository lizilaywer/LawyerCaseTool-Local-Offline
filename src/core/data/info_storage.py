# -*- coding: utf-8 -*-
"""信息存储管理模块"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

from src.config.path_manager import get_path_manager
from src.config.config_manager import safe_write_json
from src.core.ocr.document_parser import RecognitionResult
from src.utils.logger import get_logger


@dataclass
class ExtractionRecord:
    """提取记录"""
    id: str
    created_at: datetime
    case_id: Optional[str] = None
    case_name: Optional[str] = None
    results: List[RecognitionResult] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'case_id': self.case_id,
            'case_name': self.case_name,
            'results': [r.to_dict() for r in self.results],
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionRecord':
        """从字典创建"""
        return cls(
            id=data['id'],
            created_at=datetime.fromisoformat(data['created_at']),
            case_id=data.get('case_id'),
            case_name=data.get('case_name'),
            results=[RecognitionResult.from_dict(r) for r in data.get('results', [])],
            notes=data.get('notes', '')
        )


class InfoStorage:
    """信息存储管理器"""
    
    def __init__(self):
        self._logger = get_logger()
        self._path_manager = get_path_manager()
        
        # 存储目录
        self._storage_dir = self._path_manager.app_data_dir / 'extracted_info'
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存目录
        self._cache_dir = self._path_manager.app_data_dir / 'ocr_cache'
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._logger.info(f"信息存储目录: {self._storage_dir}")
    
    def save_record(self, record: ExtractionRecord) -> bool:
        """
        保存识别记录
        
        Args:
            record: 提取记录
            
        Returns:
            是否成功
        """
        try:
            # 按日期分目录存储
            date_dir = self._storage_dir / record.created_at.strftime('%Y-%m')
            date_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = date_dir / f"{record.id}.json"
            
            safe_write_json(file_path, record.to_dict(), indent=2)
            
            self._logger.info(f"保存识别记录: {file_path}")
            return True
            
        except Exception as e:
            self._logger.error(f"保存识别记录失败: {e}")
            return False
    
    def get_record(self, record_id: str) -> Optional[ExtractionRecord]:
        """
        获取单个记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            ExtractionRecord 或 None
        """
        # 遍历所有日期目录查找
        for date_dir in self._storage_dir.iterdir():
            if date_dir.is_dir():
                file_path = date_dir / f"{record_id}.json"
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        return ExtractionRecord.from_dict(data)
                    except Exception as e:
                        self._logger.error(f"读取记录失败: {e}")
        
        return None
    
    def get_all_records(self, limit: int = 100) -> List[ExtractionRecord]:
        """
        获取所有记录
        
        Args:
            limit: 最大返回数量
            
        Returns:
            ExtractionRecord 列表，按时间倒序
        """
        records = []
        
        # 遍历所有日期目录
        for date_dir in sorted(self._storage_dir.iterdir(), reverse=True):
            if not date_dir.is_dir():
                continue
            
            for file_path in sorted(date_dir.glob('*.json'), reverse=True):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    records.append(ExtractionRecord.from_dict(data))
                    
                    if len(records) >= limit:
                        break
                        
                except Exception as e:
                    self._logger.error(f"读取记录失败 {file_path}: {e}")
            
            if len(records) >= limit:
                break
        
        return records
    
    def delete_record(self, record_id: str) -> bool:
        """
        删除记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            是否成功
        """
        for date_dir in self._storage_dir.iterdir():
            if date_dir.is_dir():
                file_path = date_dir / f"{record_id}.json"
                if file_path.exists():
                    try:
                        file_path.unlink()
                        self._logger.info(f"删除记录: {file_path}")
                        return True
                    except Exception as e:
                        self._logger.error(f"删除记录失败: {e}")
                        return False
        
        return False
    
    def clean_old_records(self, days: int = 30) -> int:
        """
        清理过期记录
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for date_dir in self._storage_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            for file_path in date_dir.glob('*.json'):
                try:
                    # 读取记录检查日期
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    record_date = datetime.fromisoformat(data['created_at'])
                    
                    if record_date < cutoff_date:
                        file_path.unlink()
                        cleaned_count += 1
                        
                except Exception as e:
                    self._logger.error(f"清理记录失败 {file_path}: {e}")
        
        self._logger.info(f"清理了 {cleaned_count} 条过期记录")
        return cleaned_count
    
    def get_storage_size(self) -> Dict[str, int]:
        """
        获取存储空间使用情况
        
        Returns:
            {'records': 记录大小(bytes), 'cache': 缓存大小(bytes)}
        """
        def get_dir_size(path: Path) -> int:
            total = 0
            if path.exists():
                for entry in path.rglob('*'):
                    if entry.is_file():
                        total += entry.stat().st_size
            return total
        
        return {
            'records': get_dir_size(self._storage_dir),
            'cache': get_dir_size(self._cache_dir)
        }
    
    def clear_cache(self) -> bool:
        """
        清空缓存
        
        Returns:
            是否成功
        """
        try:
            if self._cache_dir.exists():
                shutil.rmtree(self._cache_dir)
                self._cache_dir.mkdir(parents=True, exist_ok=True)
            
            self._logger.info("已清空 OCR 缓存")
            return True
            
        except Exception as e:
            self._logger.error(f"清空缓存失败: {e}")
            return False
    
    def search_records(self, keyword: str) -> List[ExtractionRecord]:
        """
        搜索记录
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的 ExtractionRecord 列表
        """
        results = []
        
        for record in self.get_all_records(limit=1000):
            # 搜索案件名称
            if record.case_name and keyword in record.case_name:
                results.append(record)
                continue
            
            # 搜索识别结果中的字段值
            for res in record.results:
                for field_conf in res.fields.values():
                    if keyword in field_conf.value:
                        results.append(record)
                        break
                else:
                    continue
                break
        
        return results
