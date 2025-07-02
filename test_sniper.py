import requests
import json

def test_sniper_with_multiple_placeholders():
    """同じプレースホルダが複数ある場合のSniper攻撃テスト"""
    print("=== Sniper Attack (複数プレースホルダ) テスト ===")
    
    payload = {
        "template": "GET /hack/normalxss.php?cmd=<<>>&host=<<>> HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "placeholders": ["cmd", "host"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["test1", "test2"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_sniper_single_placeholder():
    """単一プレースホルダのSniper攻撃テスト"""
    print("=== Sniper Attack (単一プレースホルダ) テスト ===")
    
    payload = {
        "template": "GET /hack/normalxss.php?cmd=<<>> HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "placeholders": ["cmd"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["1", "1' OR '1'='1", "1; DROP TABLE users; --"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_sniper_no_placeholders():
    """プレースホルダがない場合のSniper攻撃テスト"""
    print("=== Sniper Attack (プレースホルダなし) テスト ===")
    
    payload = {
        "template": "GET /hack/normalxss.php HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "placeholders": [],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["1", "1' OR '1'='1", "1; DROP TABLE users; --"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_history_api():
    """保存機能（履歴API）のテスト"""
    print("=== 履歴API（/api/history, /api/history/{id}, /api/history/{id} DELETE）テスト ===")
    # 履歴一覧取得
    res = requests.get("http://localhost:8000/api/history?limit=5")
    print(f"/api/history ステータス: {res.status_code}")
    history = res.json()
    print(f"履歴件数: {len(history)}")
    if history:
        first_id = history[0]['id']
        # 詳細取得
        detail = requests.get(f"http://localhost:8000/api/history/{first_id}")
        print(f"/api/history/{first_id} ステータス: {detail.status_code}")
        print(f"詳細: {json.dumps(detail.json(), indent=2, ensure_ascii=False)}")
        # 削除
        delete = requests.delete(f"http://localhost:8000/api/history/{first_id}")
        print(f"/api/history/{first_id} DELETE ステータス: {delete.status_code}")
        print(f"削除レスポンス: {delete.json()}")
    print()

def test_statistics_api():
    """統計情報APIのテスト"""
    print("=== 統計API（/api/statistics）テスト ===")
    res = requests.get("http://localhost:8000/api/statistics")
    print(f"/api/statistics ステータス: {res.status_code}")
    print(f"統計: {json.dumps(res.json(), indent=2, ensure_ascii=False)}")
    print()

def test_http_execution_api():
    """HTTPリクエスト実行APIのテスト"""
    print("=== HTTPリクエスト実行API（/api/execute-requests）テスト ===")
    
    # まず、テスト用のリクエストを作成（複雑なHTTPリクエスト）
    payload = {
        "template": """POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/json
User-Agent: TestClient/1.0
Accept: application/json
Authorization: Bearer <<>>
Content-Length: 45

{"username": "testuser", "email": "test@example.com"}""",
        "placeholders": [],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "auth_tokens",
                "payloads": ["valid_token_123", "invalid_token_456"]
            }
        ]
    }
    
    # リクエストを作成
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"リクエスト作成 ステータス: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        request_id = result.get('request_id')
        print(f"作成されたリクエストID: {request_id}")
        
        # HTTPリクエスト実行
        execute_payload = {
            "request_id": request_id,
            "http_config": {
                "scheme": "https",
                "base_url": "api.example.com",
                "timeout": 10,
                "follow_redirects": True,
                "verify_ssl": False,
                "additional_headers": {
                    "User-Agent": "Test-Agent/1.0"
                }
            }
        }
        
        execute_response = requests.post("http://localhost:8000/api/execute-requests", json=execute_payload)
        print(f"HTTP実行 ステータス: {execute_response.status_code}")
        
        if execute_response.status_code == 200:
            execute_result = execute_response.json()
            print(f"実行結果: {json.dumps(execute_result, indent=2, ensure_ascii=False)}")
        else:
            print(f"実行エラー: {execute_response.text}")
    else:
        print(f"リクエスト作成エラー: {response.text}")
    print()

def test_single_http_execution_api():
    """個別HTTPリクエスト実行APIのテスト"""
    print("=== 個別HTTPリクエスト実行API（/api/execute-single-request）テスト ===")
    
    # まず、テスト用のリクエストを作成（存在しないドメイン）
    payload = {
        "template": """GET /api/test HTTP/1.1
Host: api.example.com
User-Agent: TestClient/1.0
Accept: application/json""",
        "placeholders": [],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "test_payloads",
                "payloads": ["test1", "test2"]
            }
        ]
    }
    
    # リクエスト作成
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"リクエスト作成 ステータス: {response.status_code}")
    
    if response.status_code != 200:
        print("リクエスト作成に失敗しました")
        return
    
    result = response.json()
    request_id = result["request_id"]
    total_requests = result["total_requests"]
    print(f"作成されたリクエストID: {request_id}")
    print(f"生成されたリクエスト数: {total_requests}")
    
    # 個別リクエスト実行（位置0のリクエスト）
    execute_payload = {
        "request_id": request_id,
        "position": 0,  # 1番目のリクエスト
        "http_config": {
            "scheme": "https",
            "base_url": "api.example.com",
            "timeout": 10,
            "follow_redirects": True,
            "verify_ssl": False,
            "additional_headers": {
                "User-Agent": "Test-Agent/1.0"
            }
        }
    }
    
    response = requests.post("http://localhost:8000/api/execute-single-request", json=execute_payload)
    print(f"個別HTTP実行 ステータス: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"個別実行結果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # レスポンスボディの詳細を確認
        http_response = result.get('http_response', {})
        print(f"レスポンスボディの長さ: {len(http_response.get('body', ''))}")
        print(f"レスポンスボディ: '{http_response.get('body', '')}'")
    else:
        print(f"個別実行エラー: {response.text}")
    print()

def test_post_request_examples():
    """POSTリクエストの様々な例のテスト"""
    print("=== POSTリクエスト例テスト ===")
    
    # 1. 通常のPOSTリクエスト（フォームデータ）
    print("--- 1. 通常のPOSTリクエスト（フォームデータ） ---")
    payload = {
        "template": """POST /api/login HTTP/1.1
Host: example.com
Content-Type: application/x-www-form-urlencoded
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: ja,en-US;q=0.9,en;q=0.8
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
Content-Length: <<>>

username=<<>>&password=<<>>&submit=Login""",
        "placeholders": ["content_length", "username", "password"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "login_credentials",
                "payloads": ["admin", "user123", "testuser"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"フォームPOST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
        print(f"最初のリクエスト: {result['requests'][0]['request'][:200]}...")
    print()
    
    # 2. JSON送信のPOSTリクエスト
    print("--- 2. JSON送信のPOSTリクエスト ---")
    payload = {
        "template": """POST /api/users HTTP/1.1
Host: api.example.com
Content-Type: application/json
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
Accept: application/json
Authorization: Bearer <<>>
Content-Length: <<>>

{"username": "<<>>", "email": "<<>>", "role": "user"}""",
        "placeholders": ["auth_token", "content_length", "username", "email"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "user_data",
                "payloads": ["john_doe", "jane_smith", "admin_user"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"JSON POST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
        print(f"最初のリクエスト: {result['requests'][0]['request'][:200]}...")
    print()
    
    # 3. Multipart送信のPOSTリクエスト
    print("--- 3. Multipart送信のPOSTリクエスト ---")
    payload = {
        "template": """POST /api/upload HTTP/1.1
Host: upload.example.com
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary<<>>
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
Accept: application/json
Content-Length: <<>>

------WebKitFormBoundary<<>>
Content-Disposition: form-data; name="file"; filename="<<>>"
Content-Type: application/octet-stream

<<>>
------WebKitFormBoundary<<>>
Content-Disposition: form-data; name="description"

<<>>
------WebKitFormBoundary<<>>--""",
        "placeholders": ["boundary1", "content_length", "boundary2", "filename", "file_content", "boundary3", "description", "boundary4"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "file_upload",
                "payloads": ["test.txt", "document.pdf", "image.jpg"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"Multipart POST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
        print(f"最初のリクエスト: {result['requests'][0]['request'][:200]}...")
    print()

def test_post_with_json_body():
    """JSONボディを含むPOSTリクエストの詳細テスト"""
    print("=== JSONボディPOSTリクエスト詳細テスト ===")
    
    payload = {
        "template": """POST /api/products HTTP/1.1
Host: api.example.com
Content-Type: application/json
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
Accept: application/json
Authorization: Bearer <<>>
Content-Length: <<>>

{
  "name": "<<>>",
  "price": <<>>,
  "category": "<<>>",
  "description": "<<>>",
  "tags": ["<<>>", "<<>>"]
}""",
        "placeholders": ["auth_token", "content_length", "product_name", "price", "category", "description", "tag1", "tag2"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "product_data",
                "payloads": ["Laptop", "Smartphone", "Tablet"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"JSONボディPOST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
        print(f"リクエストID: {result['request_id']}")
        
        # 最初のリクエストの詳細を表示
        first_request = result['requests'][0]
        print(f"最初のリクエスト:")
        print(f"  プレースホルダ: {first_request['placeholder']}")
        print(f"  ペイロード: {first_request['payload']}")
        print(f"  位置: {first_request['position']}")
        print(f"  リクエスト内容（最初の300文字）:")
        print(f"  {first_request['request'][:300]}...")
    print()

def test_post_with_multipart_file():
    """Multipartファイルアップロードの詳細テスト"""
    print("=== Multipartファイルアップロード詳細テスト ===")
    
    payload = {
        "template": """POST /api/upload-file HTTP/1.1
Host: upload.example.com
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary<<>>
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
Accept: application/json
Content-Length: <<>>

------WebKitFormBoundary<<>>
Content-Disposition: form-data; name="file"; filename="<<>>"
Content-Type: <<>>

<<>>
------WebKitFormBoundary<<>>
Content-Disposition: form-data; name="metadata"

{"filename": "<<>>", "size": "<<>>", "type": "<<>>"}
------WebKitFormBoundary<<>>--""",
        "placeholders": ["boundary1", "content_length", "boundary2", "filename", "content_type", "file_content", "boundary3", "meta_filename", "file_size", "file_type", "boundary4"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "file_types",
                "payloads": ["document.pdf", "image.png", "video.mp4"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/api/replace-placeholders", json=payload)
    print(f"MultipartファイルPOST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
        print(f"リクエストID: {result['request_id']}")
        
        # 最初のリクエストの詳細を表示
        first_request = result['requests'][0]
        print(f"最初のリクエスト:")
        print(f"  プレースホルダ: {first_request['placeholder']}")
        print(f"  ペイロード: {first_request['payload']}")
        print(f"  位置: {first_request['position']}")
        print(f"  リクエスト内容（最初の400文字）:")
        print(f"  {first_request['request'][:400]}...")
    print()

if __name__ == "__main__":
    test_sniper_with_multiple_placeholders()
    test_sniper_single_placeholder()
    test_sniper_no_placeholders()
    test_history_api()
    test_statistics_api()
    test_http_execution_api()
    test_single_http_execution_api()
    test_post_request_examples()
    test_post_with_json_body()
    test_post_with_multipart_file() 