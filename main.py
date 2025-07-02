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
from database import db_manager, FuzzerRequest, GeneratedRequest

# HTTPリクエスト送信関連のインポート
from http_client import RequestExecutor, HTTPRequestConfig
from job_manager import job_manager

app = FastAPI(
    title="プレースホルダ置換API",
    description="Burp Suite Intruderの4つの攻撃戦略を実装したAPI",
    version="1.0.0"
)

# APIルーターを作成
from fastapi import APIRouter

api_router = APIRouter(prefix="/api")

# データベーステーブルの作成
db_manager.create_tables()

# 静的ファイルを配信
app.mount("/static", StaticFiles(directory="."), name="static")

# APIルーターをアプリケーションに登録
app.include_router(api_router)

# データベースセッションの依存関係
def get_db():
    """データベースセッションを取得する依存関係"""
    db = db_manager.SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    """
    timeout: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = False
    scheme: str = "http"
    base_url: str = "localhost:8000"
    additional_headers: Optional[Dict[str, str]] = None

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

class JobListResponseModel(BaseModel):
    """
    ジョブ一覧レスポンスの定義
    
    Attributes:
        jobs (List[Dict[str, Any]]): ジョブのリスト
        total (int): 総ジョブ数
    """
    jobs: List[Dict[str, Any]]
    total: int

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
async def replace_placeholders(request: PlaceholderRequest, db: Session = Depends(get_db)):
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
async def apply_mutations(request: MutationRequest, db: Session = Depends(get_db)):
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
async def intuitive_replace_placeholders(request: IntuitiveRequest, db: Session = Depends(get_db)):
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
    ルートエンドポイント
    
    APIの基本情報と利用可能なエンドポイントを提供します。
    
    Returns:
        Dict[str, str]: APIの基本情報
    """
    return {
        "message": "プレースホルダ置換API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/replace-placeholders": "プレースホルダ置換API（データベースに保存）",
            "GET /api/history": "ファザーリクエストの履歴取得",
            "GET /api/history/{id}": "特定のファザーリクエストの詳細取得",
            "DELETE /api/history/{id}": "特定のファザーリクエストの削除",
            "GET /api/statistics": "データベース統計情報",
            "GET /test": "テスト用Webインターフェース",
            "GET /history-page": "履歴表示用Webインターフェース",
            "GET /docs": "APIドキュメント"
        },
        "strategies": [
            "sniper - 各ペイロードを各位置に順番に配置",
            "battering_ram - 同じペイロードを全ての位置に同時に配置",
            "pitchfork - 各位置に異なるペイロードセットを使用し、同時に配置",
            "cluster_bomb - 全てのペイロードの組み合わせをテスト"
        ],
        "database": {
            "type": "SQLite",
            "file": "fuzzer_requests.db",
            "features": [
                "リクエストと生成されたリクエストの永続化",
                "履歴の表示と管理",
                "統計情報の提供"
            ]
        }
    }

@app.get("/api/history", response_model=List[FuzzerRequestResponse])
async def get_history(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
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
async def get_request_detail(request_id: int, db: Session = Depends(get_db)):
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
async def get_statistics(db: Session = Depends(get_db)):
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
async def execute_requests(request: ExecuteRequestModel, db: Session = Depends(get_db)):
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
                'additional_headers': request.http_config.additional_headers
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
async def get_jobs():
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

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponseModel)
async def get_job_status(job_id: str):
    """
    ジョブの状態を取得するエンドポイント
    
    Args:
        job_id (str): ジョブのID
        
    Returns:
        JobStatusResponseModel: ジョブの状態
        
    Raises:
        HTTPException: ジョブが見つからない場合
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    return JobStatusResponseModel(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress.to_dict(),
        results=job.results,
        error_message=job.error_message
    )

@app.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    ジョブをキャンセルするエンドポイント
    
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
    古いジョブを削除するエンドポイント
    
    Args:
        max_age_hours (int): 最大保持時間（時間）
        
    Returns:
        Dict[str, Any]: クリーンアップ結果
    """
    deleted_count = job_manager.cleanup_old_jobs(max_age_hours)
    return {
        "message": f"{deleted_count} 個の古いジョブを削除しました",
        "deleted_count": deleted_count,
        "max_age_hours": max_age_hours
    }

@app.get("/api/jobs/statistics")
async def get_job_statistics():
    """
    ジョブ統計情報を取得するエンドポイント
    """
    stats = job_manager.get_job_statistics()
    return stats  # 404をraiseしない

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

if __name__ == "__main__":
    # 開発サーバーを起動
    # host="0.0.0.0" で全てのインターフェースからアクセス可能
    # port=8000 でポート8000を使用
    # reload=True でコード変更時に自動リロード
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 