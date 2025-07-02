#!/usr/bin/env python3
"""
JobManager - バックグラウンドジョブ管理システム

大量のリクエスト実行を非同期で管理し、進捗状況を追跡します。
"""

import asyncio
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import threading
from dataclasses import dataclass, asdict
import json


class JobStatus(str, Enum):
    """ジョブの状態を表す列挙型"""
    PENDING = "pending"      # 待機中
    RUNNING = "running"      # 実行中
    COMPLETED = "completed"  # 完了
    FAILED = "failed"        # 失敗
    CANCELLED = "cancelled"  # キャンセル


@dataclass
class JobProgress:
    """ジョブの進捗状況"""
    total_requests: int = 0
    completed_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    current_request: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    estimated_remaining_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = asdict(self)
        if self.start_time:
            result['start_time'] = self.start_time.isoformat()
        if self.end_time:
            result['end_time'] = self.end_time.isoformat()
        
        # 計算プロパティを追加
        result['progress_percentage'] = self.progress_percentage
        result['elapsed_time'] = self.elapsed_time
        
        return result

    @property
    def progress_percentage(self) -> float:
        """進捗率（0-100）"""
        if self.total_requests == 0:
            return 0.0
        return (self.completed_requests / self.total_requests) * 100

    @property
    def elapsed_time(self) -> Optional[float]:
        """経過時間（秒）"""
        if not self.start_time:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


@dataclass
class Job:
    """ジョブ情報"""
    id: str
    name: str
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    updated_at: datetime
    request_id: int
    http_config: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status.value,
            'progress': self.progress.to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'request_id': self.request_id,
            'http_config': self.http_config,
            'results': self.results,
            'error_message': self.error_message
        }


class JobManager:
    """バックグラウンドジョブ管理クラス"""
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = None
        self._max_concurrent_jobs = 5
        self._active_jobs = 0
    
    def create_job(self, name: str, request_id: int, total_requests: int, 
                   http_config: Optional[Dict[str, Any]] = None) -> str:
        """新しいジョブを作成"""
        job_id = str(uuid.uuid4())
        now = datetime.now()
        
        progress = JobProgress(
            total_requests=total_requests,
            start_time=now
        )
        
        job = Job(
            id=job_id,
            name=name,
            status=JobStatus.PENDING,
            progress=progress,
            created_at=now,
            updated_at=now,
            request_id=request_id,
            http_config=http_config,
            results=[]
        )
        
        with self._lock:
            self._jobs[job_id] = job
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """ジョブを取得"""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """全てのジョブを取得"""
        with self._lock:
            return list(self._jobs.values())
    
    def update_job_progress(self, job_id: str, completed: int, successful: int, 
                           failed: int, current: int = None) -> bool:
        """ジョブの進捗を更新"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            job.progress.completed_requests = completed
            job.progress.successful_requests = successful
            job.progress.failed_requests = failed
            if current is not None:
                job.progress.current_request = current
            
            # 残り時間の推定
            if job.progress.completed_requests > 0 and job.progress.start_time:
                elapsed = (datetime.now() - job.progress.start_time).total_seconds()
                rate = job.progress.completed_requests / elapsed
                remaining = job.progress.total_requests - job.progress.completed_requests
                if rate > 0:
                    job.progress.estimated_remaining_time = remaining / rate
            
            job.updated_at = datetime.now()
            return True
    
    def complete_job(self, job_id: str, results: List[Dict[str, Any]], 
                     error_message: Optional[str] = None) -> bool:
        """ジョブを完了"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            job.status = JobStatus.FAILED if error_message else JobStatus.COMPLETED
            job.progress.end_time = datetime.now()
            job.results = results
            job.error_message = error_message
            job.updated_at = datetime.now()
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            job.status = JobStatus.CANCELLED
            job.progress.end_time = datetime.now()
            job.updated_at = datetime.now()
            return True
    
    def delete_job(self, job_id: str) -> bool:
        """ジョブを削除"""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """古いジョブを削除"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        deleted_count = 0
        
        with self._lock:
            job_ids_to_delete = []
            for job_id, job in self._jobs.items():
                if job.created_at.timestamp() < cutoff_time:
                    job_ids_to_delete.append(job_id)
            
            for job_id in job_ids_to_delete:
                del self._jobs[job_id]
                deleted_count += 1
        
        return deleted_count
    
    async def execute_requests_job(self, job_id: str, requests: List[Dict[str, Any]], 
                                   http_config: Optional[Dict[str, Any]] = None) -> None:
        """リクエスト実行ジョブを実行"""
        job = self.get_job(job_id)
        if not job:
            return
        
        # ジョブを実行中に設定
        with self._lock:
            job.status = JobStatus.RUNNING
            job.updated_at = datetime.now()
        
        try:
            # HTTPRequestConfigを作成
            from http_client import HTTPRequestConfig, RequestExecutor
            
            config = HTTPRequestConfig()
            if http_config:
                config.scheme = http_config.get('scheme', 'http')
                config.base_url = http_config.get('base_url', 'localhost:8000')
                config.timeout = http_config.get('timeout', 30)
                config.follow_redirects = http_config.get('follow_redirects', True)
                config.verify_ssl = http_config.get('verify_ssl', True)
                config.headers = http_config.get('additional_headers')
            
            # リクエストを実行
            results = await RequestExecutor.execute_requests(requests, config)
            
            # 成功・失敗をカウント
            successful = sum(1 for r in results if not r.get('http_response', {}).get('error'))
            failed = len(results) - successful
            
            # 進捗を更新
            self.update_job_progress(job_id, len(results), successful, failed)
            
            # ジョブ完了
            self.complete_job(job_id, results)
            
        except Exception as e:
            # エラーでジョブ終了
            self.complete_job(job_id, [], str(e))
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """ジョブ統計情報を取得"""
        with self._lock:
            total_jobs = len(self._jobs)
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = 0
            
            for job in self._jobs.values():
                status_counts[job.status.value] += 1
            
            return {
                'total_jobs': total_jobs,
                'status_distribution': status_counts,
                'active_jobs': self._active_jobs
            }


# グローバルインスタンス
job_manager = JobManager() 