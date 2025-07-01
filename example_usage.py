import requests
import json

# APIのベースURL
BASE_URL = "http://localhost:8000"

def test_sniper_attack():
    """Sniper attackのテスト"""
    print("=== Sniper Attack テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<id>> AND name=<<name>>",
        "placeholders": ["id", "name"],
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

if __name__ == "__main__":
    try:
        # API情報を取得
        test_api_info()
        
        # 各戦略をテスト
        test_sniper_attack()
        test_battering_ram_attack()
        test_pitchfork_attack()
        test_cluster_bomb_attack()
        
    except requests.exceptions.ConnectionError:
        print("エラー: APIサーバーに接続できません。")
        print("サーバーを起動してください: python main.py")
    except Exception as e:
        print(f"エラー: {e}") 