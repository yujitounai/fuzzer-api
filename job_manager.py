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

# データベース関連のインポート
from database import db_manager, Job as DBJob, JobResult as DBJobResult
from sqlalchemy.orm import Session


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
        self._db_session: Optional[Session] = None
        self._job_processor_active = True
        self._running_tasks: Dict[str, Any] = {}  # 実行中のタスクを追跡
        
        # 起動時にデータベースからジョブを復元
        self._restore_jobs_from_database()
        
        # バックグラウンドでジョブを処理するスレッドを開始
        self._start_job_processor()
    
    def _get_db_session(self) -> Session:
        """データベースセッションを取得"""
        if self._db_session is None:
            self._db_session = db_manager.SessionLocal()
        return self._db_session
    
    def _restore_jobs_from_database(self):
        """データベースからジョブを復元"""
        try:
            print("データベースからジョブを復元中...")
            db = self._get_db_session()
            db_jobs = db_manager.get_all_jobs(db)
            
            restored_count = 0
            for db_job in db_jobs:
                try:
                    # データベースのジョブをメモリ内のJobオブジェクトに変換
                    progress_data = db_job.get_progress()
                    # JobProgressの有効なフィールドのみを抽出
                    valid_fields = ['total_requests', 'completed_requests', 'successful_requests', 
                                   'failed_requests', 'current_request', 'start_time', 'end_time', 
                                   'estimated_remaining_time']
                    progress_init_data = {k: v for k, v in progress_data.items() if k in valid_fields}
                    
                    # 日時文字列をdatetimeオブジェクトに変換
                    if 'start_time' in progress_init_data and isinstance(progress_init_data['start_time'], str):
                        progress_init_data['start_time'] = datetime.fromisoformat(progress_init_data['start_time'])
                    if 'end_time' in progress_init_data and isinstance(progress_init_data['end_time'], str):
                        progress_init_data['end_time'] = datetime.fromisoformat(progress_init_data['end_time'])
                        
                    progress = JobProgress(**progress_init_data)
                    
                    job = Job(
                        id=db_job.id,
                        name=db_job.name,
                        status=JobStatus(db_job.status),
                        progress=progress,
                        created_at=db_job.created_at,
                        updated_at=db_job.updated_at,
                        request_id=db_job.fuzzer_request_id,
                        http_config=db_job.http_config,
                        results=[],
                        error_message=db_job.error_message
                    )
                    
                    # メモリに復元
                    with self._lock:
                        self._jobs[db_job.id] = job
                    
                    restored_count += 1
                    
                except Exception as e:
                    print(f"ジョブ {db_job.id} の復元に失敗: {e}")
                    
            print(f"データベースから {restored_count} 件のジョブを復元しました")
            
        except Exception as e:
            print(f"ジョブ復元時のエラー: {e}")
    
    def _start_job_processor(self):
        """バックグラウンドジョブ処理スレッドを開始"""
        def job_processor():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while self._job_processor_active:
                try:
                    # PENDING状態のジョブを探す
                    pending_jobs = []
                    with self._lock:
                        for job in self._jobs.values():
                            if job.status == JobStatus.PENDING:
                                pending_jobs.append(job)
                    
                    if pending_jobs:
                        print(f"バックグラウンド処理: {len(pending_jobs)}件のPENDINGジョブを発見")
                    
                    # PENDING状態のジョブを実行（一つずつ）
                    for job in pending_jobs:
                        if self._active_jobs < self._max_concurrent_jobs:
                            print(f"PENDING ジョブ {job.id} を実行開始 (アクティブ: {self._active_jobs}/{self._max_concurrent_jobs})")
                            loop.run_until_complete(self._execute_pending_job(job.id))
                        else:
                            print(f"同時実行数制限に達しているため、ジョブ {job.id} はスキップ")
                    
                    time.sleep(5)  # 5秒間隔でチェック
                except Exception as e:
                    print(f"ジョブ処理スレッドエラー: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(5)
            
            loop.close()
        
        # デーモンスレッドとして開始
        processor_thread = threading.Thread(target=job_processor, daemon=True)
        processor_thread.start()
        print("バックグラウンドジョブ処理スレッドを開始しました")
    
    async def _execute_pending_job(self, job_id: str):
        """PENDING状態のジョブを実行"""
        self._active_jobs += 1
        try:
            job = self.get_job(job_id)
            if not job or job.status != JobStatus.PENDING:
                print(f"ジョブ {job_id}: 実行対象外 - ステータス: {job.status if job else 'None'}")
                return
            
            print(f"PENDING ジョブ {job_id} の自動実行を開始")
            
            # 元のリクエストデータを取得
            from database import db_manager
            db = self._get_db_session()
            
            try:
                fuzzer_request = db_manager.get_fuzzer_request_by_id(db, job.request_id)
                if not fuzzer_request:
                    print(f"ジョブ {job_id}: リクエストデータが見つかりません (request_id: {job.request_id})")
                    self.complete_job(job_id, [], f"リクエストデータが見つかりません (request_id: {job.request_id})")
                    return
                
                print(f"ジョブ {job_id}: リクエストデータ取得成功")
                
                # 生成されたリクエストを抽出
                requests_data = []
                for gen_req in fuzzer_request.generated_requests:
                    req_dict = {
                        "request": gen_req.request_content,
                        "placeholder": gen_req.placeholder,
                        "payload": gen_req.payload,
                        "position": gen_req.position
                    }
                    
                    # applied_toフィールドがある場合は追加
                    if gen_req.applied_to:
                        req_dict["applied_to"] = gen_req.get_applied_to()
                    
                    requests_data.append(req_dict)
                
                if not requests_data:
                    print(f"ジョブ {job_id}: 生成されたリクエストが空です")
                    self.complete_job(job_id, [], "生成されたリクエストが空です")
                    return
                
                print(f"ジョブ {job_id}: {len(requests_data)}件の生成リクエストを実行開始")
                
                # リクエストを再実行
                await self.execute_requests_job(job_id, requests_data, job.http_config)
                
            except Exception as db_error:
                print(f"ジョブ {job_id}: データベースからのリクエスト取得エラー: {db_error}")
                self.complete_job(job_id, [], f"データベースエラー: {str(db_error)}")
                return
            
        except Exception as e:
            print(f"PENDING ジョブ {job_id} の実行エラー: {e}")
            self.complete_job(job_id, [], str(e))
        finally:
            self._active_jobs -= 1
    
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
        
        # データベースにも保存
        try:
            db = self._get_db_session()
            db_manager.save_job(
                db=db,
                job_id=job_id,
                name=name,
                status=JobStatus.PENDING.value,
                fuzzer_request_id=request_id,
                http_config=http_config,
                progress=progress.to_dict()
            )
        except Exception as e:
            print(f"データベース保存エラー: {e}")
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """ジョブを取得"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                print(f"ジョブ {job_id}: メモリから取得 - 結果数: {len(job.results) if job.results else 0}")
                
                # データベースから実行結果を取得
                try:
                    db = self._get_db_session()
                    results = db_manager.get_job_results(db=db, job_id=job_id)
                    if results:
                        print(f"ジョブ {job_id}: データベースから結果を取得 - 結果数: {len(results)}")
                        job.results = results
                    else:
                        print(f"ジョブ {job_id}: データベースに結果が見つかりません")
                except Exception as e:
                    print(f"データベース取得エラー: {e}")
            else:
                print(f"ジョブ {job_id}: メモリにジョブが見つかりません")
            
            return job
    
    def get_all_jobs(self) -> List[Job]:
        """全てのジョブを取得"""
        with self._lock:
            # メモリ内のジョブを取得
            memory_jobs = list(self._jobs.values())
        
        # データベースからも取得
        try:
            db = self._get_db_session()
            db_jobs = db_manager.get_all_jobs(db)
            
            # データベースのジョブをメモリ内のジョブとマージ
            db_job_ids = {job.id for job in db_jobs}
            memory_job_ids = {job.id for job in memory_jobs}
            
            # データベースにあってメモリにないジョブを復元
            for db_job in db_jobs:
                if db_job.id not in memory_job_ids:
                    # データベースのジョブをメモリ内のJobオブジェクトに変換
                    progress_data = db_job.get_progress()
                    # JobProgressの有効なフィールドのみを抽出
                    valid_fields = ['total_requests', 'completed_requests', 'successful_requests', 
                                   'failed_requests', 'current_request', 'start_time', 'end_time', 
                                   'estimated_remaining_time']
                    progress_init_data = {k: v for k, v in progress_data.items() if k in valid_fields}
                    
                    # 日時文字列をdatetimeオブジェクトに変換
                    if 'start_time' in progress_init_data and isinstance(progress_init_data['start_time'], str):
                        progress_init_data['start_time'] = datetime.fromisoformat(progress_init_data['start_time'])
                    if 'end_time' in progress_init_data and isinstance(progress_init_data['end_time'], str):
                        progress_init_data['end_time'] = datetime.fromisoformat(progress_init_data['end_time'])
                        
                    progress = JobProgress(**progress_init_data)
                    job = Job(
                        id=db_job.id,
                        name=db_job.name,
                        status=JobStatus(db_job.status),
                        progress=progress,
                        created_at=db_job.created_at,
                        updated_at=db_job.updated_at,
                        request_id=db_job.fuzzer_request_id,
                        http_config=db_job.http_config,
                        results=[],
                        error_message=db_job.error_message
                    )
                    memory_jobs.append(job)
            
            # メモリにあってデータベースにないジョブをデータベースに保存
            for memory_job in memory_jobs:
                if memory_job.id not in db_job_ids:
                    try:
                        db_manager.save_job(
                            db=db,
                            job_id=memory_job.id,
                            name=memory_job.name,
                            status=memory_job.status.value,
                            fuzzer_request_id=memory_job.request_id,
                            http_config=memory_job.http_config,
                            progress=memory_job.progress.to_dict(),
                            error_message=memory_job.error_message
                        )
                    except Exception as e:
                        print(f"データベース保存エラー: {e}")
                        
        except Exception as e:
            print(f"データベース取得エラー: {e}")
        
        return memory_jobs
    
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
        
        # データベースも更新
        try:
            db = self._get_db_session()
            db_manager.update_job(
                db=db,
                job_id=job_id,
                progress=job.progress.to_dict()
            )
        except Exception as e:
            print(f"データベース更新エラー: {e}")
        
        return True
    
    def complete_job(self, job_id: str, results: List[Dict[str, Any]], 
                     error_message: Optional[str] = None) -> bool:
        """ジョブを完了"""
        print(f"ジョブ {job_id}: complete_job呼び出し - 結果数: {len(results) if results else 0}")
        
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                print(f"ジョブ {job_id}: ジョブが見つかりません")
                return False
            
            job.status = JobStatus.FAILED if error_message else JobStatus.COMPLETED
            job.progress.end_time = datetime.now()
            job.results = results
            job.error_message = error_message
            job.updated_at = datetime.now()
            
            print(f"ジョブ {job_id}: メモリに結果を保存 - 結果数: {len(results) if results else 0}")
        
        # データベースも更新
        try:
            db = self._get_db_session()
            db_manager.update_job(
                db=db,
                job_id=job_id,
                status=job.status.value,
                progress=job.progress.to_dict(),
                error_message=error_message
            )
            
            # 実行結果も保存
            if results:
                print(f"ジョブ {job_id}: データベースに結果を保存 - 結果数: {len(results)}")
                db_manager.save_job_results(db=db, job_id=job_id, results=results)
            else:
                print(f"ジョブ {job_id}: 結果が空のためデータベース保存をスキップ")
                
        except Exception as e:
            print(f"データベース更新エラー: {e}")
        
        return True
    
    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            # 実行中のタスクをキャンセル
            if job_id in self._running_tasks:
                task = self._running_tasks[job_id]
                if hasattr(task, 'cancel'):
                    print(f"ジョブ {job_id}: 実行中のタスクをキャンセル中...")
                    task.cancel()
                del self._running_tasks[job_id]
            
            job.status = JobStatus.CANCELLED
            job.progress.end_time = datetime.now()
            job.updated_at = datetime.now()
        
        # データベースも更新
        try:
            db = self._get_db_session()
            db_manager.update_job(
                db=db,
                job_id=job_id,
                status=JobStatus.CANCELLED.value,
                progress=job.progress.to_dict()
            )
        except Exception as e:
            print(f"ジョブキャンセル時のデータベース更新エラー: {e}")
            
        return True
    
    def resume_job(self, job_id: str) -> bool:
        """ジョブを再開"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                print(f"ジョブ再開エラー: ジョブ {job_id} が見つかりません")
                return False
            
            # キャンセルまたは失敗状態のジョブのみ再開可能
            if job.status not in [JobStatus.CANCELLED, JobStatus.FAILED]:
                print(f"ジョブ再開エラー: ジョブ {job_id} は再開できない状態です (現在: {job.status})")
                return False
            
            print(f"ジョブ {job_id} を再開: {job.status} -> PENDING")
            
            # ジョブを待機状態にリセット
            job.status = JobStatus.PENDING
            job.progress.end_time = None
            job.error_message = None
            job.updated_at = datetime.now()
            
            # 部分実行されたリクエストがある場合、継続から再開するのではなく、最初から再実行
            # 簡素化のため、一度完全にリセット
            # job.progress.completed_requests = 0
            # job.progress.successful_requests = 0 
            # job.progress.failed_requests = 0
            # job.progress.current_request = 0
            job.results = []  # 結果もクリア
        
        # データベースも更新
        try:
            db = self._get_db_session()
            db_manager.update_job(
                db=db,
                job_id=job_id,
                status=JobStatus.PENDING.value,
                progress=job.progress.to_dict(),
                error_message=None
            )
            print(f"ジョブ {job_id}: データベース更新完了")
        except Exception as e:
            print(f"ジョブ再開時のデータベース更新エラー: {e}")
            return False
            
        print(f"ジョブ {job_id}: 再開準備完了、バックグラウンド処理待ち")
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
                config.sequential_execution = http_config.get('sequential_execution', False)
                config.request_delay = http_config.get('request_delay', 0.0)
            
            print(f"ジョブ {job_id}: リクエスト実行開始 - {len(requests)}件のリクエスト")
            
            # リクエストを実行（キャンセル可能なタスクとして）
            task = asyncio.create_task(
                self._execute_requests_with_cancellation(job_id, requests, config)
            )
            
            # 実行中のタスクを記録
            with self._lock:
                self._running_tasks[job_id] = task
            
            # タスクを実行
            results = await task
            
            print(f"ジョブ {job_id}: リクエスト実行完了 - 結果数: {len(results)}")
            print(f"ジョブ {job_id}: 結果の詳細: {results[:2]}...")  # 最初の2件を表示
            
            # 成功・失敗をカウント
            successful = sum(1 for r in results if not r.get('http_response', {}).get('error'))
            failed = len(results) - successful
            
            print(f"ジョブ {job_id}: 成功={successful}, 失敗={failed}")
            
            # 進捗を更新
            self.update_job_progress(job_id, len(results), successful, failed)
            
            # ジョブ完了
            self.complete_job(job_id, results)
            
        except asyncio.CancelledError:
            print(f"ジョブ {job_id}: キャンセルされました")
            # ジョブはすでにキャンセル状態になっているはず
        except Exception as e:
            print(f"ジョブ {job_id}: エラー発生 - {e}")
            # エラーでジョブ終了
            self.complete_job(job_id, [], str(e))
        finally:
            # 実行中のタスクから削除
            with self._lock:
                if job_id in self._running_tasks:
                    del self._running_tasks[job_id]
    
    async def _execute_requests_with_cancellation(self, job_id: str, requests: List[Dict[str, Any]], 
                                                  config: 'HTTPRequestConfig') -> List[Dict[str, Any]]:
        """キャンセル対応のリクエスト実行"""
        from http_client import RequestExecutor
        
        # 定期的にキャンセル状態をチェックしながら実行
        if config.sequential_execution:
            # 同期実行の場合は一つずつ実行し、キャンセルチェックを行う
            return await self._execute_requests_sequential_with_cancel(job_id, requests, config)
        else:
            # 並列実行の場合
            return await RequestExecutor.execute_requests(requests, config)
    
    async def _execute_requests_sequential_with_cancel(self, job_id: str, requests: List[Dict[str, Any]], 
                                                       config: 'HTTPRequestConfig') -> List[Dict[str, Any]]:
        """キャンセル対応の同期実行"""
        from http_client import HTTPClient
        
        results = []
        
        async with HTTPClient() as client:
            for i, request in enumerate(requests):
                # キャンセル状態をチェック
                job = self.get_job(job_id)
                if job and job.status == JobStatus.CANCELLED:
                    print(f"ジョブ {job_id}: リクエスト {i+1} でキャンセル検出、実行を停止")
                    break
                
                print(f"同期実行: リクエスト {i+1}/{len(requests)} を送信中...")
                try:
                    response = await client.send_request(request["request"], config)
                    result = {
                        "request": request.get("request", ""),
                        "placeholder": request.get("placeholder", ""),
                        "payload": request.get("payload", ""),
                        "position": request.get("position", 0),
                        "http_response": {
                            "status_code": response.status_code,
                            "headers": response.headers,
                            "body": response.body,
                            "url": response.url,
                            "elapsed_time": response.elapsed_time,
                            "error": response.error,
                            "actual_request": response.actual_request
                        }
                    }
                    results.append(result)
                    print(f"同期実行: リクエスト {i+1} 完了 - ステータス: {response.status_code}")
                    
                    # 進捗を更新
                    self.update_job_progress(job_id, i+1, len([r for r in results if not r.get('http_response', {}).get('error')]), 
                                           len([r for r in results if r.get('http_response', {}).get('error')]), i+1)
                    
                    # リクエスト間の待機時間（最後のリクエスト以外）
                    if i < len(requests) - 1 and config.request_delay > 0:
                        print(f"同期実行: {config.request_delay}秒待機中...")
                        
                        # 待機中もキャンセルチェック（1秒刻みで）
                        wait_time = config.request_delay
                        while wait_time > 0:
                            sleep_duration = min(1.0, wait_time)
                            await asyncio.sleep(sleep_duration)
                            wait_time -= sleep_duration
                            
                            # キャンセルチェック
                            job = self.get_job(job_id)
                            if job and job.status == JobStatus.CANCELLED:
                                print(f"ジョブ {job_id}: 待機中にキャンセル検出、実行を停止")
                                return results
                        
                except Exception as e:
                    print(f"同期実行: リクエスト {i+1} エラー - {str(e)}")
                    result = {
                        "request": request.get("request", ""),
                        "placeholder": request.get("placeholder", ""),
                        "payload": request.get("payload", ""),
                        "position": request.get("position", 0),
                        "http_response": {
                            "status_code": 0,
                            "headers": {},
                            "body": "",
                            "url": "",
                            "elapsed_time": 0,
                            "error": str(e)
                        }
                    }
                    results.append(result)
                    
                    # 進捗を更新
                    self.update_job_progress(job_id, i+1, len([r for r in results if not r.get('http_response', {}).get('error')]), 
                                           len([r for r in results if r.get('http_response', {}).get('error')]), i+1)
                    
                    # エラーが発生してもウェイトを入れる（オプション）
                    if i < len(requests) - 1 and config.request_delay > 0:
                        await asyncio.sleep(config.request_delay)
                        
        return results
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """ジョブ統計情報を取得"""
        with self._lock:
            total_jobs = len(self._jobs)
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = 0
            
            for job in self._jobs.values():
                status_counts[job.status.value] += 1
        
        # データベースからも統計情報を取得
        try:
            db = self._get_db_session()
            db_stats = db_manager.get_job_statistics(db)
            
            # データベースの統計情報を優先
            return {
                'total_jobs': db_stats['total_jobs'],
                'status_distribution': {
                    'pending': db_stats.get('pending_jobs', 0),
                    'running': db_stats.get('running_jobs', 0),
                    'completed': db_stats.get('completed_jobs', 0),
                    'failed': db_stats.get('failed_jobs', 0),
                    'cancelled': 0  # データベース統計に含まれていない場合
                },
                'active_jobs': self._active_jobs,
                'total_requests': db_stats.get('total_requests', 0),
                'avg_execution_time': db_stats.get('avg_execution_time', 0)
            }
        except Exception as e:
            print(f"データベース統計取得エラー: {e}")
            # エラーが発生した場合はメモリ内の統計情報を返す
            return {
                'total_jobs': total_jobs,
                'status_distribution': status_counts,
                'active_jobs': self._active_jobs,
                'total_requests': 0,
                'avg_execution_time': 0
            }


# グローバルインスタンス
job_manager = JobManager() 