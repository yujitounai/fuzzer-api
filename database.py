"""
データベースモデルとセッション管理

このモジュールは、リクエストと生成されたリクエストを永続化するための
SQLAlchemyデータベースモデルとセッション管理機能を提供します。
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional
import json

# データベースURL（SQLiteを使用）
DATABASE_URL = "sqlite:///./fuzzer_requests.db"

# SQLAlchemyエンジンの作成
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # SQLite用の設定
)

# セッションクラスの作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラスの作成
Base = declarative_base()

class FuzzerRequest(Base):
    """
    ファザーリクエストのメインテーブル
    
    このテーブルは、ユーザーが送信したリクエストの基本情報を保存します。
    各リクエストは複数の生成されたリクエストを持つことができます。
    """
    __tablename__ = "fuzzer_requests"
    
    id = Column(Integer, primary_key=True, index=True, comment="リクエストの一意識別子")
    template = Column(Text, nullable=False, comment="プレースホルダを含むテンプレート文字列")
    placeholders = Column(Text, nullable=False, comment="プレースホルダ名のリスト（JSON形式）")
    strategy = Column(String(50), nullable=False, comment="攻撃戦略（sniper, battering_ram, pitchfork, cluster_bomb）")
    payload_sets = Column(Text, nullable=False, comment="ペイロードセットのリスト（JSON形式）")
    total_requests = Column(Integer, nullable=False, comment="生成されたリクエストの総数")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="リクエスト作成日時")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最終更新日時")
    
    # リレーションシップ: このリクエストから生成されたリクエストのリスト
    generated_requests = relationship("GeneratedRequest", back_populates="fuzzer_request", cascade="all, delete-orphan")
    
    def set_placeholders(self, placeholders: List[str]):
        """プレースホルダリストをJSON形式で保存"""
        self.placeholders = json.dumps(placeholders, ensure_ascii=False)
    
    def get_placeholders(self) -> List[str]:
        """保存されたプレースホルダリストを取得"""
        return json.loads(self.placeholders) if self.placeholders else []
    
    def set_payload_sets(self, payload_sets: List[dict]):
        """ペイロードセットをJSON形式で保存"""
        self.payload_sets = json.dumps(payload_sets, ensure_ascii=False)
    
    def get_payload_sets(self) -> List[dict]:
        """保存されたペイロードセットを取得"""
        return json.loads(self.payload_sets) if self.payload_sets else []

class GeneratedRequest(Base):
    """
    生成されたリクエストのテーブル
    
    このテーブルは、ファザーエンジンによって生成された各リクエストの詳細を保存します。
    各生成されたリクエストは、元のファザーリクエストに関連付けられます。
    """
    __tablename__ = "generated_requests"
    
    id = Column(Integer, primary_key=True, index=True, comment="生成されたリクエストの一意識別子")
    fuzzer_request_id = Column(Integer, ForeignKey("fuzzer_requests.id"), nullable=False, comment="元のファザーリクエストのID")
    request_number = Column(Integer, nullable=False, comment="リクエスト番号（順序）")
    request_content = Column(Text, nullable=False, comment="生成されたリクエストの内容")
    placeholder = Column(String(255), nullable=True, comment="使用されたプレースホルダ名")
    payload = Column(Text, nullable=True, comment="使用されたペイロード")
    position = Column(Integer, nullable=True, comment="プレースホルダの位置（Sniper攻撃用）")
    applied_to = Column(Text, nullable=True, comment="適用されたプレースホルダのリスト（JSON形式）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="生成日時")
    
    # リレーションシップ: 元のファザーリクエスト
    fuzzer_request = relationship("FuzzerRequest", back_populates="generated_requests")
    
    def set_applied_to(self, applied_to: List[str]):
        """適用されたプレースホルダリストをJSON形式で保存"""
        self.applied_to = json.dumps(applied_to, ensure_ascii=False) if applied_to else None
    
    def get_applied_to(self) -> List[str]:
        """保存された適用プレースホルダリストを取得"""
        return json.loads(self.applied_to) if self.applied_to else []

class Job(Base):
    """
    ジョブ情報のテーブル
    
    このテーブルは、HTTPリクエスト実行ジョブの基本情報を保存します。
    各ジョブは複数の実行結果を持つことができます。
    """
    __tablename__ = "jobs"
    
    id = Column(String(36), primary_key=True, index=True, comment="ジョブの一意識別子（UUID）")
    name = Column(String(255), nullable=False, comment="ジョブ名")
    status = Column(String(20), nullable=False, comment="ジョブの状態（pending, running, completed, failed, cancelled）")
    fuzzer_request_id = Column(Integer, ForeignKey("fuzzer_requests.id"), nullable=False, comment="関連するファザーリクエストのID")
    http_config = Column(JSON, nullable=True, comment="HTTP設定（JSON形式）")
    progress = Column(JSON, nullable=False, comment="進捗情報（JSON形式）")
    error_message = Column(Text, nullable=True, comment="エラーメッセージ")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最終更新日時")
    
    # リレーションシップ: このジョブの実行結果のリスト
    results = relationship("JobResult", back_populates="job", cascade="all, delete-orphan")
    
    def set_progress(self, progress: dict):
        """進捗情報をJSON形式で保存"""
        self.progress = json.dumps(progress, ensure_ascii=False)
    
    def get_progress(self) -> dict:
        """保存された進捗情報を取得"""
        return json.loads(self.progress) if self.progress else {}

class JobResult(Base):
    """
    ジョブ実行結果のテーブル
    
    このテーブルは、各ジョブの実行結果の詳細を保存します。
    各実行結果は、元のジョブに関連付けられます。
    """
    __tablename__ = "job_results"
    
    id = Column(Integer, primary_key=True, index=True, comment="実行結果の一意識別子")
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, comment="元のジョブのID")
    request_number = Column(Integer, nullable=False, comment="リクエスト番号（順序）")
    request_content = Column(Text, nullable=False, comment="実行したリクエストの内容")
    placeholder = Column(String(255), nullable=True, comment="使用されたプレースホルダ名")
    payload = Column(Text, nullable=True, comment="使用されたペイロード")
    position = Column(Integer, nullable=True, comment="プレースホルダの位置")
    http_response = Column(JSON, nullable=True, comment="HTTPレスポンス（JSON形式）")
    success = Column(Integer, nullable=False, default=0, comment="成功フラグ（0: 失敗, 1: 成功）")
    error_message = Column(Text, nullable=True, comment="エラーメッセージ")
    elapsed_time = Column(Integer, nullable=True, comment="実行時間（ミリ秒）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="実行日時")
    
    # リレーションシップ: 元のジョブ
    job = relationship("Job", back_populates="results")
    
    def set_http_response(self, http_response: dict):
        """HTTPレスポンスをJSON形式で保存"""
        self.http_response = json.dumps(http_response, ensure_ascii=False) if http_response else None
    
    def get_http_response(self) -> dict:
        """保存されたHTTPレスポンスを取得"""
        return json.loads(self.http_response) if self.http_response else {}

class DatabaseManager:
    """
    データベース操作を管理するクラス
    
    このクラスは、ファザーリクエストと生成されたリクエストの
    保存、取得、削除などの操作を提供します。
    """
    
    def __init__(self):
        """データベースマネージャーの初期化"""
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def create_tables(self):
        """データベーステーブルを作成"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_db(self):
        """データベースセッションを取得"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def save_fuzzer_request(self, db, template: str, placeholders: List[str], 
                          strategy: str, payload_sets: List[dict], 
                          generated_requests: List[dict]) -> FuzzerRequest:
        """
        ファザーリクエストと生成されたリクエストを保存
        
        Args:
            db: データベースセッション
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            strategy (str): 攻撃戦略
            payload_sets (List[dict]): ペイロードセットのリスト
            generated_requests (List[dict]): 生成されたリクエストのリスト
            
        Returns:
            FuzzerRequest: 保存されたファザーリクエストオブジェクト
        """
        # ファザーリクエストを作成
        fuzzer_request = FuzzerRequest(
            template=template,
            strategy=strategy,
            total_requests=len(generated_requests)
        )
        fuzzer_request.set_placeholders(placeholders)
        fuzzer_request.set_payload_sets(payload_sets)
        
        # データベースに保存
        db.add(fuzzer_request)
        db.commit()
        db.refresh(fuzzer_request)
        
        # 生成されたリクエストを保存
        for i, req in enumerate(generated_requests):
            generated_request = GeneratedRequest(
                fuzzer_request_id=fuzzer_request.id,
                request_number=i + 1,
                request_content=req.get("request", ""),
                placeholder=req.get("placeholder"),
                payload=req.get("payload"),
                position=req.get("position")
            )
            
            # applied_toフィールドがある場合は保存
            if "applied_to" in req:
                generated_request.set_applied_to(req["applied_to"])
            
            db.add(generated_request)
        
        db.commit()
        return fuzzer_request
    
    def get_all_fuzzer_requests(self, db, limit: int = 100, offset: int = 0) -> List[FuzzerRequest]:
        """
        全てのファザーリクエストを取得
        
        Args:
            db: データベースセッション
            limit (int): 取得件数の制限
            offset (int): オフセット
            
        Returns:
            List[FuzzerRequest]: ファザーリクエストのリスト
        """
        return db.query(FuzzerRequest).order_by(FuzzerRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_fuzzer_request_by_id(self, db, request_id: int) -> Optional[FuzzerRequest]:
        """
        指定されたIDのファザーリクエストを取得
        
        Args:
            db: データベースセッション
            request_id (int): ファザーリクエストのID
            
        Returns:
            Optional[FuzzerRequest]: ファザーリクエストオブジェクト（見つからない場合はNone）
        """
        return db.query(FuzzerRequest).filter(FuzzerRequest.id == request_id).first()
    
    def delete_fuzzer_request(self, db, request_id: int) -> bool:
        """
        指定されたIDのファザーリクエストを削除
        
        Args:
            db: データベースセッション
            request_id (int): ファザーリクエストのID
            
        Returns:
            bool: 削除が成功した場合はTrue
        """
        fuzzer_request = db.query(FuzzerRequest).filter(FuzzerRequest.id == request_id).first()
        if fuzzer_request:
            db.delete(fuzzer_request)
            db.commit()
            return True
        return False
    
    def get_statistics(self, db) -> dict:
        """
        データベースの統計情報を取得
        
        Args:
            db: データベースセッション
            
        Returns:
            dict: 統計情報
        """
        total_requests = db.query(FuzzerRequest).count()
        total_generated = db.query(GeneratedRequest).count()
        
        # 戦略別の統計
        strategy_stats = {}
        for strategy in ["sniper", "battering_ram", "pitchfork", "cluster_bomb"]:
            count = db.query(FuzzerRequest).filter(FuzzerRequest.strategy == strategy).count()
            strategy_stats[strategy] = count
        
        return {
            "total_fuzzer_requests": total_requests,
            "total_generated_requests": total_generated,
            "strategy_distribution": strategy_stats
        }
    
    # ジョブ関連の操作メソッド
    def save_job(self, db, job_id: str, name: str, status: str, fuzzer_request_id: int, 
                 http_config: Optional[dict] = None, progress: Optional[dict] = None, 
                 error_message: Optional[str] = None) -> Job:
        """
        ジョブを保存
        
        Args:
            db: データベースセッション
            job_id (str): ジョブID
            name (str): ジョブ名
            status (str): ジョブの状態
            fuzzer_request_id (int): 関連するファザーリクエストのID
            http_config (Optional[dict]): HTTP設定
            progress (Optional[dict]): 進捗情報
            error_message (Optional[str]): エラーメッセージ
            
        Returns:
            Job: 保存されたジョブオブジェクト
        """
        job = Job(
            id=job_id,
            name=name,
            status=status,
            fuzzer_request_id=fuzzer_request_id,
            http_config=http_config,
            error_message=error_message
        )
        
        if progress:
            job.set_progress(progress)
        else:
            job.set_progress({})
        
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    def get_all_jobs(self, db) -> List[Job]:
        """
        全てのジョブを取得
        
        Args:
            db: データベースセッション
            
        Returns:
            List[Job]: ジョブのリスト
        """
        return db.query(Job).order_by(Job.created_at.desc()).all()
    
    def get_job_by_id(self, db, job_id: str) -> Optional[Job]:
        """
        指定されたIDのジョブを取得
        
        Args:
            db: データベースセッション
            job_id (str): ジョブID
            
        Returns:
            Optional[Job]: ジョブオブジェクト（見つからない場合はNone）
        """
        return db.query(Job).filter(Job.id == job_id).first()
    
    def update_job(self, db, job_id: str, status: Optional[str] = None, 
                   progress: Optional[dict] = None, error_message: Optional[str] = None) -> bool:
        """
        ジョブを更新
        
        Args:
            db: データベースセッション
            job_id (str): ジョブID
            status (Optional[str]): 新しい状態
            progress (Optional[dict]): 新しい進捗情報
            error_message (Optional[str]): エラーメッセージ
            
        Returns:
            bool: 更新が成功した場合はTrue
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        
        if status is not None:
            job.status = status
        if progress is not None:
            job.set_progress(progress)
        if error_message is not None:
            job.error_message = error_message
        
        job.updated_at = datetime.now()
        db.commit()
        return True
    
    def delete_job(self, db, job_id: str) -> bool:
        """
        指定されたIDのジョブを削除
        
        Args:
            db: データベースセッション
            job_id (str): ジョブID
            
        Returns:
            bool: 削除が成功した場合はTrue
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            db.delete(job)
            db.commit()
            return True
        return False
    
    def save_job_results(self, db, job_id: str, results: List[dict]) -> List[JobResult]:
        """
        ジョブの実行結果を保存
        
        Args:
            db: データベースセッション
            job_id (str): ジョブID
            results (List[dict]): 実行結果のリスト
            
        Returns:
            List[JobResult]: 保存された実行結果のリスト
        """
        job_results = []
        
        for i, result in enumerate(results):
            http_response = result.get('http_response', {})
            is_success = not http_response.get('error')
            
            job_result = JobResult(
                job_id=job_id,
                request_number=i + 1,
                request_content=result.get('request', ''),
                placeholder=result.get('placeholder'),
                payload=result.get('payload'),
                position=result.get('position'),
                success=1 if is_success else 0,
                error_message=http_response.get('error'),
                elapsed_time=int(http_response.get('elapsed_time', 0) * 1000) if http_response.get('elapsed_time') else None
            )
            
            if http_response:
                job_result.set_http_response(http_response)
            
            db.add(job_result)
            job_results.append(job_result)
        
        db.commit()
        return job_results
    
    def get_job_results(self, db, job_id: str) -> List[dict]:
        """
        ジョブの実行結果を取得
        
        Args:
            db: データベースセッション
            job_id (str): ジョブID
            
        Returns:
            List[dict]: 実行結果のリスト
        """
        try:
            job_results = db.query(JobResult).filter(JobResult.job_id == job_id).order_by(JobResult.request_number).all()
            
            results = []
            for job_result in job_results:
                # プレースホルダ情報を安全に取得
                placeholder = getattr(job_result, 'placeholder', None)
                payload = getattr(job_result, 'payload', None) 
                position = getattr(job_result, 'position', None)
                
                result = {
                    'request': job_result.request_content,
                    'placeholder': placeholder,
                    'payload': payload,
                    'position': position,
                    'http_response': job_result.get_http_response()
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"ジョブ結果の取得でエラー: {e}")
            # エラーが発生した場合は空のリストを返す
            return []
    
    def get_job_statistics(self, db) -> dict:
        """
        ジョブの統計情報を取得
        
        Args:
            db: データベースセッション
            
        Returns:
            dict: ジョブ統計情報
        """
        total_jobs = db.query(Job).count()
        
        # 状態別の統計
        status_counts = {}
        for status in ["pending", "running", "completed", "failed", "cancelled"]:
            count = db.query(Job).filter(Job.status == status).count()
            status_counts[status] = count
        
        # 総リクエスト数と平均実行時間
        total_requests = 0
        total_execution_time = 0
        completed_jobs = 0
        
        for job in db.query(Job).filter(Job.status == "completed").all():
            progress = job.get_progress()
            total_requests += progress.get('total_requests', 0)
            
            if job.created_at and job.updated_at:
                execution_time = (job.updated_at - job.created_at).total_seconds()
                total_execution_time += execution_time
                completed_jobs += 1
        
        avg_execution_time = total_execution_time / completed_jobs if completed_jobs > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "pending_jobs": status_counts.get("pending", 0),
            "running_jobs": status_counts.get("running", 0),
            "completed_jobs": status_counts.get("completed", 0),
            "failed_jobs": status_counts.get("failed", 0),
            "cancelled_jobs": status_counts.get("cancelled", 0),
            "total_requests": total_requests,
            "avg_execution_time": avg_execution_time
        }

# グローバルなデータベースマネージャーインスタンス
db_manager = DatabaseManager() 