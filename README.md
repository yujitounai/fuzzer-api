# プレースホルダ置換API

戦略に応じて入力した文字列のプレースホルダを置き換えるPython APIです。4つの攻撃戦略（Sniper、Battering ram、Pitchfork、Cluster bomb）をサポートしています。

## 機能

### 1. Sniper Attack
- 各ペイロードを各位置に順番に配置
- 単一のペイロードセットを使用
- 総リクエスト数 = 位置数 × ペイロード数

### 2. Battering Ram Attack
- 同じペイロードを全ての位置に同時に配置
- 単一のペイロードセットを使用
- 総リクエスト数 = ペイロード数

### 3. Pitchfork Attack
- 各位置に異なるペイロードセットを使用し、同時に配置
- ペイロードセット数 = プレースホルダ数
- 総リクエスト数 = 最小のペイロードセットのサイズ

### 4. Cluster Bomb Attack
- 全てのペイロードの組み合わせをテスト
- ペイロードセット数 = プレースホルダ数
- 総リクエスト数 = 全ペイロードセットの積

## セットアップ

1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

2. サーバーを起動:
```bash
python main.py
```

サーバーは `http://localhost:8000` で起動します。

## 使用方法

### API エンドポイント

#### POST /replace-placeholders
プレースホルダを指定された戦略に応じて置き換えます。

**リクエスト例:**
```json
{
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
```

**レスポンス例:**
```json
{
  "strategy": "sniper",
  "total_requests": 6,
  "requests": [
    {
      "request": "SELECT * FROM users WHERE id=1 AND name=",
      "placeholder": "id",
      "payload": "1"
    },
    {
      "request": "SELECT * FROM users WHERE id=1' OR '1'='1 AND name=",
      "placeholder": "id",
      "payload": "1' OR '1'='1"
    }
  ]
}
```

#### GET /
APIの基本情報を取得します。

### サンプルスクリプト

`example_usage.py` を実行して各戦略をテストできます:

```bash
python example_usage.py
```

## 戦略の詳細

### Sniper Attack
- **用途**: 個別のパラメータで一般的な脆弱性をファジングする場合
- **例**: SQLインジェクション、XSSなどの単一パラメータ攻撃

### Battering Ram Attack
- **用途**: 同じ入力を複数の場所に挿入する必要がある場合
- **例**: ユーザー名をクッキーとボディパラメータの両方に挿入

### Pitchfork Attack
- **用途**: 関連するが異なる入力を複数の場所に挿入する場合
- **例**: ユーザー名とそのユーザーに対応する既知のID番号

### Cluster Bomb Attack
- **用途**: 無関係または未知の入力を複数の場所に挿入する場合
- **例**: ユーザー名とパスワードの推測

## 注意事項

- Cluster Bomb Attackは、ペイロードセットが多い場合に非常に大きな数のリクエストを生成する可能性があります
- ペイロードセットの数は、Pitchfork AttackとCluster Bomb Attackではプレースホルダの数と一致する必要があります
- テンプレート内のプレースホルダは `<<placeholder_name>>` の形式で指定してください

## ライセンス

MIT License 