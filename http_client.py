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
    sequential_execution: bool = False  # True: 同期実行（順次）, False: 並列実行
    request_delay: float = 0.0  # リクエスト間の待機時間（秒）

@dataclass
class HTTPResponse:
    """HTTPレスポンス情報"""
    status_code: int
    headers: Dict[str, str]
    body: str
    url: str
    elapsed_time: float
    error: Optional[str] = None
    actual_request: Optional[str] = None  # 実際に送信されたリクエスト

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
        
        # multipart/form-dataの場合は、改行文字も含めて正確に処理
        content_type = headers.get('Content-Type', '').lower()
        if 'multipart/form-data' in content_type:
            # 原文からボディ部分を抽出（改行を保持）
            # 最初にCRLF（\r\n\r\n）をチェック
            body_start_index = request_text.find('\r\n\r\n')
            if body_start_index != -1:
                body = request_text[body_start_index + 4:]
                logger.info("multipart/form-data: CRLF形式でボディを抽出")
            else:
                # 次にLF（\n\n）をチェック
                body_start_index = request_text.find('\n\n')
                if body_start_index != -1:
                    body = request_text[body_start_index + 2:]
                    # LFをCRLFに変換
                    body = body.replace('\n', '\r\n')
                    logger.info("multipart/form-data: LFをCRLFに変換")
                else:
                    # 最後の手段として行ベースで処理
                    body = '\r\n'.join(body_lines)
                    logger.info("multipart/form-data: 行ベースでCRLF形式に変換")
        
        # Content-Lengthヘッダーがある場合、ボディの長さを検証（参考情報のみ）
        if 'Content-Length' in headers:
            try:
                expected_length = int(headers['Content-Length'])
                actual_length = len(body.encode('utf-8'))
                if actual_length != expected_length:
                    logger.info(f"元のContent-Length: {expected_length}, 実際のボディサイズ: {actual_length}")
                    logger.info("Content-Lengthは送信時にライブラリが自動計算します")
                else:
                    logger.info(f"Content-Lengthが一致: {expected_length} bytes")
            except ValueError:
                logger.info("無効なContent-Lengthヘッダーを検出")
        
        return {
            "method": method,
            "url": url,
            "headers": headers,
            "body": body,
            "version": version
        }
    
    def calculate_content_length(self, body: str) -> int:
        """
        リクエストボディのContent-Lengthを計算
        
        Args:
            body (str): リクエストボディ
            
        Returns:
            int: Content-Lengthの値
        """
        return len(body.encode('utf-8'))
    
    def ensure_multipart_body_format(self, body: str, content_type: str) -> str:
        """
        multipart/form-dataのボディ形式を確認（修正は最小限）
        
        Args:
            body (str): リクエストボディ
            content_type (str): Content-Typeヘッダー
            
        Returns:
            str: ボディ（可能な限り元のまま）
        """
        if 'multipart/form-data' not in content_type.lower():
            return body
        
        # バウンダリーを抽出
        boundary_match = re.search(r'boundary=([^;]+)', content_type)
        if not boundary_match:
            logger.info("multipart/form-dataのバウンダリーが見つかりません - 元のボディをそのまま使用")
            return body
        
        boundary = boundary_match.group(1)
        final_boundary = f'--{boundary}--'
        
        logger.info(f"元のボディ長: {len(body.encode('utf-8'))} bytes")
        logger.info(f"バウンダリー: {boundary}")
        
        # 最終バウンダリーのチェック（修正は行わない）
        if body.rstrip().endswith(final_boundary):
            logger.info("最終バウンダリー: 正しい形式")
        elif body.rstrip().endswith(f'--{boundary}'):
            logger.info("最終バウンダリー: 通常のバウンダリーで終了")
        else:
            logger.info("最終バウンダリー: 不明な形式")
        
        # 改行文字の確認
        if '\r\n' in body:
            logger.info("改行文字: CRLF形式")
        elif '\n' in body:
            logger.info("改行文字: LF形式")
        
        # 元のボディをそのまま返す（aiohttpに処理を委ねる）
        logger.info("元のボディをそのまま使用します")
        return body
    
    def build_actual_request(self, method: str, url: str, headers: Dict[str, str], data: Optional[bytes]) -> str:
        """
        実際に送信されたリクエストを再構築
        
        Args:
            method (str): HTTPメソッド
            url (str): 完全なURL
            headers (Dict[str, str]): 送信されたヘッダー
            data (Optional[bytes]): 送信されたデータ
            
        Returns:
            str: 実際のHTTPリクエスト文字列
        """
        try:
            # URLからパス部分を抽出
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            path = parsed_url.path
            if parsed_url.query:
                path += '?' + parsed_url.query
            if parsed_url.fragment:
                path += '#' + parsed_url.fragment
            
            # リクエスト行を構築
            request_lines = [f"{method} {path} HTTP/1.1"]
            
            # ヘッダーを追加
            actual_headers = headers.copy()
            
            # Content-Lengthを実際のデータサイズで計算
            if data is not None:
                if isinstance(data, bytes):
                    actual_content_length = len(data)
                elif isinstance(data, str):
                    actual_content_length = len(data.encode('utf-8'))
                else:
                    actual_content_length = len(str(data).encode('utf-8'))
                actual_headers['Content-Length'] = str(actual_content_length)
                logger.info(f"実際のContent-Length: {actual_content_length}")
            
            # ヘッダーを追加
            for key, value in actual_headers.items():
                request_lines.append(f"{key}: {value}")
            
            # 空行を追加
            request_lines.append("")
            
            # ボディを追加（ある場合）
            if data is not None:
                # データの型に応じて処理
                if isinstance(data, bytes):
                    # バイト型データの場合
                    try:
                        body_str = data.decode('utf-8')
                        request_lines.append(body_str)
                    except UnicodeDecodeError:
                        # バイナリデータの場合
                        request_lines.append(f"[Binary data: {len(data)} bytes]")
                elif isinstance(data, str):
                    # 文字列型データの場合
                    request_lines.append(data)
                else:
                    # その他の型の場合
                    request_lines.append(str(data))
            
            # 改行で結合
            actual_request = '\n'.join(request_lines)
            
            logger.info(f"実際のリクエストを再構築: {len(actual_request)} characters")
            return actual_request
            
        except Exception as e:
            logger.error(f"実際のリクエスト再構築エラー: {e}")
            return f"[リクエスト再構築エラー: {e}]"
    
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
                # Content-Lengthは常にライブラリに自動計算させる
                if key.lower() not in ['host', 'connection', 'content-length']:
                    headers[key] = value
            
            # Hostヘッダーの処理（既に設定されている場合はそのまま使用）
            if 'Host' not in headers and 'host' not in headers:
                headers['Host'] = host_header
            
            # ボディの処理
            data = None
            # GETリクエストやHEADリクエストの場合はボディを設定しない
            if parsed["body"] and parsed["method"].upper() not in ['GET', 'HEAD']:
                # Content-Typeヘッダーに基づいてボディを処理
                content_type = headers.get('Content-Type', '').lower()
                
                if 'multipart/form-data' in content_type:
                    # multipart/form-dataの場合は元のボディをできるだけそのまま使用
                    original_body = parsed["body"]
                    
                    # Content-Typeヘッダーにboundaryが含まれているか確認
                    logger.info(f"Content-Typeヘッダー: {headers.get('Content-Type', 'N/A')}")
                    logger.info(f"元のボディサイズ: {len(original_body.encode('utf-8'))} bytes")
                    
                    # 改行文字の状況を確認
                    has_crlf = '\r\n' in original_body
                    has_lf = '\n' in original_body
                    logger.info(f"改行文字の状況: CRLF={has_crlf}, LF={has_lf}")
                    
                    # multipart/form-dataの最終バウンダリーのみチェック
                    body = self.ensure_multipart_body_format(original_body, content_type)
                    
                    # データはbytesとして処理
                    data = body.encode('utf-8')
                    
                    logger.info(f"multipart/form-data処理: 最終ボディサイズ={len(data)} bytes")
                    logger.info("Content-Lengthはライブラリが自動計算します")
                    
                    # データの先頭と末尾を確認
                    logger.info(f"データの先頭: {repr(data[:150])}")
                    logger.info(f"データの末尾: {repr(data[-150:])}")
                    
                elif 'application/json' in content_type:
                    try:
                        data = json.dumps(json.loads(parsed["body"]))
                    except json.JSONDecodeError:
                        data = parsed["body"]
                elif 'application/x-www-form-urlencoded' in content_type:
                    data = parsed["body"]
                else:
                    data = parsed["body"]
            
            # 送信前にデバッグ情報を出力
            logger.info(f"送信予定のURL: {url}")
            logger.info(f"送信予定のメソッド: {parsed['method']}")
            logger.info(f"送信予定のヘッダー: {headers}")
            if data:
                logger.info(f"送信予定のデータタイプ: {type(data)}")
                logger.info(f"送信予定のデータサイズ: {len(data) if isinstance(data, (str, bytes)) else 'N/A'}")
                if isinstance(data, str) and len(data) < 500:
                    logger.info(f"送信予定のデータ内容: {repr(data[:200])}")
                elif isinstance(data, bytes) and len(data) < 500:
                    logger.info(f"送信予定のデータ内容: {repr(data[:200])}")
            
            # リクエストを送信
            start_time = asyncio.get_event_loop().time()
            
            # multipart/form-dataの場合は特別な処理
            request_kwargs = {
                "method": parsed["method"],
                "url": url,
                "headers": headers,
                "timeout": aiohttp.ClientTimeout(total=config.timeout),
                "allow_redirects": config.follow_redirects
            }
            
            # Content-Typeに基づいてデータの渡し方を調整
            content_type = headers.get('Content-Type', '').lower()
            if 'multipart/form-data' in content_type and data:
                # multipart/form-dataの場合は、aiohttpの自動処理を避けるためにdataパラメータを使用
                request_kwargs["data"] = data
                logger.info("multipart/form-dataとしてdataパラメータで送信")
            elif data:
                request_kwargs["data"] = data
                logger.info("通常のデータとして送信")
            
            async with self.session.request(**request_kwargs) as response:
                elapsed_time = asyncio.get_event_loop().time() - start_time
                
                # レスポンスボディを読み取り
                body = await response.text()
                
                # 実際に送信されたリクエストを再構築
                actual_request = self.build_actual_request(
                    method=parsed["method"],
                    url=url,
                    headers=headers,
                    data=data
                )
                
                return HTTPResponse(
                    status_code=response.status,
                    headers=dict(response.headers),
                    body=body,
                    url=str(response.url),
                    elapsed_time=elapsed_time,
                    actual_request=actual_request
                )
                
        except Exception as e:
            logger.error(f"リクエスト送信エラー: {e}")
            
            # エラーの場合でも実際のリクエストを記録（可能な限り）
            actual_request = "[エラーにより実際のリクエストを記録できませんでした]"
            try:
                # エラーでも可能な限りリクエストを再構築
                parsed = self.parse_http_request(request_text)
                url = f"{config.scheme}://{config.base_url}{parsed['url']}"
                headers = parsed["headers"]
                
                # ボディの処理
                data = None
                if parsed["body"]:
                    data = parsed["body"].encode('utf-8')
                
                actual_request = self.build_actual_request(
                    method=parsed["method"],
                    url=url,
                    headers=headers,
                    data=data
                )
            except Exception as inner_e:
                logger.error(f"実際のリクエスト再構築エラー: {inner_e}")
                actual_request = f"[リクエスト再構築エラー: {inner_e}]"
            
            return HTTPResponse(
                status_code=0,
                headers={},
                body="",
                url="",
                elapsed_time=0,
                error=str(e),
                actual_request=actual_request
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
    
    async def send_multiple_requests_sequential(self, requests: List[str], config: HTTPRequestConfig = None) -> List[HTTPResponse]:
        """
        複数のリクエストを順次送信（同期実行）
        
        Args:
            requests (List[str]): リクエスト文字列のリスト
            config (HTTPRequestConfig): リクエスト設定
            
        Returns:
            List[HTTPResponse]: レスポンス情報のリスト
        """
        if config is None:
            config = HTTPRequestConfig()
            
        results = []
        for i, request in enumerate(requests):
            print(f"同期実行: リクエスト {i+1}/{len(requests)} を送信中...")
            try:
                response = await self.send_request(request, config)
                results.append(response)
                print(f"同期実行: リクエスト {i+1} 完了 - ステータス: {response.status_code}")
                
                # リクエスト間の待機時間（最後のリクエスト以外）
                if i < len(requests) - 1 and config.request_delay > 0:
                    print(f"同期実行: {config.request_delay}秒待機中...")
                    await asyncio.sleep(config.request_delay)
                    
            except Exception as e:
                print(f"同期実行: リクエスト {i+1} エラー - {str(e)}")
                results.append(e)
                
                # エラーが発生してもウェイトを入れる（オプション）
                if i < len(requests) - 1 and config.request_delay > 0:
                    await asyncio.sleep(config.request_delay)
                    
        return results

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
        if config is None:
            config = HTTPRequestConfig()
            
        async with HTTPClient() as client:
            # リクエスト文字列を抽出
            request_texts = [req["request"] for req in requests]
            
            # 実行モードに応じてリクエストを送信
            if config.sequential_execution:
                print(f"同期実行モード: {len(request_texts)}件のリクエストを順次実行します")
                responses = await client.send_multiple_requests_sequential(request_texts, config)
            else:
                print(f"並列実行モード: {len(request_texts)}件のリクエストを並列実行します")
                responses = await client.send_multiple_requests(request_texts, config)
            
            # 結果を結合
            results = []
            for i, (request, response) in enumerate(zip(requests, responses)):
                print(f"DEBUG: RequestExecutor - リクエスト {i+1} データ: {request}")
                if isinstance(response, Exception):
                    # エラーの場合
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
                            "error": str(response),
                            "actual_request": None
                        }
                    }
                else:
                    # 正常な場合
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
                print(f"DEBUG: RequestExecutor - 結果データ: {result}")
                results.append(result)
            
            return results 