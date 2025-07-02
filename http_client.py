"""
HTTPリクエスト送信機能

生成されたリクエスト文字列を使って実際にHTTPリクエストを送信する機能を提供します。
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import re
from urllib.parse import urlparse
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HTTPRequestConfig:
    """HTTPリクエスト設定"""
    method: str = "GET"
    headers: Dict[str, str] = None
    timeout: int = 30
    follow_redirects: bool = True
    verify_ssl: bool = True
    scheme: str = "http"  # http または https
    base_url: str = "localhost:8000"  # ベースURL（スキームなし）

@dataclass
class HTTPResponse:
    """HTTPレスポンス情報"""
    status_code: int
    headers: Dict[str, str]
    body: str
    url: str
    elapsed_time: float
    error: Optional[str] = None

class HTTPClient:
    """HTTPリクエスト送信クライアント"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーの開始"""
        connector = aiohttp.TCPConnector(verify_ssl=False)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了"""
        if self.session:
            await self.session.close()
    
    def parse_http_request(self, request_text: str) -> Dict[str, Any]:
        """
        HTTPリクエスト文字列を厳密に解析して、URL、メソッド、ヘッダー、ボディを抽出
        
        Args:
            request_text (str): HTTPリクエスト文字列
            
        Returns:
            Dict[str, Any]: 解析されたリクエスト情報
        """
        lines = request_text.strip().split('\n')
        if not lines:
            raise ValueError("空のリクエスト文字列です")
        
        # リクエストラインを解析
        request_line = lines[0].strip()
        parts = request_line.split(' ')
        if len(parts) < 2:
            raise ValueError("無効なリクエストラインです")
        
        method = parts[0].upper()
        url = parts[1]
        version = parts[2] if len(parts) > 2 else "HTTP/1.1"
        
        # ヘッダーを解析（複数行ヘッダーに対応）
        headers = {}
        body_start = 0
        i = 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:  # 空行がボディの開始
                body_start = i + 1
                break
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 複数行ヘッダーの処理
                j = i + 1
                while j < len(lines) and lines[j].startswith((' ', '\t')):
                    value += ' ' + lines[j].strip()
                    j += 1
                
                headers[key] = value
                i = j
            else:
                i += 1
        
        # ボディを抽出
        body_lines = lines[body_start:] if body_start < len(lines) else []
        body = '\n'.join(body_lines)
        
        # Content-Lengthヘッダーがある場合、ボディの長さを検証
        if 'Content-Length' in headers:
            try:
                expected_length = int(headers['Content-Length'])
                actual_length = len(body.encode('utf-8'))
                if actual_length != expected_length:
                    logger.warning(f"Content-Length不一致: 期待値={expected_length}, 実際={actual_length}")
            except ValueError:
                logger.warning("無効なContent-Lengthヘッダー")
        
        return {
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
            "version": version
        }
    
    async def send_request(self, request_text: str, config: HTTPRequestConfig = None) -> HTTPResponse:
        """
        リクエスト文字列を厳密に送信
        
        Args:
            request_text (str): HTTPリクエスト文字列
            config (HTTPRequestConfig): リクエスト設定
            
        Returns:
            HTTPResponse: レスポンス情報
        """
        if config is None:
            config = HTTPRequestConfig()
        
        try:
            # リクエスト文字列を解析
            parsed = self.parse_http_request(request_text)
            
            # URLの処理
            request_url = parsed["url"]
            
            # Hostヘッダーからドメインを取得
            host_header = parsed["headers"].get('Host', '')
            if not host_header:
                # Hostヘッダーがない場合は設定されたベースURLを使用
                host_header = config.base_url
            
            # リクエスト1行目のパス部分を抽出
            if request_url.startswith(('http://', 'https://')):
                # 完全なURLの場合はパス部分のみを抽出
                from urllib.parse import urlparse
                parsed_url = urlparse(request_url)
                path = parsed_url.path
                if parsed_url.query:
                    path += '?' + parsed_url.query
                if parsed_url.fragment:
                    path += '#' + parsed_url.fragment
            else:
                # 相対パスの場合はそのまま使用
                path = request_url
                if not path.startswith('/'):
                    path = '/' + path
            
            # 最終的なURLを構築
            url = f"{config.scheme}://{host_header}{path}"
            
            # ヘッダーの処理
            headers = {}
            
            # 設定されたヘッダーを追加
            if config.headers:
                headers.update(config.headers)
            
            # 解析されたヘッダーを追加（設定されたヘッダーを上書き）
            for key, value in parsed["headers"].items():
                # 一部のヘッダーは自動設定されるため除外
                if key.lower() not in ['host', 'content-length', 'connection']:
                    headers[key] = value
            
            # Hostヘッダーの処理（既に設定されている場合はそのまま使用）
            if 'Host' not in headers and 'host' not in headers:
                headers['Host'] = host_header
            
            # ボディの処理
            data = None
            if parsed["body"]:
                # Content-Typeヘッダーに基づいてボディを処理
                content_type = headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    try:
                        data = json.dumps(json.loads(parsed["body"]))
                    except json.JSONDecodeError:
                        data = parsed["body"]
                elif 'application/x-www-form-urlencoded' in content_type:
                    data = parsed["body"]
                else:
                    data = parsed["body"]
            
            # リクエストを送信
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.request(
                method=parsed["method"],
                url=url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=config.timeout),
                allow_redirects=config.follow_redirects
            ) as response:
                elapsed_time = asyncio.get_event_loop().time() - start_time
                
                # レスポンスボディを読み取り
                body = await response.text()
                
                return HTTPResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    body=body,
                    url=str(response.url),
                    elapsed_time=elapsed_time
                )
                
        except Exception as e:
            logger.error(f"リクエスト送信エラー: {e}")
            return HTTPResponse(
                status_code=0,
                headers={},
                body="",
                url="",
                elapsed_time=0,
                error=str(e)
            )
    
    async def send_multiple_requests(self, requests: List[str], config: HTTPRequestConfig = None) -> List[HTTPResponse]:
        """
        複数のリクエストを並行送信
        
        Args:
            requests (List[str]): リクエスト文字列のリスト
            config (HTTPRequestConfig): リクエスト設定
            
        Returns:
            List[HTTPResponse]: レスポンス情報のリスト
        """
        tasks = [self.send_request(req, config) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)

class RequestExecutor:
    """リクエスト実行クラス"""
    
    @staticmethod
    async def execute_requests(requests: List[Dict[str, Any]], config: HTTPRequestConfig = None) -> List[Dict[str, Any]]:
        """
        生成されたリクエストを実行
        
        Args:
            requests (List[Dict[str, Any]]): 生成されたリクエストのリスト
            config (HTTPRequestConfig): リクエスト設定
            
        Returns:
            List[Dict[str, Any]]: 実行結果のリスト
        """
        async with HTTPClient() as client:
            # リクエスト文字列を抽出
            request_texts = [req["request"] for req in requests]
            
            # リクエストを送信
            responses = await client.send_multiple_requests(request_texts, config)
            
            # 結果を結合
            results = []
            for i, (request, response) in enumerate(zip(requests, responses)):
                if isinstance(response, Exception):
                    # エラーの場合
                    result = {
                        **request,
                        "http_response": {
                            "status_code": 0,
                            "headers": {},
                            "body": "",
                            "url": "",
                            "elapsed_time": 0,
                            "error": str(response)
                        }
                    }
                else:
                    # 正常な場合
                    result = {
                        **request,
                        "http_response": {
                            "status_code": response.status_code,
                            "headers": response.headers,
                            "body": response.body,
                            "url": response.url,
                            "elapsed_time": response.elapsed_time,
                            "error": response.error
                        }
                    }
                results.append(result)
            
            return results 