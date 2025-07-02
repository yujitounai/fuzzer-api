import requests
import json

# APIのベースURL
BASE_URL = "http://localhost:8000"

def test_sniper_attack():
    """Sniper attackのテスト"""
    print("=== Sniper Attack テスト ===")
    
    payload = {
        "template": "GET /hack/normalxss.php?cmd=<<>> HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\nAccept-Encoding: gzip, deflate, br, zstd\nAccept-Language: ja,en-US;q=0.9,en;q=0.8",
        "placeholders": ["cmd", "host"],
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["1", "1' OR '1'='1", "1; DROP TABLE users; --"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_battering_ram_attack():
    """Battering ram attackのテスト"""
    print("=== Battering Ram Attack テスト ===")
    
    payload = {
        "template": "username=<<username>>&password=<<password>>",
        "placeholders": ["username", "password"],
        "strategy": "battering_ram",
        "payload_sets": [
            {
                "name": "common_credentials",
                "payloads": ["admin", "test", "guest"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_pitchfork_attack():
    """Pitchfork attackのテスト"""
    print("=== Pitchfork Attack テスト ===")
    
    payload = {
        "template": "username=<<username>>&user_id=<<user_id>>",
        "placeholders": ["username", "user_id"],
        "strategy": "pitchfork",
        "payload_sets": [
            {
                "name": "usernames",
                "payloads": ["admin", "user1", "test"]
            },
            {
                "name": "user_ids",
                "payloads": ["1", "2", "3"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_cluster_bomb_attack():
    """Cluster bomb attackのテスト"""
    print("=== Cluster Bomb Attack テスト ===")
    
    payload = {
        "template": "username=<<username>>&password=<<password>>",
        "placeholders": ["username", "password"],
        "strategy": "cluster_bomb",
        "payload_sets": [
            {
                "name": "usernames",
                "payloads": ["admin", "user1"]
            },
            {
                "name": "passwords",
                "payloads": ["password123", "123456", "qwerty"]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_api_info():
    """APIの基本情報を取得"""
    print("=== API情報 ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
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
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"フォームPOST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
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
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"JSON POST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
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
    
    response = requests.post(f"{BASE_URL}/replace-placeholders", json=payload)
    print(f"Multipart POST ステータス: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"生成されたリクエスト数: {result['total_requests']}")
    print()

if __name__ == "__main__":
    try:
        # API情報を取得
        test_api_info()
        
        # 各戦略をテスト
        test_sniper_attack()
        test_battering_ram_attack()
        test_pitchfork_attack()
        test_cluster_bomb_attack()
        test_post_request_examples()
        
    except requests.exceptions.ConnectionError:
        print("エラー: APIサーバーに接続できません。")
        print("サーバーを起動してください: python main.py")
    except Exception as e:
        print(f"エラー: {e}") 