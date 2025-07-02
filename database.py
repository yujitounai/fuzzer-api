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

# グローバルなデータベースマネージャーインスタンス
db_manager = DatabaseManager() 