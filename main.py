"""
プレースホルダ置換API - 4つの攻撃戦略を実装

このAPIは、Burp SuiteのIntruder機能で使用される4つの攻撃戦略を実装しています：
- Sniper: 1つのペイロードセットを各プレースホルダ位置に順番に配置
- Battering Ram: 1つのペイロードセットを全てのプレースホルダに同時に配置
- Pitchfork: 複数のペイロードセットを対応するプレースホルダに同時に配置
- Cluster Bomb: 全てのペイロードセットの組み合わせをテスト

プレースホルダ形式: <<プレースホルダ名>> または <<>> (Sniper攻撃用)
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union
import itertools
from enum import Enum
import uvicorn

app = FastAPI(
    title="プレースホルダ置換API",
    description="Burp Suite Intruderの4つの攻撃戦略を実装したAPI",
    version="1.0.0"
)

# 静的ファイルを配信
app.mount("/static", StaticFiles(directory="."), name="static")

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
    strategy: str
    total_requests: int
    requests: List[Dict[str, Any]]

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

fuzzer = FuzzerEngine()

@app.post("/replace-placeholders", response_model=PlaceholderResponse)
async def replace_placeholders(request: PlaceholderRequest):
    """
    プレースホルダ置換APIエンドポイント
    
    指定された攻撃戦略に基づいてプレースホルダをペイロードで置換し、
    生成されたリクエストのリストを返します。
    
    Args:
        request (PlaceholderRequest): 置換リクエスト
        
    Returns:
        PlaceholderResponse: 攻撃戦略名、総リクエスト数、リクエストリストを含むレスポンス
        
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
        
        return PlaceholderResponse(
            strategy=request.strategy.value,
            total_requests=len(requests),
            requests=requests
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部エラー: {str(e)}")

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
            "POST /replace-placeholders": "プレースホルダ置換API",
            "GET /test": "テスト用Webインターフェース",
            "GET /docs": "APIドキュメント"
        },
        "strategies": [
            "sniper - 各ペイロードを各位置に順番に配置",
            "battering_ram - 同じペイロードを全ての位置に同時に配置",
            "pitchfork - 各位置に異なるペイロードセットを使用し、同時に配置",
            "cluster_bomb - 全てのペイロードの組み合わせをテスト"
        ]
    }

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

if __name__ == "__main__":
    # 開発サーバーを起動
    # host="0.0.0.0" で全てのインターフェースからアクセス可能
    # port=8000 でポート8000を使用
    # reload=True でコード変更時に自動リロード
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 