"""
プレースホルダ置換API - 4つの攻撃戦略を実装

このAPIは、Burp SuiteのIntruder機能で使用される4つの攻撃戦略を実装しています：
- Sniper: 1つのペイロードセットを各プレースホルダ位置に順番に配置
- Battering Ram: 1つのペイロードセットを全てのプレースホルダに同時に配置
- Pitchfork: 複数のペイロードセットを対応するプレースホルダに同時に配置
- Cluster Bomb: 全てのペイロードセットの組み合わせをテスト

プレースホルダ形式: <<プレースホルダ名>> または <<>> (Sniper攻撃用)

データベース機能:
- リクエストと生成されたリクエストの永続化
- 履歴の表示と管理
- 統計情報の提供
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import itertools
from enum import Enum
import uvicorn
import asyncio
from sqlalchemy.orm import Session

# データベース関連のインポート
from database import db_manager, FuzzerRequest, GeneratedRequest, Job as DBJob, JobResult as DBJobResult, User, get_db

# HTTPリクエスト送信関連のインポート
from http_client import RequestExecutor, HTTPRequestConfig
from job_manager import job_manager

# 認証関連のインポート
from auth import auth_manager, get_current_user, get_current_active_user

# 脆弱性分析関連のインポート
from vulnerability_analysis import (
    error_pattern_analyzer, 
    payload_reflection_analyzer, 
    time_delay_analyzer,
    ErrorPatternConfigModel,
    PayloadReflectionConfigModel,
    TimeDelayConfigModel,
    ErrorPatternAnalysisResult,
    PayloadReflectionAnalysisResult,
    TimeDelayAnalysisResult
)

app = FastAPI(
    title="プレースホルダ置換API",
    description="Burp Suite Intruderの4つの攻撃戦略を実装したAPI",
    version="1.0.0"
)

# ビルトインアカウントを作成する関数
def create_builtin_account():
    """アプリケーション起動時にビルトインアカウントを作成"""
    try:
        db = next(get_db())
        builtin_username = "admin"
        builtin_email = "admin@example.com"
        builtin_password = "admin123"
        
        # ビルトインアカウントが既に存在するかチェック
        existing_user = auth_manager.get_user_by_username(db, builtin_username)
        if existing_user:
            print(f"ビルトインアカウント '{builtin_username}' は既に存在しています")
            return existing_user
        
        # ビルトインアカウントを作成
        print(f"ビルトインアカウント '{builtin_username}' を作成しています...")
        user = auth_manager.create_user(
            db=db,
            username=builtin_username,
            email=builtin_email,
            password=builtin_password
        )
        print(f"ビルトインアカウント '{builtin_username}' が正常に作成されました")
        return user
        
    except Exception as e:
        print(f"ビルトインアカウントの作成中にエラーが発生しました: {e}")
        return None
    finally:
        if 'db' in locals():
            db.close()

# アプリケーション起動時のイベント
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    print("アプリケーションを起動しています...")
    # ビルトインアカウントを作成
    create_builtin_account()
    print("アプリケーションの起動が完了しました")

# APIルーターを作成
from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

# データベーステーブルの作成
db_manager.create_tables()

# 静的ファイルを配信
app.mount("/static", StaticFiles(directory="."), name="static")

# APIルーターをアプリケーションに登録
app.include_router(api_router)

# 注意: get_dbはdatabase.pyから直接インポートして使用

class AttackStrategy(str, Enum):
    SNIPER = "sniper"
    BATTERING_RAM = "battering_ram"
    PITCHFORK = "pitchfork"
    CLUSTER_BOMB = "cluster_bomb"

class PayloadSet(BaseModel):
    """
    ペイロードセットの定義
    
    Attributes:
        payloads (List[str]): ペイロードのリスト
    """
    name: str
    payloads: List[str]

class MutationValue(BaseModel):
    """
    変異値の定義（辞書的な値またはrepeat機能付きの値）
    
    Attributes:
        value (str): 基本値
        repeat (Optional[int]): 繰り返し回数（指定された場合、valueをrepeat回繰り返す）
    """
    value: str
    repeat: Optional[int] = None

def process_mutation_values(values: List[Union[str, MutationValue]]) -> List[str]:
    """
    変異値のリストを処理して、実際のペイロードリストを生成する
    
    Args:
        values (List[Union[str, MutationValue]]): 変異値のリスト
        
    Returns:
        List[str]: 処理されたペイロードのリスト
    """
    processed_payloads = []
    
    for value in values:
        if isinstance(value, str):
            # 文字列の場合はそのまま追加
            processed_payloads.append(value)
        elif isinstance(value, MutationValue):
            # MutationValueの場合はrepeat機能を処理
            if value.repeat is not None and value.repeat > 0:
                # repeat回数分繰り返す
                processed_payloads.append(value.value * value.repeat)
            else:
                # repeatが指定されていない場合はそのまま追加
                processed_payloads.append(value.value)
    
    return processed_payloads

class Mutation(BaseModel):
    """
    変異の定義
    
    Attributes:
        token (str): 置換対象のトークン（例: "<<X>>"）
        strategy (str): 変異戦略（"dictionary", "numbers"など）
        values (List[Union[str, MutationValue]]): 変異値のリスト
    """
    token: str
    strategy: str
    values: List[Union[str, MutationValue]]

class IntuitiveRequest(BaseModel):
    """
    直感的なプレースホルダ置換リクエストの定義
    
    Attributes:
        template (str): プレースホルダを含むテンプレート文字列
        strategy (str): 攻撃戦略（sniper, battering_ram, pitchfork, cluster_bomb）
        payload_sets (List[Mutation]): ペイロードセットのリスト（token, strategy, valuesを含む）
    """
    template: str
    strategy: AttackStrategy
    payload_sets: List[Mutation]

class MutationRequest(BaseModel):
    """
    変異ベースのプレースホルダ置換リクエストの定義
    
    Attributes:
        template (str): プレースホルダを含むテンプレート文字列
        mutations (List[Mutation]): 変異のリスト
    """
    template: str
    mutations: List[Mutation]

class PlaceholderRequest(BaseModel):
    """
    プレースホルダ置換リクエストの定義
    
    Attributes:
        template (str): プレースホルダを含むテンプレート文字列
        placeholders (List[str]): プレースホルダ名のリスト（Sniper攻撃では空リスト）
        strategy (str): 攻撃戦略（sniper, battering_ram, pitchfork, cluster_bomb）
        payload_sets (List[PayloadSet]): ペイロードセットのリスト
    """
    template: str
    placeholders: List[str]
    strategy: AttackStrategy
    payload_sets: List[PayloadSet]

class PlaceholderResponse(BaseModel):
    """
    プレースホルダ置換レスポンスの定義
    
    Attributes:
        strategy (str): 使用された攻撃戦略
        total_requests (int): 生成されたリクエストの総数
        requests (List[Dict[str, Any]]): 生成されたリクエストのリスト
        request_id (int): データベースに保存されたリクエストのID
    """
    strategy: str
    total_requests: int
    requests: List[Dict[str, Any]]
    request_id: Optional[int] = None

class FuzzerRequestResponse(BaseModel):
    """
    ファザーリクエスト履歴のレスポンス定義
    
    Attributes:
        id (int): リクエストのID
        template (str): テンプレート文字列
        placeholders (List[str]): プレースホルダ名のリスト
        strategy (str): 攻撃戦略
        total_requests (int): 生成されたリクエストの総数
        created_at (str): 作成日時
    """
    id: int
    template: str
    placeholders: List[str]
    strategy: str
    total_requests: int
    created_at: str

class StatisticsResponse(BaseModel):
    """
    統計情報のレスポンス定義
    
    Attributes:
        total_fuzzer_requests (int): 総ファザーリクエスト数
        total_generated_requests (int): 総生成リクエスト数
        strategy_distribution (Dict[str, int]): 戦略別の分布
    """
    total_fuzzer_requests: int
    total_generated_requests: int
    strategy_distribution: Dict[str, int]

class HTTPRequestConfigModel(BaseModel):
    """
    HTTPリクエスト設定の定義
    
    Attributes:
        timeout (int): タイムアウト時間（秒）
        follow_redirects (bool): リダイレクトを追跡するかどうか
        verify_ssl (bool): SSL証明書を検証するかどうか
        scheme (str): プロトコル（http または https）
        base_url (str): ベースURL（スキームなし）
        additional_headers (Dict[str, str]): 追加のヘッダー
        sequential_execution (bool): 同期実行フラグ（True: 順次実行, False: 並列実行）
        request_delay (float): リクエスト間の待機時間（秒）
    """
    timeout: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = False
    scheme: str = "http"
    base_url: str = "localhost:8000"
    additional_headers: Optional[Dict[str, str]] = None
    sequential_execution: bool = False
    request_delay: float = 0.0

class ExecuteRequestModel(BaseModel):
    """
    リクエスト実行の定義
    
    Attributes:
        request_id (int): 実行するリクエストのID
        http_config (HTTPRequestConfigModel): HTTPリクエスト設定
    """
    request_id: int
    http_config: Optional[HTTPRequestConfigModel] = None

class ExecuteResponseModel(BaseModel):
    """
    リクエスト実行結果の定義
    
    Attributes:
        request_id (int): 実行したリクエストのID
        total_requests (int): 実行したリクエストの総数
        successful_requests (int): 成功したリクエストの数
        failed_requests (int): 失敗したリクエストの数
        results (List[Dict[str, Any]]): 実行結果の詳細
    """
    request_id: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    results: List[Dict[str, Any]]

class ExecuteSingleRequestModel(BaseModel):
    """
    個別リクエスト実行の定義
    
    Attributes:
        request_id (int): 実行するリクエストのID
        position (int): 実行するリクエストの位置（インデックス）
        http_config (HTTPRequestConfigModel): HTTPリクエスト設定
    """
    request_id: int
    position: int
    http_config: Optional[HTTPRequestConfigModel] = None

class ExecuteSingleResponseModel(BaseModel):
    """
    個別リクエスト実行結果の定義
    
    Attributes:
        request_id (int): 実行したリクエストのID
        position (int): 実行したリクエストの位置
        request (Dict[str, Any]): 実行したリクエストの内容
        http_response (Dict[str, Any]): HTTPレスポンス
    """
    request_id: int
    position: int
    request: Dict[str, Any]
    http_response: Optional[Dict[str, Any]] = None

class JobResponseModel(BaseModel):
    """
    ジョブ作成レスポンスの定義
    
    Attributes:
        job_id (str): ジョブのID
        status (str): ジョブの状態
        message (str): メッセージ
    """
    job_id: str
    status: str
    message: str

class JobStatusResponseModel(BaseModel):
    """
    ジョブ状態レスポンスの定義
    
    Attributes:
        job_id (str): ジョブのID
        status (str): ジョブの状態
        progress (Dict[str, Any]): 進捗情報
        results (Optional[List[Dict[str, Any]]]): 実行結果
        error_message (Optional[str]): エラーメッセージ
    """
    job_id: str
    status: str
    progress: Dict[str, Any]
    results: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None

class JobSummaryResponseModel(BaseModel):
    """
    ジョブサマリーレスポンスの定義（結果データを含まない）
    
    Attributes:
        job_id (str): ジョブのID
        status (str): ジョブの状態
        progress (Dict[str, Any]): 進捗情報
        error_message (Optional[str]): エラーメッセージ
        created_at (str): 作成日時
        updated_at (str): 更新日時
        request_id (Optional[int]): 関連するリクエストID
    """
    job_id: str
    status: str
    progress: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    request_id: Optional[int] = None

class JobResultSummaryModel(BaseModel):
    """
    ジョブ結果サマリーの定義
    
    Attributes:
        request_number (int): リクエスト番号
        placeholder (Optional[str]): プレースホルダ名
        payload (Optional[str]): ペイロード
        position (Optional[int]): 位置
        status_code (Optional[int]): HTTPステータスコード
        success (bool): 成功フラグ
        error_message (Optional[str]): エラーメッセージ
        elapsed_time (Optional[float]): 実行時間
        url (Optional[str]): リクエストURL
    """
    request_number: int
    placeholder: Optional[str] = None
    payload: Optional[str] = None
    position: Optional[int] = None
    status_code: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    elapsed_time: Optional[float] = None
    url: Optional[str] = None

class JobResultsResponseModel(BaseModel):
    """
    ジョブ結果リストレスポンスの定義
    
    Attributes:
        job_id (str): ジョブのID
        total_results (int): 総結果数
        results (List[JobResultSummaryModel]): 結果サマリーのリスト
        limit (int): 取得制限数
        offset (int): オフセット
        has_more (bool): 更に結果があるかどうか
    """
    job_id: str
    total_results: int
    results: List[JobResultSummaryModel]
    limit: int
    offset: int
    has_more: bool

class JobResultDetailResponseModel(BaseModel):
    """
    ジョブ結果詳細レスポンスの定義
    
    Attributes:
        job_id (str): ジョブのID
        request_number (int): リクエスト番号
        request_content (str): リクエスト内容
        placeholder (Optional[str]): プレースホルダ名
        payload (Optional[str]): ペイロード
        position (Optional[int]): 位置
        http_response (Optional[Dict[str, Any]]): HTTPレスポンス
        success (bool): 成功フラグ
        error_message (Optional[str]): エラーメッセージ
        elapsed_time (Optional[float]): 実行時間
        created_at (str): 作成日時
    """
    job_id: str
    request_number: int
    request_content: str
    placeholder: Optional[str] = None
    payload: Optional[str] = None
    position: Optional[int] = None
    http_response: Optional[Dict[str, Any]] = None
    success: bool
    error_message: Optional[str] = None
    elapsed_time: Optional[float] = None
    created_at: str

class JobListResponseModel(BaseModel):
    """
    ジョブ一覧レスポンスの定義
    
    Attributes:
        jobs (List[Dict[str, Any]]): ジョブのリスト
        total (int): 総ジョブ数
    """
    jobs: List[Dict[str, Any]]
    total: int

# 認証関連のPydanticモデル
class UserRegisterRequest(BaseModel):
    """
    ユーザー登録リクエストの定義
    
    Attributes:
        username (str): ユーザー名
        email (str): メールアドレス
        password (str): パスワード
    """
    username: str
    email: str
    password: str

class UserLoginRequest(BaseModel):
    """
    ユーザーログインリクエストの定義
    
    Attributes:
        username (str): ユーザー名
        password (str): パスワード
    """
    username: str
    password: str

class UserResponse(BaseModel):
    """
    ユーザー情報レスポンスの定義
    
    Attributes:
        id (int): ユーザーID
        username (str): ユーザー名
        email (str): メールアドレス
        is_active (bool): アクティブフラグ
        created_at (str): 作成日時
        updated_at (str): 更新日時
    """
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    updated_at: str

class Token(BaseModel):
    """
    トークンレスポンスの定義
    
    Attributes:
        access_token (str): アクセストークン
        token_type (str): トークンタイプ
        user (UserResponse): ユーザー情報
    """
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    """
    トークンデータの定義
    
    Attributes:
        user_id (Optional[int]): ユーザーID
    """
    user_id: Optional[int] = None

class FuzzerEngine:
    def __init__(self):
        pass
    
    def sniper_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Sniper攻撃: 各ペイロードを各位置に順番に配置
        
        Sniper攻撃では固定のプレースホルダ <<>> を使用し、同じプレースホルダが
        複数ある場合に、各出現位置を順番にペイロードで置換します。
        置換されなかったプレースホルダは空文字列で置換されます。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): 使用されない（Sniper攻撃では固定プレースホルダを使用）
            payload_sets (List[PayloadSet]): ペイロードセットのリスト（最初のセットのみ使用）
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットが提供されていない場合
        """
        if not payload_sets:
            raise ValueError("少なくとも1つのペイロードセットが必要です")
        
        payload_set = payload_sets[0]
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template.replace("<<>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payload": "",
            "position": 0
        })
        
        # Sniper攻撃では固定のプレースホルダ <<>> を使用
        placeholder_pattern = "<<>>"
        placeholder_count = template.count(placeholder_pattern)
        
        for payload in payload_set.payloads:
            for position in range(placeholder_count):
                result = template
                # 指定された位置のプレースホルダのみを置換
                current_pos = 0
                start = 0
                while current_pos <= position:
                    pos = result.find(placeholder_pattern, start)
                    if pos == -1:
                        break
                    if current_pos == position:
                        # この位置のプレースホルダを置換
                        result = result[:pos] + payload + result[pos + len(placeholder_pattern):]
                        break
                    start = pos + 1
                    current_pos += 1
                
                # 置換されていないプレースホルダを空文字列で置換
                result = result.replace(placeholder_pattern, "")
                
                requests.append({
                    "request": result,
                    "placeholder": "<<>>",
                    "payload": payload,
                    "position": position + 1
                })
        
        return requests
    
    def battering_ram_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Battering Ram攻撃: 同じペイロードを全ての位置に同時に配置
        
        Battering Ram攻撃では、1つのペイロードセットの各ペイロードを
        全てのプレースホルダに同時に配置します。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            payload_sets (List[PayloadSet]): ペイロードセットのリスト（最初のセットのみ使用）
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットが提供されていない場合
        """
        if not payload_sets:
            raise ValueError("少なくとも1つのペイロードセットが必要です")
        
        payload_set = payload_sets[0]
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template
        for placeholder in placeholders:
            original_template = original_template.replace(f"<<{placeholder}>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payload": "",
            "applied_to": []
        })
        
        for payload in payload_set.payloads:
            result = template
            for placeholder in placeholders:
                result = result.replace(f"<<{placeholder}>>", payload)
            requests.append({
                "request": result,
                "payload": payload,
                "applied_to": placeholders
            })
        
        return requests
    
    def pitchfork_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Pitchfork攻撃: 各位置に異なるペイロードセットを使用し、同時に配置
        
        Pitchfork攻撃では、各プレースホルダに対応するペイロードセットがあり、
        各セットの同じインデックスのペイロードを同時に配置します。
        最小のペイロードセットのサイズまで処理します。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            payload_sets (List[PayloadSet]): ペイロードセットのリスト
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットの数がプレースホルダの数と一致しない場合
        """
        if len(payload_sets) != len(placeholders):
            raise ValueError("ペイロードセットの数はプレースホルダの数と一致する必要があります")
        
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template
        for placeholder in placeholders:
            original_template = original_template.replace(f"<<{placeholder}>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payloads": {}
        })
        
        # 最小のペイロードセットのサイズを取得
        min_payload_count = min(len(ps.payloads) for ps in payload_sets)
        
        for i in range(min_payload_count):
            result = template
            placeholder_payload_map = {}
            
            for j, (placeholder, payload_set) in enumerate(zip(placeholders, payload_sets)):
                payload = payload_set.payloads[i]
                result = result.replace(f"<<{placeholder}>>", payload)
                placeholder_payload_map[placeholder] = payload
            
            requests.append({
                "request": result,
                "payloads": placeholder_payload_map
            })
        
        return requests
    
    def cluster_bomb_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Cluster Bomb攻撃: 全てのペイロードの組み合わせをテスト
        
        Cluster Bomb攻撃では、各プレースホルダに対応するペイロードセットがあり、
        全てのペイロードの組み合わせをテストします。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            payload_sets (List[PayloadSet]): ペイロードセットのリスト
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットの数がプレースホルダの数と一致しない場合
        """
        if len(payload_sets) != len(placeholders):
            raise ValueError("ペイロードセットの数はプレースホルダの数と一致する必要があります")
        
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template
        for placeholder in placeholders:
            original_template = original_template.replace(f"<<{placeholder}>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payloads": {}
        })
        
        # 全てのペイロードの組み合わせを生成
        payload_combinations = list(itertools.product(*[ps.payloads for ps in payload_sets]))
        
        for combination in payload_combinations:
            result = template
            placeholder_payload_map = {}
            
            for placeholder, payload in zip(placeholders, combination):
                result = result.replace(f"<<{placeholder}>>", payload)
                placeholder_payload_map[placeholder] = payload
            
            requests.append({
                "request": result,
                "payloads": placeholder_payload_map
            })
        
        return requests

    def mutation_attack(self, template: str, mutations: List[Mutation]) -> List[Dict[str, Any]]:
        """
        変異ベース攻撃: 各トークンに対して指定された変異を適用
        
        変異ベース攻撃では、各トークンに対して辞書的な値やrepeat機能付きの値を
        適用してリクエストを生成します。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            mutations (List[Mutation]): 変異のリスト
            
        Returns:
            List[Dict[str, Any]]: 生成されたリクエストのリスト
        """
        requests = []
        
        # オリジナルのテンプレート（全てのトークンを空文字列で置換）を最初に追加
        original_template = template
        for mutation in mutations:
            original_template = original_template.replace(mutation.token, "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payload": "",
            "position": 0
        })
        
        # 各変異に対して処理
        for mutation in mutations:
            # 変異値を処理してペイロードリストを生成
            payloads = process_mutation_values(mutation.values)
            
            # 各ペイロードに対してリクエストを生成
            for i, payload in enumerate(payloads):
                result = template.replace(mutation.token, payload)
                requests.append({
                    "request": result,
                    "placeholder": mutation.token,
                    "payload": payload,
                    "position": i + 1,
                    "strategy": mutation.strategy
                })
        
        return requests

fuzzer = FuzzerEngine()

async def execute_single_request_async(request_data: Dict[str, Any], http_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    単一リクエストを非同期で実行するヘルパー関数
    
    Args:
        request_data (Dict[str, Any]): リクエストデータ
        http_config (Optional[Dict[str, Any]]): HTTP設定
        
    Returns:
        Dict[str, Any]: 実行結果
    """
    try:
        # HTTP設定を適用
        config = HTTPRequestConfig()
        if http_config:
            config.timeout = http_config.get('timeout', 30)
            config.follow_redirects = http_config.get('follow_redirects', True)
            config.verify_ssl = http_config.get('verify_ssl', False)
            config.scheme = http_config.get('scheme', 'http')
            config.base_url = http_config.get('base_url', 'localhost:8000')
            config.additional_headers = http_config.get('additional_headers')
        
        # リクエスト実行
        executor = RequestExecutor(config)
        result = await executor.execute_request(request_data['request'])
        
        return {
            'request': request_data,
            'http_response': result,
            'success': True
        }
    except Exception as e:
        return {
            'request': request_data,
            'error': str(e),
            'success': False
        }

