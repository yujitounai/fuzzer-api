import requests
import json

def test_sniper_with_multiple_placeholders():
    """同じプレースホルダが複数ある場合のSniper攻撃テスト"""
    print("=== Sniper Attack (複数プレースホルダ) テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<>> AND id=<<>>",
        "placeholders": ["id"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["test1", "test2"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_sniper_single_placeholder():
    """単一プレースホルダのSniper攻撃テスト"""
    print("=== Sniper Attack (単一プレースホルダ) テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<>>",
        "placeholders": ["id"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["1", "1' OR '1'='1", "1; DROP TABLE users; --"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_sniper_complex_template():
    """複雑なテンプレートのSniper攻撃テスト"""
    print("=== Sniper Attack (複雑なテンプレート) テスト ===")
    
    payload = {
        "template": "SELECT * FROM users WHERE id=<<>> AND name=<<>> AND email=<<>>",
        "placeholders": ["id"],  # Sniperでは使用されないが、APIの仕様上必要
        "strategy": "sniper",
        "payload_sets": [
            {
                "name": "sql_injection",
                "payloads": ["admin", "1' OR '1'='1"]
            }
        ]
    }
    
    response = requests.post("http://localhost:8000/replace-placeholders", json=payload)
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

if __name__ == "__main__":
    test_sniper_with_multiple_placeholders()
    test_sniper_single_placeholder()
    test_sniper_complex_template() 