@app.post("/api/replace-placeholders", response_model=PlaceholderResponse)
async def replace_placeholders(request: PlaceholderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    プレースホルダ置換APIエンドポイント
    
    指定された攻撃戦略に基づいてプレースホルダをペイロードで置換し、
    生成されたリクエストのリストを返します。また、リクエストと生成された
    リクエストをデータベースに永続化します。
    
    Args:
        request (PlaceholderRequest): 置換リクエスト
        db (Session): データベースセッション
        
    Returns:
        PlaceholderResponse: 攻撃戦略名、総リクエスト数、リクエストリスト、リクエストIDを含むレスポンス
        
    Raises:
        HTTPException: 無効な攻撃戦略が指定された場合
    """
    try:
        # 攻撃戦略に基づいて適切なメソッドを呼び出し
        if request.strategy == AttackStrategy.SNIPER:
            requests = fuzzer.sniper_attack(request.template, request.placeholders, request.payload_sets)
        elif request.strategy == AttackStrategy.BATTERING_RAM:
            requests = fuzzer.battering_ram_attack(request.template, request.placeholders, request.payload_sets)
        elif request.strategy == AttackStrategy.PITCHFORK:
            requests = fuzzer.pitchfork_attack(request.template, request.placeholders, request.payload_sets)
        elif request.strategy == AttackStrategy.CLUSTER_BOMB:
            requests = fuzzer.cluster_bomb_attack(request.template, request.placeholders, request.payload_sets)
        else:
            raise HTTPException(status_code=400, detail=f"無効な攻撃戦略: {request.strategy}")
        
        # ペイロードセットを辞書形式に変換
        payload_sets_dict = [{"name": ps.name, "payloads": ps.payloads} for ps in request.payload_sets]
        
        # データベースに保存
        fuzzer_request = db_manager.save_fuzzer_request(
            db=db,
            template=request.template,
            placeholders=request.placeholders,
            strategy=request.strategy.value,
            payload_sets=payload_sets_dict,
            generated_requests=requests
        )
        
        return PlaceholderResponse(
            strategy=request.strategy.value,
            total_requests=len(requests),
            requests=requests,
            request_id=fuzzer_request.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部エラー: {str(e)}")

@app.post("/api/mutations", response_model=PlaceholderResponse)
async def apply_mutations(request: MutationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    変異ベースのプレースホルダ置換を実行
    
    各トークンに対して指定された変異（辞書的な値やrepeat機能付きの値）を適用して
    リクエストを生成します。
    
    Args:
        request (MutationRequest): 変異リクエスト
        db (Session): データベースセッション
        
    Returns:
        PlaceholderResponse: 生成されたリクエストの情報
    """
    try:
        # 変異ベース攻撃を実行
        requests = fuzzer.mutation_attack(request.template, request.mutations)
        
        # データベースに保存
        fuzzer_request = FuzzerRequest(
            template=request.template,
            strategy="mutation",
            total_requests=len(requests)
        )
        fuzzer_request.set_placeholders([mutation.token for mutation in request.mutations])
        fuzzer_request.set_payload_sets([])  # mutationsではpayload_setsは使用しない
        db.add(fuzzer_request)
        db.commit()
        db.refresh(fuzzer_request)
        
        # 生成されたリクエストをデータベースに保存
        for i, req in enumerate(requests):
            generated_request = GeneratedRequest(
                fuzzer_request_id=fuzzer_request.id,
                request_number=i + 1,
                request_content=req["request"],
                placeholder=req.get("placeholder", ""),
                payload=req.get("payload", ""),
                position=req.get("position", 0)
            )
            db.add(generated_request)
        db.commit()
        
        return PlaceholderResponse(
            strategy="mutation",
            total_requests=len(requests),
            requests=requests,
            request_id=fuzzer_request.id
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/intuitive", response_model=PlaceholderResponse)
async def intuitive_replace_placeholders(request: IntuitiveRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    直感的なプレースホルダ置換API
    
    placeholdersを使わずに、payload_setsのtokenから自動的にプレースホルダを抽出します。
    """
    try:
        # payload_setsからプレースホルダを自動抽出（<<>>を除去）
        placeholders = []
        for payload_set in request.payload_sets:
            # <<username>> -> username に変換
            placeholder_name = payload_set.token.strip("<>")
            placeholders.append(placeholder_name)
        
        # payload_setsを従来の形式に変換
        converted_payload_sets = []
        for payload_set in request.payload_sets:
            # valuesを処理してペイロードリストを生成
            processed_payloads = process_mutation_values(payload_set.values)
            
            # プレースホルダ名をnameとして使用
            placeholder_name = payload_set.token.strip("<>")
            converted_payload_sets.append(PayloadSet(
                name=placeholder_name,
                payloads=processed_payloads
            ))
        
        # 従来のリクエスト形式に変換
        placeholder_request = PlaceholderRequest(
            template=request.template,
            placeholders=placeholders,
            strategy=request.strategy,
            payload_sets=converted_payload_sets
        )
        
        # 既存の処理を再利用
        return await replace_placeholders(placeholder_request, db)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"リクエストの処理に失敗しました: {str(e)}")

@app.get("/")
async def root():
    """
    ルートエンドポイント - 履歴ページにリダイレクト
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/history-page", status_code=302)

@app.get("/api/history", response_model=List[FuzzerRequestResponse])
async def get_history(db: Session = Depends(get_db), limit: int = 50, offset: int = 0, current_user: User = Depends(get_current_active_user)):
    """
    ファザーリクエストの履歴を取得するエンドポイント
    
    Args:
        db (Session): データベースセッション
        limit (int): 取得件数の制限（デフォルト: 50）
        offset (int): オフセット（デフォルト: 0）
        
    Returns:
        List[FuzzerRequestResponse]: ファザーリクエストの履歴リスト
    """
    fuzzer_requests = db_manager.get_all_fuzzer_requests(db, limit=limit, offset=offset)
    
    history = []
    for req in fuzzer_requests:
        history.append(FuzzerRequestResponse(
            id=req.id,
            template=req.template,
            placeholders=req.get_placeholders(),
            strategy=req.strategy,
            total_requests=req.total_requests,
            created_at=req.created_at.isoformat() if req.created_at else ""
        ))
    
    return history

@app.get("/api/history/{request_id}", response_model=PlaceholderResponse)
async def get_request_detail(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    特定のファザーリクエストの詳細を取得するエンドポイント
    
    Args:
        request_id (int): ファザーリクエストのID
        db (Session): データベースセッション
        
    Returns:
        PlaceholderResponse: ファザーリクエストの詳細
        
    Raises:
        HTTPException: リクエストが見つからない場合
    """
    fuzzer_request = db_manager.get_fuzzer_request_by_id(db, request_id)
    if not fuzzer_request:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")
    
    # 生成されたリクエストを取得
    generated_requests = []
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
        
        generated_requests.append(req_dict)
    
    return PlaceholderResponse(
        strategy=fuzzer_request.strategy,
        total_requests=fuzzer_request.total_requests,
        requests=generated_requests,
        request_id=fuzzer_request.id
    )

@app.delete("/api/history/{request_id}")
async def delete_request(request_id: int, db: Session = Depends(get_db)):
    """
    特定のファザーリクエストを削除するエンドポイント
    
    Args:
        request_id (int): ファザーリクエストのID
        db (Session): データベースセッション
        
    Returns:
        Dict[str, str]: 削除結果のメッセージ
        
    Raises:
        HTTPException: リクエストが見つからない場合
    """
    success = db_manager.delete_fuzzer_request(db, request_id)
    if not success:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")
    
    return {"message": f"リクエストID {request_id} を削除しました"}

@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    データベースの統計情報を取得するエンドポイント
    
    Args:
        db (Session): データベースセッション
        
    Returns:
        StatisticsResponse: 統計情報
    """
    stats = db_manager.get_statistics(db)
    return StatisticsResponse(**stats)

@app.post("/api/execute-requests", response_model=JobResponseModel)
async def execute_requests(request: ExecuteRequestModel, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    リクエスト実行APIエンドポイント（JobManager使用）
    
    指定されたリクエストIDの全ての生成されたリクエストをバックグラウンドで実行します。
    
    Args:
        request (ExecuteRequestModel): 実行リクエスト
        db (Session): データベースセッション
        
    Returns:
        JobResponseModel: ジョブ作成結果
        
    Raises:
        HTTPException: リクエストが見つからない場合
    """
    try:
        # リクエストを取得
        fuzzer_request = db_manager.get_fuzzer_request_by_id(db, request.request_id)
        if not fuzzer_request:
            raise HTTPException(status_code=404, detail="リクエストが見つかりません")
        
        # 生成されたリクエストを取得
        generated_requests = []
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
            
            generated_requests.append(req_dict)
        
        # HTTP設定を辞書形式に変換
        http_config_dict = None
        if request.http_config:
            http_config_dict = {
                'timeout': request.http_config.timeout,
                'follow_redirects': request.http_config.follow_redirects,
                'verify_ssl': request.http_config.verify_ssl,
                'scheme': request.http_config.scheme,
                'base_url': request.http_config.base_url,
                'additional_headers': request.http_config.additional_headers,
                'sequential_execution': request.http_config.sequential_execution,
                'request_delay': request.http_config.request_delay
            }
        
        # ジョブを作成
        job_name = f"Execute Requests - ID {request.request_id}"
        job_id = job_manager.create_job(
            name=job_name,
            request_id=request.request_id,
            total_requests=len(generated_requests),
            http_config=http_config_dict
        )
        
        # バックグラウンドでジョブを実行
        asyncio.create_task(
            job_manager.execute_requests_job(
                job_id=job_id,
                requests=generated_requests,
                http_config=http_config_dict
            )
        )
        
        return JobResponseModel(
            job_id=job_id,
            status="pending",
            message=f"ジョブが作成されました。ジョブID: {job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"実行エラー: {str(e)}")

@app.post("/api/execute-single-request", response_model=ExecuteSingleResponseModel)
async def execute_single_request(request: ExecuteSingleRequestModel, db: Session = Depends(get_db)):
    """
    個別のリクエストを実行するエンドポイント
    
    Args:
        request (ExecuteSingleRequestModel): 個別実行リクエスト
        db (Session): データベースセッション
        
    Returns:
        ExecuteSingleResponseModel: 実行結果
        
    Raises:
        HTTPException: リクエストが見つからない場合、または位置が無効な場合
    """
    # ファザーリクエストを取得
    fuzzer_request = db_manager.get_fuzzer_request_by_id(db, request.request_id)
    if not fuzzer_request:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")
    
    # 生成されたリクエストを取得
    generated_requests = []
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
        
        generated_requests.append(req_dict)
    
    # 位置の妥当性をチェック
    if request.position < 0 or request.position >= len(generated_requests):
        raise HTTPException(status_code=400, detail="無効なリクエスト位置です")
    
    # 指定された位置のリクエストのみを取得
    single_request = generated_requests[request.position]
    
    # HTTP設定を準備
    http_config = None
    if request.http_config:
        http_config = HTTPRequestConfig(
            timeout=request.http_config.timeout,
            follow_redirects=request.http_config.follow_redirects,
            verify_ssl=request.http_config.verify_ssl,
            scheme=request.http_config.scheme,
            base_url=request.http_config.base_url,
            headers=request.http_config.additional_headers
            # 単一リクエストなのでsequential_executionやrequest_delayは不要
        )
    
    try:
        # 単一リクエストを実行
        results = await RequestExecutor.execute_requests([single_request], http_config)
        
        return ExecuteSingleResponseModel(
            request_id=request.request_id,
            position=request.position,
            request=single_request,
            http_response=results[0].get("http_response") if results else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リクエスト実行エラー: {str(e)}")

@app.get("/api/jobs", response_model=JobListResponseModel)
async def get_jobs(current_user: User = Depends(get_current_active_user)):
    """
    ジョブ一覧を取得するエンドポイント
    
    Returns:
        JobListResponseModel: ジョブ一覧
    """
    jobs = job_manager.get_all_jobs()
    return JobListResponseModel(
        jobs=[job.to_dict() for job in jobs],
        total=len(jobs)
    )

@app.get("/api/jobs/statistics")
async def get_job_statistics(current_user: User = Depends(get_current_active_user)):
    """
    ジョブ統計情報を取得するエンドポイント
    """
    try:
        stats = job_manager.get_job_statistics()
        print(f"[DEBUG] /api/jobs/statistics response: {stats}")
        return stats
    except Exception as e:
        print(f"[ERROR] /api/jobs/statistics: {e}")
        # 空の統計情報を返す
        return {
            "total_jobs": 0,
            "pending_jobs": 0,
            "running_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "total_requests": 0,
            "avg_execution_time": 0
        }

@app.get("/api/jobs/{job_id}", response_model=JobSummaryResponseModel)
async def get_job_status(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    ジョブのサマリー情報を取得するエンドポイント
    
    Args:
        job_id (str): ジョブのID
        db: データベースセッション
        
    Returns:
        JobSummaryResponseModel: ジョブのサマリー情報
        
    Raises:
        HTTPException: ジョブが見つからない場合
    """
    # メモリ内のジョブを取得
    job = job_manager.get_job(job_id)
    if not job:
        # データベースからも確認
        db_job = db_manager.get_job_by_id(db, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
        
        # データベースのジョブをメモリ内のJobオブジェクトに変換
        progress_data = db_job.get_progress()
        # JobProgressの有効なフィールドのみを抽出
        valid_fields = ['total_requests', 'completed_requests', 'successful_requests', 
                       'failed_requests', 'current_request', 'start_time', 'end_time', 
                       'estimated_remaining_time']
        progress_init_data = {k: v for k, v in progress_data.items() if k in valid_fields}
        
        # 日時文字列をdatetimeオブジェクトに変換
        from datetime import datetime
        if 'start_time' in progress_init_data and isinstance(progress_init_data['start_time'], str):
            progress_init_data['start_time'] = datetime.fromisoformat(progress_init_data['start_time'])
        if 'end_time' in progress_init_data and isinstance(progress_init_data['end_time'], str):
            progress_init_data['end_time'] = datetime.fromisoformat(progress_init_data['end_time'])
            
        progress = job_manager.JobProgress(**progress_init_data)
        job = job_manager.Job(
            id=db_job.id,
            name=db_job.name,
            status=job_manager.JobStatus(db_job.status),
            progress=progress,
            created_at=db_job.created_at,
            updated_at=db_job.updated_at,
            request_id=db_job.fuzzer_request_id,
            http_config=db_job.http_config,
            results=[],
            error_message=db_job.error_message
        )
    
    return JobSummaryResponseModel(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress.to_dict(),
        error_message=job.error_message,
        created_at=job.created_at.isoformat() if job.created_at else "",
        updated_at=job.updated_at.isoformat() if job.updated_at else "",
        request_id=job.request_id
    )

@app.post("/api/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    """
    ジョブを停止するエンドポイント
    
    Args:
        job_id (str): ジョブのID
        
    Returns:
        Dict[str, str]: 停止結果
        
    Raises:
        HTTPException: ジョブが見つからない場合
    """
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    return {"message": f"ジョブ {job_id} を停止しました"}

@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """
    ジョブを再開するエンドポイント
    
    Args:
        job_id (str): ジョブのID
        
    Returns:
        Dict[str, str]: 再開結果
        
    Raises:
        HTTPException: ジョブが見つからない、または再開できない場合
    """
    success = job_manager.resume_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="ジョブが見つからないか、再開できない状態です")
    
    return {"message": f"ジョブ {job_id} を再開しました"}

@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    ジョブをキャンセルするエンドポイント（下位互換性のため保持）
    
    Args:
        job_id (str): ジョブのID
        
    Returns:
        Dict[str, str]: キャンセル結果
        
    Raises:
        HTTPException: ジョブが見つからない場合
    """
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    return {"message": f"ジョブ {job_id} をキャンセルしました"}

@app.delete("/api/jobs/{job_id}/delete")
async def delete_job(job_id: str):
    """
    ジョブを削除するエンドポイント
    
    Args:
        job_id (str): ジョブのID
        
    Returns:
        Dict[str, str]: 削除結果
        
    Raises:
        HTTPException: ジョブが見つからない場合
    """
    success = job_manager.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    return {"message": f"ジョブ {job_id} を削除しました"}

@app.post("/api/jobs/cleanup")
async def cleanup_jobs(max_age_hours: int = 24):
    """
    古いジョブをクリーンアップ
    
    Args:
        max_age_hours (int): クリーンアップする最大時間（時間）
        
    Returns:
        Dict[str, Any]: クリーンアップ結果
    """
    try:
        cleaned_count = job_manager.cleanup_old_jobs(max_age_hours)
        return {
            "message": f"{cleaned_count}個の古いジョブをクリーンアップしました",
            "cleaned_jobs": cleaned_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"クリーンアップエラー: {str(e)}")

# 古い統合分析APIは削除済み - 新しい3つの専用APIに置き換えられました

# 認証関連のPydanticモデル
class UserRegisterRequest(BaseModel):
    """
    ユーザー登録リクエストの定義
    
    Attributes:
        username (str): ユーザー名
        email (str): メールアドレス
        password (str): パスワード
    """
    username: str
    email: str
    password: str

class UserLoginRequest(BaseModel):
    """
    ユーザーログインリクエストの定義
    
    Attributes:
        username (str): ユーザー名
        password (str): パスワード
    """
    username: str
    password: str

class UserResponse(BaseModel):
    """
    ユーザー情報レスポンスの定義
    
    Attributes:
        id (int): ユーザーID
        username (str): ユーザー名
        email (str): メールアドレス
        is_active (bool): アクティブフラグ
        created_at (str): 作成日時
        updated_at (str): 更新日時
    """
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    updated_at: str

class Token(BaseModel):
    """
    トークンレスポンスの定義
    
    Attributes:
        access_token (str): アクセストークン
        token_type (str): トークンタイプ
        user (UserResponse): ユーザー情報
    """
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    """
    トークンデータの定義
    
    Attributes:
        user_id (Optional[int]): ユーザーID
    """
    user_id: Optional[int] = None

class FuzzerEngine:
    def __init__(self):
        pass
    
    def sniper_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Sniper攻撃: 各ペイロードを各位置に順番に配置
        
        Sniper攻撃では固定のプレースホルダ <<>> を使用し、同じプレースホルダが
        複数ある場合に、各出現位置を順番にペイロードで置換します。
        置換されなかったプレースホルダは空文字列で置換されます。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): 使用されない（Sniper攻撃では固定プレースホルダを使用）
            payload_sets (List[PayloadSet]): ペイロードセットのリスト（最初のセットのみ使用）
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットが提供されていない場合
        """
        if not payload_sets:
            raise ValueError("少なくとも1つのペイロードセットが必要です")
        
        payload_set = payload_sets[0]
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template.replace("<<>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payload": "",
            "position": 0
        })
        
        # Sniper攻撃では固定のプレースホルダ <<>> を使用
        placeholder_pattern = "<<>>"
        placeholder_count = template.count(placeholder_pattern)
        
        for payload in payload_set.payloads:
            for position in range(placeholder_count):
                result = template
                # 指定された位置のプレースホルダのみを置換
                current_pos = 0
                start = 0
                while current_pos <= position:
                    pos = result.find(placeholder_pattern, start)
                    if pos == -1:
                        break
                    if current_pos == position:
                        # この位置のプレースホルダを置換
                        result = result[:pos] + payload + result[pos + len(placeholder_pattern):]
                        break
                    start = pos + 1
                    current_pos += 1
                
                # 置換されていないプレースホルダを空文字列で置換
                result = result.replace(placeholder_pattern, "")
                
                requests.append({
                    "request": result,
                    "placeholder": "<<>>",
                    "payload": payload,
                    "position": position + 1
                })
        
        return requests
    
    def battering_ram_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Battering Ram攻撃: 同じペイロードを全ての位置に同時に配置
        
        Battering Ram攻撃では、1つのペイロードセットの各ペイロードを
        全てのプレースホルダに同時に配置します。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            payload_sets (List[PayloadSet]): ペイロードセットのリスト（最初のセットのみ使用）
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットが提供されていない場合
        """
        if not payload_sets:
            raise ValueError("少なくとも1つのペイロードセットが必要です")
        
        payload_set = payload_sets[0]
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template
        for placeholder in placeholders:
            original_template = original_template.replace(f"<<{placeholder}>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payload": "",
            "applied_to": []
        })
        
        for payload in payload_set.payloads:
            result = template
            for placeholder in placeholders:
                result = result.replace(f"<<{placeholder}>>", payload)
            requests.append({
                "request": result,
                "payload": payload,
                "applied_to": placeholders
            })
        
        return requests
    
    def pitchfork_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Pitchfork攻撃: 各位置に異なるペイロードセットを使用し、同時に配置
        
        Pitchfork攻撃では、各プレースホルダに対応するペイロードセットがあり、
        各セットの同じインデックスのペイロードを同時に配置します。
        最小のペイロードセットのサイズまで処理します。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            payload_sets (List[PayloadSet]): ペイロードセットのリスト
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットの数がプレースホルダの数と一致しない場合
        """
        if len(payload_sets) != len(placeholders):
            raise ValueError("ペイロードセットの数はプレースホルダの数と一致する必要があります")
        
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template
        for placeholder in placeholders:
            original_template = original_template.replace(f"<<{placeholder}>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payloads": {}
        })
        
        # 最小のペイロードセットのサイズを取得
        min_payload_count = min(len(ps.payloads) for ps in payload_sets)
        
        for i in range(min_payload_count):
            result = template
            placeholder_payload_map = {}
            
            for j, (placeholder, payload_set) in enumerate(zip(placeholders, payload_sets)):
                payload = payload_set.payloads[i]
                result = result.replace(f"<<{placeholder}>>", payload)
                placeholder_payload_map[placeholder] = payload
            
            requests.append({
                "request": result,
                "payloads": placeholder_payload_map
            })
        
        return requests
    
    def cluster_bomb_attack(self, template: str, placeholders: List[str], payload_sets: List[PayloadSet]) -> List[Dict[str, str]]:
        """
        Cluster Bomb攻撃: 全てのペイロードの組み合わせをテスト
        
        Cluster Bomb攻撃では、各プレースホルダに対応するペイロードセットがあり、
        全てのペイロードの組み合わせをテストします。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            placeholders (List[str]): プレースホルダ名のリスト
            payload_sets (List[PayloadSet]): ペイロードセットのリスト
            
        Returns:
            List[Dict[str, str]]: 生成されたリクエストのリスト
            
        Raises:
            ValueError: ペイロードセットの数がプレースホルダの数と一致しない場合
        """
        if len(payload_sets) != len(placeholders):
            raise ValueError("ペイロードセットの数はプレースホルダの数と一致する必要があります")
        
        requests = []
        
        # オリジナルのテンプレート（プレースホルダを空文字列で置換）を最初に追加
        original_template = template
        for placeholder in placeholders:
            original_template = original_template.replace(f"<<{placeholder}>>", "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payloads": {}
        })
        
        # 全てのペイロードの組み合わせを生成
        payload_combinations = list(itertools.product(*[ps.payloads for ps in payload_sets]))
        
        for combination in payload_combinations:
            result = template
            placeholder_payload_map = {}
            
            for placeholder, payload in zip(placeholders, combination):
                result = result.replace(f"<<{placeholder}>>", payload)
                placeholder_payload_map[placeholder] = payload
            
            requests.append({
                "request": result,
                "payloads": placeholder_payload_map
            })
        
        return requests

    def mutation_attack(self, template: str, mutations: List[Mutation]) -> List[Dict[str, Any]]:
        """
        変異ベース攻撃: 各トークンに対して指定された変異を適用
        
        変異ベース攻撃では、各トークンに対して辞書的な値やrepeat機能付きの値を
        適用してリクエストを生成します。
        
        Args:
            template (str): プレースホルダを含むテンプレート文字列
            mutations (List[Mutation]): 変異のリスト
            
        Returns:
            List[Dict[str, Any]]: 生成されたリクエストのリスト
        """
        requests = []
        
        # オリジナルのテンプレート（全てのトークンを空文字列で置換）を最初に追加
        original_template = template
        for mutation in mutations:
            original_template = original_template.replace(mutation.token, "")
        requests.append({
            "request": original_template,
            "placeholder": "original",
            "payload": "",
            "position": 0
        })
        
        # 各変異に対して処理
        for mutation in mutations:
            # 変異値を処理してペイロードリストを生成
            payloads = process_mutation_values(mutation.values)
            
            # 各ペイロードに対してリクエストを生成
            for i, payload in enumerate(payloads):
                result = template.replace(mutation.token, payload)
                requests.append({
                    "request": result,
                    "placeholder": mutation.token,
                    "payload": payload,
                    "position": i + 1,
                    "strategy": mutation.strategy
                })
        
        return requests

fuzzer = FuzzerEngine()

async def execute_single_request_async(request_data: Dict[str, Any], http_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    単一リクエストを非同期で実行するヘルパー関数
    
    Args:
        request_data (Dict[str, Any]): リクエストデータ
        http_config (Optional[Dict[str, Any]]): HTTP設定
        
    Returns:
        Dict[str, Any]: 実行結果
    """
    try:
        # HTTP設定を適用
        config = HTTPRequestConfig()
        if http_config:
            config.timeout = http_config.get('timeout', 30)
            config.follow_redirects = http_config.get('follow_redirects', True)
            config.verify_ssl = http_config.get('verify_ssl', False)
            config.scheme = http_config.get('scheme', 'http')
            config.base_url = http_config.get('base_url', 'localhost:8000')
            config.additional_headers = http_config.get('additional_headers')
        
        # リクエスト実行
        executor = RequestExecutor(config)
        result = await executor.execute_request(request_data['request'])
        
        return {
            'request': request_data,
            'http_response': result,
            'success': True
        }
    except Exception as e:
        return {
            'request': request_data,
            'error': str(e),
            'success': False
        }

@app.post("/api/replace-placeholders", response_model=PlaceholderResponse)
async def replace_placeholders(request: PlaceholderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    プレースホルダ置換APIエンドポイント
    
    指定された攻撃戦略に基づいてプレースホルダをペイロードで置換し、
    生成されたリクエストのリストを返します。また、リクエストと生成された
    リクエストをデータベースに永続化します。
    
    Args:
        request (PlaceholderRequest): 置換リクエスト
        db (Session): データベースセッション
        
    Returns:
        PlaceholderResponse: 攻撃戦略名、総リクエスト数、リクエストリスト、リクエストIDを含むレスポンス
        
    Raises:
        HTTPException: 無効な攻撃戦略が指定された場合
    """
    try:
        # 攻撃戦略に基づいて適切なメソッドを呼び出し
        if request.strategy == AttackStrategy.SNIPER:
            requests = fuzzer.sniper_attack(request.template, request.placeholders, request.payload_sets)
        elif request.strategy == AttackStrategy.BATTERING_RAM:
            requests = fuzzer.battering_ram_attack(request.template, request.placeholders, request.payload_sets)
        elif request.strategy == AttackStrategy.PITCHFORK:
            requests = fuzzer.pitchfork_attack(request.template, request.placeholders, request.payload_sets)
        elif request.strategy == AttackStrategy.CLUSTER_BOMB:
            requests = fuzzer.cluster_bomb_attack(request.template, request.placeholders, request.payload_sets)
        else:
            raise HTTPException(status_code=400, detail=f"無効な攻撃戦略: {request.strategy}")
        
        # ペイロードセットを辞書形式に変換
        payload_sets_dict = [{"name": ps.name, "payloads": ps.payloads} for ps in request.payload_sets]
        
        # データベースに保存
        fuzzer_request = db_manager.save_fuzzer_request(
            db=db,
            template=request.template,
            placeholders=request.placeholders,
            strategy=request.strategy.value,
            payload_sets=payload_sets_dict,
            generated_requests=requests
        )
        
        return PlaceholderResponse(
            strategy=request.strategy.value,
            total_requests=len(requests),
            requests=requests,
            request_id=fuzzer_request.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部エラー: {str(e)}")

@app.post("/api/mutations", response_model=PlaceholderResponse)
async def apply_mutations(request: MutationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    変異ベースのプレースホルダ置換を実行
    
    各トークンに対して指定された変異（辞書的な値やrepeat機能付きの値）を適用して
    リクエストを生成します。
    
    Args:
        request (MutationRequest): 変異リクエスト
        db (Session): データベースセッション
        
    Returns:
        PlaceholderResponse: 生成されたリクエストの情報
    """
    try:
        # 変異ベース攻撃を実行
        requests = fuzzer.mutation_attack(request.template, request.mutations)
        
        # データベースに保存
        fuzzer_request = FuzzerRequest(
            template=request.template,
            strategy="mutation",
            total_requests=len(requests)
        )
        fuzzer_request.set_placeholders([mutation.token for mutation in request.mutations])
        fuzzer_request.set_payload_sets([])  # mutationsではpayload_setsは使用しない
        db.add(fuzzer_request)
        db.commit()
        db.refresh(fuzzer_request)
        
        # 生成されたリクエストをデータベースに保存
        for i, req in enumerate(requests):
            generated_request = GeneratedRequest(
                fuzzer_request_id=fuzzer_request.id,
                request_number=i + 1,
                request_content=req["request"],
                placeholder=req.get("placeholder", ""),
                payload=req.get("payload", ""),
                position=req.get("position", 0)
            )
            db.add(generated_request)
        db.commit()
        
        return PlaceholderResponse(
            strategy="mutation",
            total_requests=len(requests),
            requests=requests,
            request_id=fuzzer_request.id
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/intuitive", response_model=PlaceholderResponse)
async def intuitive_replace_placeholders(request: IntuitiveRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    直感的なプレースホルダ置換API
    
    placeholdersを使わずに、payload_setsのtokenから自動的にプレースホルダを抽出します。
    """
    try:
        # payload_setsからプレースホルダを自動抽出（<<>>を除去）
        placeholders = []
        for payload_set in request.payload_sets:
            # <<username>> -> username に変換
            placeholder_name = payload_set.token.strip("<>")
            placeholders.append(placeholder_name)
        
        # payload_setsを従来の形式に変換
        converted_payload_sets = []
        for payload_set in request.payload_sets:
            # valuesを処理してペイロードリストを生成
            processed_payloads = process_mutation_values(payload_set.values)
            
            # プレースホルダ名をnameとして使用
            placeholder_name = payload_set.token.strip("<>")
            converted_payload_sets.append(PayloadSet(
                name=placeholder_name,
                payloads=processed_payloads
            ))
        
        # 従来のリクエスト形式に変換
        placeholder_request = PlaceholderRequest(
            template=request.template,
            placeholders=placeholders,
            strategy=request.strategy,
            payload_sets=converted_payload_sets
        )
        
        # 既存の処理を再利用
        return await replace_placeholders(placeholder_request, db)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"リクエストの処理に失敗しました: {str(e)}")

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """
    テスト用HTMLページを提供するエンドポイント
    
    APIの動作をテストするためのWebインターフェースを提供します。
    
    Returns:
        HTMLResponse: テスト用HTMLページ
    """
    try:
        with open("web_test.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="テストページが見つかりません")

@app.get("/api/test-response")
async def test_response():
    """
    テスト用レスポンスエンドポイント
    
    個別リクエスト実行のテスト用に使用します。
    
    Returns:
        Dict[str, Any]: テストレスポンス
    """
    return {
        "message": "テストレスポンスです",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": {
            "id": 123,
            "name": "テストデータ",
            "status": "success"
        }
    }

@app.get("/history-page", response_class=HTMLResponse)
async def history_page():
    """
    履歴表示用HTMLページを提供するエンドポイント
    
    ファザーリクエストの履歴と統計情報を表示するWebインターフェースを提供します。
    
    Returns:
        HTMLResponse: 履歴表示用HTMLページ
    """
    try:
        with open("history.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="履歴ページが見つかりません")

@app.get("/api/jobs/{job_id}/results", response_model=JobResultsResponseModel)
async def get_job_results(job_id: str, db: Session = Depends(get_db), limit: int = 50, offset: int = 0, current_user: User = Depends(get_current_active_user)):
    """
    ジョブの結果リストを取得するエンドポイント（ページネーション付き）
    
    Args:
        job_id (str): ジョブのID
        db: データベースセッション
        limit (int): 取得制限数（デフォルト: 50）
        offset (int): オフセット（デフォルト: 0）
        
    Returns:
        JobResultsResponseModel: ジョブの結果リスト
        
    Raises:
        HTTPException: ジョブが見つからない場合
    """
    # ジョブの存在確認
    job = job_manager.get_job(job_id)
    if not job:
        db_job = db_manager.get_job_by_id(db, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    try:
        # データベースから結果を取得（ページネーション）
        db_results = db.query(DBJobResult).filter(DBJobResult.job_id == job_id).order_by(DBJobResult.request_number).offset(offset).limit(limit).all()
        
        # 総数を取得
        total_count = db.query(DBJobResult).filter(DBJobResult.job_id == job_id).count()
        
        # 結果サマリーを作成
        results = []
        for db_result in db_results:
            http_response = db_result.get_http_response()
            status_code = http_response.get('status_code') if http_response else None
            url = http_response.get('url') if http_response else None
            
            result_summary = JobResultSummaryModel(
                request_number=db_result.request_number,
                placeholder=db_result.placeholder,
                payload=db_result.payload,
                position=db_result.position,
                status_code=status_code,
                success=db_result.success,
                error_message=db_result.error_message,
                elapsed_time=db_result.elapsed_time,
                url=url
            )
            results.append(result_summary)
        
        has_more = offset + limit < total_count
        
        return JobResultsResponseModel(
            job_id=job_id,
            total_results=total_count,
            results=results,
            limit=limit,
            offset=offset,
            has_more=has_more
        )
        
    except Exception as e:
        print(f"結果取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"結果取得エラー: {str(e)}")

@app.get("/api/jobs/{job_id}/results/{result_id}", response_model=JobResultDetailResponseModel)
async def get_job_result_detail(job_id: str, result_id: int, db: Session = Depends(get_db)):
    """
    ジョブの特定の結果詳細を取得するエンドポイント
    
    Args:
        job_id (str): ジョブのID
        result_id (int): 結果のID（request_number）
        db: データベースセッション
        
    Returns:
        JobResultDetailResponseModel: 結果の詳細
        
    Raises:
        HTTPException: ジョブまたは結果が見つからない場合
    """
    # ジョブの存在確認
    job = job_manager.get_job(job_id)
    if not job:
        db_job = db_manager.get_job_by_id(db, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    try:
        # データベースから特定の結果を取得
        db_result = db.query(DBJobResult).filter(
            DBJobResult.job_id == job_id,
            DBJobResult.request_number == result_id
        ).first()
        
        if not db_result:
            raise HTTPException(status_code=404, detail="結果が見つかりません")
        
        # 結果詳細を作成
        result_detail = JobResultDetailResponseModel(
            job_id=job_id,
            request_number=db_result.request_number,
            request_content=db_result.request_content,
            placeholder=db_result.placeholder,
            payload=db_result.payload,
            position=db_result.position,
            http_response=db_result.get_http_response(),
            success=db_result.success,
            error_message=db_result.error_message,
            elapsed_time=db_result.elapsed_time,
            created_at=db_result.created_at.isoformat() if db_result.created_at else ""
        )
        
        return result_detail
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"結果詳細取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"結果詳細取得エラー: {str(e)}")

# 古いVulnerabilityAnalyzerクラスは削除済み - vulnerability_analysis.pyの個別分析エンジンで置き換えられました
# class VulnerabilityAnalyzer:

# 認証関連エンドポイント
@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    新しいユーザーを登録するエンドポイント
    
    Args:
        request: ユーザー登録リクエスト
        db: データベースセッション
        
    Returns:
        UserResponse: 作成されたユーザー情報
        
    Raises:
        HTTPException: ユーザー名またはメールが既に存在する場合
    """
    # ユーザー名の重複チェック
    existing_user = auth_manager.get_user_by_username(db, request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="このユーザー名は既に使用されています")
    
    # メールアドレスの重複チェック
    existing_email = auth_manager.get_user_by_email(db, request.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")
    
    # ユーザー作成
    user = auth_manager.create_user(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password
    )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else ""
    )

@app.post("/api/auth/login", response_model=Token)
async def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    ユーザーログインエンドポイント
    
    Args:
        request: ログインリクエスト
        db: データベースセッション
        
    Returns:
        Token: JWTトークンとユーザー情報
        
    Raises:
        HTTPException: 認証に失敗した場合
    """
    # ユーザー認証
    user = auth_manager.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="アカウントが無効です")
    
    # JWTトークン作成
    access_token = auth_manager.create_access_token(data={"sub": str(user.id)})
    
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else ""
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    現在のユーザー情報を取得するエンドポイント
    
    Args:
        current_user: 現在のユーザー（JWT認証）
        
    Returns:
        UserResponse: ユーザー情報
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
        updated_at=current_user.updated_at.isoformat() if current_user.updated_at else ""
    )

# エラーパターン検出用モデル - vulnerability_analysis.pyに移動済み
# class ErrorPatternConfigModel(BaseModel):

# class ErrorPatternFinding(BaseModel):

# class ErrorPatternAnalysisResult(BaseModel):

# ペイロード反射検出用モデル - vulnerability_analysis.pyに移動済み
# class PayloadReflectionConfigModel(BaseModel):

# class PayloadReflectionFinding(BaseModel):

# class PayloadReflectionAnalysisResult(BaseModel):

# 時間遅延検出用モデル - vulnerability_analysis.pyに移動済み
# class TimeDelayConfigModel(BaseModel):

# class TimeDelayFinding(BaseModel):

# class TimeDelayAnalysisResult(BaseModel):

# 3つの専用脆弱性分析APIエンドポイント

@app.post("/api/jobs/{job_id}/analyze/error-patterns", response_model=ErrorPatternAnalysisResult)
async def analyze_error_patterns(job_id: str, 
                                config: Optional[ErrorPatternConfigModel] = None,
                                db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_active_user)):
    """
    エラーパターン検出分析
    
    Args:
        job_id (str): 分析対象のジョブID
        config: エラーパターン検出設定
        db: データベースセッション
        current_user: 現在のユーザー
        
    Returns:
        ErrorPatternAnalysisResult: エラーパターン分析結果
    """
    # ジョブの存在確認
    job = job_manager.get_job(job_id)
    if not job:
        db_job = db_manager.get_job_by_id(db, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    try:
        # エラーパターン分析を実行
        if config:
            result = error_pattern_analyzer.analyze_job_errors(
                job_id, db, config.error_patterns, config.case_sensitive
            )
        else:
            result = error_pattern_analyzer.analyze_job_errors(job_id, db)
        
        return result
        
    except Exception as e:
        print(f"エラーパターン分析エラー: {e}")
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")

@app.get("/api/jobs/{job_id}/analyze/error-patterns", response_model=ErrorPatternAnalysisResult)
async def analyze_error_patterns_get(job_id: str,
                                   error_patterns: Optional[str] = None,
                                   case_sensitive: bool = False,
                                   db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_active_user)):
    """
    エラーパターン検出分析（GETバージョン）
    
    Args:
        job_id (str): 分析対象のジョブID
        error_patterns: カンマ区切りのエラーパターン
        case_sensitive: 大文字小文字を区別するかどうか
        db: データベースセッション
        current_user: 現在のユーザー
        
    Returns:
        ErrorPatternAnalysisResult: エラーパターン分析結果
    """
    config = ErrorPatternConfigModel(
        error_patterns=error_patterns.split(',') if error_patterns else None,
        case_sensitive=case_sensitive
    )
    
    return await analyze_error_patterns(job_id, config, db, current_user)

@app.post("/api/jobs/{job_id}/analyze/payload-reflection", response_model=PayloadReflectionAnalysisResult)
async def analyze_payload_reflection(job_id: str,
                                   config: Optional[PayloadReflectionConfigModel] = None,
                                   db: Session = Depends(get_db),
                                   current_user: User = Depends(get_current_active_user)):
    """
    ペイロード反射検出分析
    
    Args:
        job_id (str): 分析対象のジョブID
        config: ペイロード反射検出設定
        db: データベースセッション
        current_user: 現在のユーザー
        
    Returns:
        PayloadReflectionAnalysisResult: ペイロード反射分析結果
    """
    # ジョブの存在確認
    job = job_manager.get_job(job_id)
    if not job:
        db_job = db_manager.get_job_by_id(db, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    try:
        # ペイロード反射分析を実行
        if config:
            result = payload_reflection_analyzer.analyze_job_reflections(
                job_id, db, 
                config.check_html_encoding,
                config.check_url_encoding,
                config.check_js_encoding,
                config.minimum_payload_length
            )
        else:
            result = payload_reflection_analyzer.analyze_job_reflections(job_id, db)
        
        return result
        
    except Exception as e:
        print(f"ペイロード反射分析エラー: {e}")
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")

@app.get("/api/jobs/{job_id}/analyze/payload-reflection", response_model=PayloadReflectionAnalysisResult)
async def analyze_payload_reflection_get(job_id: str,
                                       check_html_encoding: bool = True,
                                       check_url_encoding: bool = True,
                                       check_js_encoding: bool = True,
                                       minimum_payload_length: int = 3,
                                       db: Session = Depends(get_db),
                                       current_user: User = Depends(get_current_active_user)):
    """
    ペイロード反射検出分析（GETバージョン）
    
    Args:
        job_id (str): 分析対象のジョブID
        check_html_encoding: HTMLエンコーディングをチェックするかどうか
        check_url_encoding: URLエンコーディングをチェックするかどうか
        check_js_encoding: JavaScriptエンコーディングをチェックするかどうか
        minimum_payload_length: 検出対象とする最小ペイロード長
        db: データベースセッション
        current_user: 現在のユーザー
        
    Returns:
        PayloadReflectionAnalysisResult: ペイロード反射分析結果
    """
    config = PayloadReflectionConfigModel(
        check_html_encoding=check_html_encoding,
        check_url_encoding=check_url_encoding,
        check_js_encoding=check_js_encoding,
        minimum_payload_length=minimum_payload_length
    )
    
    return await analyze_payload_reflection(job_id, config, db, current_user)

@app.post("/api/jobs/{job_id}/analyze/time-delay", response_model=TimeDelayAnalysisResult)
async def analyze_time_delay(job_id: str,
                           config: Optional[TimeDelayConfigModel] = None,
                           db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_active_user)):
    """
    時間遅延検出分析
    
    Args:
        job_id (str): 分析対象のジョブID
        config: 時間遅延検出設定
        db: データベースセッション
        current_user: 現在のユーザー
        
    Returns:
        TimeDelayAnalysisResult: 時間遅延分析結果
    """
    # ジョブの存在確認
    job = job_manager.get_job(job_id)
    if not job:
        db_job = db_manager.get_job_by_id(db, job_id)
        if not db_job:
            raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    try:
        # 時間遅延分析を実行
        if config:
            result = time_delay_analyzer.analyze_job_time_delays(
                job_id, db,
                config.time_threshold,
                config.baseline_method,
                config.consider_payload_type
            )
        else:
            result = time_delay_analyzer.analyze_job_time_delays(job_id, db)
        
        return result
        
    except Exception as e:
        print(f"時間遅延分析エラー: {e}")
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")

@app.get("/api/jobs/{job_id}/analyze/time-delay", response_model=TimeDelayAnalysisResult)
async def analyze_time_delay_get(job_id: str,
                               time_threshold: float = 2.0,
                               baseline_method: str = "first_request",
                               consider_payload_type: bool = True,
                               db: Session = Depends(get_db),
                               current_user: User = Depends(get_current_active_user)):
    """
    時間遅延検出分析（GETバージョン）
    
    Args:
        job_id (str): 分析対象のジョブID
        time_threshold: 遅延として判定する閾値（秒）
        baseline_method: ベースライン計算方法
        consider_payload_type: ペイロードタイプを考慮するかどうか
        db: データベースセッション
        current_user: 現在のユーザー
        
    Returns:
        TimeDelayAnalysisResult: 時間遅延分析結果
    """
    config = TimeDelayConfigModel(
        time_threshold=time_threshold,
        baseline_method=baseline_method,
        consider_payload_type=consider_payload_type
    )
    
    return await analyze_time_delay(job_id, config, db, current_user)

if __name__ == "__main__":
    import os
    
    # データベーステーブルを作成
    db_manager.create_tables()
    
    # 開発サーバーを起動
    # host="0.0.0.0" で全てのインターフェースからアクセス可能
    # PORTは環境変数から取得（Renderで自動設定される）
    port = int(os.getenv("PORT", 8000))
    
    # 本番環境では reload=False を設定
    is_production = os.getenv("ENVIRONMENT") == "production"
    uvicorn.run(app, host="0.0.0.0", port=port, reload=not is_production) 