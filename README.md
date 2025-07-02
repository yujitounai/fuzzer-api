# プレースホルダ置換API

戦略に応じて入力した文字列のプレースホルダを置き換えるPython APIです。4つの攻撃戦略（Sniper、Battering ram、Pitchfork、Cluster bomb）をサポートし、リクエストと生成されたリクエストの永続化機能も提供しています。

## 機能

### 攻撃戦略

#### 1. Sniper Attack
- 各ペイロードを各位置に順番に配置
- 単一のペイロードセットを使用
- 総リクエスト数 = 位置数 × ペイロード数

#### 2. Battering Ram Attack
- 同じペイロードを全ての位置に同時に配置
- 単一のペイロードセットを使用
- 総リクエスト数 = ペイロード数

#### 3. Pitchfork Attack
- 各位置に異なるペイロードセットを使用し、同時に配置
- ペイロードセット数 = プレースホルダ数
- 総リクエスト数 = 最小のペイロードセットのサイズ

#### 4. Cluster Bomb Attack
- 全てのペイロードの組み合わせをテスト
- ペイロードセット数 = プレースホルダ数
- 総リクエスト数 = 全ペイロードセットの積

### 永続化機能

#### データベース
- SQLite + SQLAlchemyによるリクエストと生成されたリクエストの永続化
- 自動的にリクエスト履歴を保存
- 統計情報の提供

#### 履歴管理
- リクエスト履歴の表示・検索
- 詳細情報の取得
- 不要なリクエストの削除

#### Webインターフェース
- テスト用Webページ（`/test`）
- 履歴表示用Webページ（`/history-page`）
- 統計情報の可視化

## セットアップ

1. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

**主要な依存関係:**
- `fastapi`: Webフレームワーク
- `uvicorn`: ASGIサーバー
- `sqlalchemy`: データベースORM
- `aiohttp`: HTTPリクエスト送信（非同期）
- `pydantic`: データバリデーション

2. サーバーを起動:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

サーバーは `http://localhost:8000` で起動します。

## 使用方法

### Webインターフェース

#### テストページ
- **URL**: `http://localhost:8000/test`
- **機能**: プレースホルダ置換のテスト実行

#### 履歴ページ
- **URL**: `http://localhost:8000/history-page`
- **機能**: 
  - リクエスト履歴の表示・管理・統計情報
  - HTTPリクエスト実行機能（設定可能なタイムアウト、リダイレクト追跡、SSL検証、追加ヘッダー）
  - 実行結果の詳細表示（ステータスコード、レスポンス時間、エラー情報）
  - レスポンス内容の表示（ヘッダー、ボディ）

### API エンドポイント

#### POST /replace-placeholders
プレースホルダを指定された戦略に応じて置き換え、データベースに保存します。

**リクエスト例:**
```json
{
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
```

**レスポンス例:**
```json
{
  "strategy": "sniper",
  "total_requests": 4,
  "requests": [
    {
      "request": "GET /hack/normalxss.php?cmd= HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\nAccept-Encoding: gzip, deflate, br, zstd\nAccept-Language: ja,en-US;q=0.9,en;q=0.8",
      "placeholder": "original",
      "payload": "",
      "position": 0
    },
    {
      "request": "GET /hack/normalxss.php?cmd=1 HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\nAccept-Encoding: gzip, deflate, br, zstd\nAccept-Language: ja,en-US;q=0.9,en;q=0.8",
      "placeholder": "<<>>",
      "payload": "1",
      "position": 1
    },
    {
      "request": "GET /hack/normalxss.php?cmd=1' OR '1'='1 HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\nAccept-Encoding: gzip, deflate, br, zstd\nAccept-Language: ja,en-US;q=0.9,en;q=0.8",
      "placeholder": "<<>>",
      "payload": "1' OR '1'='1",
      "position": 2
    },
    {
      "request": "GET /hack/normalxss.php?cmd=1; DROP TABLE users; -- HTTP/1.1\nHost: bogus.jp\nUser-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36\nAccept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7\nAccept-Encoding: gzip, deflate, br, zstd\nAccept-Language: ja,en-US;q=0.9,en;q=0.8",
      "placeholder": "<<>>",
      "payload": "1; DROP TABLE users; --",
      "position": 3
    }
  ]
}
```

#### GET /history
リクエスト履歴を取得します。

**クエリパラメータ:**
- `limit`: 取得件数（デフォルト: 50）
- `offset`: オフセット（デフォルト: 0）

#### GET /history/{request_id}
特定のリクエストの詳細を取得します。

#### DELETE /history/{request_id}
特定のリクエストを削除します。

#### GET /statistics
データベースの統計情報を取得します。

**レスポンス例:**
```json
{
  "total_fuzzer_requests": 10,
  "total_generated_requests": 45,
  "strategy_distribution": {
    "sniper": 5,
    "battering_ram": 2,
    "pitchfork": 2,
    "cluster_bomb": 1
  }
}
```

#### POST /execute-requests
生成されたリクエストを実際にHTTPリクエストとして送信します。

**設定可能なパラメータ:**
- `scheme`: プロトコル（http または https）
- `base_url`: ベースURL（スキームなし、例: localhost:8000, example.com:443）
- `timeout`: タイムアウト時間（秒）
- `follow_redirects`: リダイレクトを追跡するかどうか
- `verify_ssl`: SSL証明書を検証するかどうか
- `additional_headers`: 追加のHTTPヘッダー

**リクエスト例:**
```json
{
  "request_id": 1,
  "http_config": {
    "scheme": "https",
    "base_url": "example.com:443",
    "timeout": 30,
    "follow_redirects": true,
    "verify_ssl": false,
    "additional_headers": {
      "User-Agent": "Custom-Agent/1.0"
    }
  }
}
```

**レスポンス例:**
```json
{
  "request_id": 1,
  "total_requests": 5,
  "successful_requests": 4,
  "failed_requests": 1,
  "results": [
    {
      "request": "GET /api/test HTTP/1.1\nHost: localhost:8000\n\n",
      "placeholder": "original",
      "payload": "",
      "position": 0,
      "http_response": {
        "status_code": 200,
        "headers": {
          "Content-Type": "application/json",
          "Content-Length": "123"
        },
        "body": "{\"message\": \"success\"}",
        "url": "http://localhost:8000/api/test",
        "elapsed_time": 0.023,
        "error": null
      }
    }
  ]
}
```

#### GET /
APIの基本情報を取得します。

### サンプルスクリプト

#### 基本テスト
`test_sniper.py` を実行してSniper攻撃と保存機能をテストできます:

```bash
python test_sniper.py
```

#### 全戦略テスト
`example_usage.py` を実行して各戦略をテストできます:

```bash
python example_usage.py
```

## データベース

### テーブル構造

#### fuzzer_requests
- `id`: リクエストの一意識別子
- `template`: プレースホルダを含むテンプレート文字列
- `placeholders`: プレースホルダ名のリスト（JSON形式）
- `strategy`: 攻撃戦略
- `payload_sets`: ペイロードセットのリスト（JSON形式）
- `total_requests`: 生成されたリクエストの総数
- `created_at`: リクエスト作成日時
- `updated_at`: 最終更新日時

#### generated_requests
- `id`: 生成されたリクエストの一意識別子
- `fuzzer_request_id`: 元のファザーリクエストのID
- `request_number`: リクエスト番号（順序）
- `request_content`: 生成されたリクエストの内容
- `placeholder`: 使用されたプレースホルダ名
- `payload`: 使用されたペイロード
- `position`: プレースホルダの位置（Sniper攻撃用）
- `applied_to`: 適用されたプレースホルダのリスト（JSON形式）
- `created_at`: 生成日時

## 戦略の詳細

### Sniper Attack
- **用途**: 個別のパラメータで一般的な脆弱性をファジングする場合
- **例**: SQLインジェクション、XSSなどの単一パラメータ攻撃
- **プレースホルダ形式**: `<<>>`（固定形式）

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
- テンプレート内のプレースホルダは `<<placeholder_name>>` の形式で指定してください（Sniper攻撃では `<<>>`）
- データベースファイル（`fuzzer_requests.db`）は自動的に作成されます
- 履歴データは永続的に保存されるため、不要なデータは適宜削除してください

## 開発

### 依存関係
- FastAPI: Webフレームワーク
- SQLAlchemy: ORM
- Alembic: データベースマイグレーション
- Uvicorn: ASGIサーバー
- Pydantic: データバリデーション

### ファイル構成
```
fuzzer20250630/
├── main.py              # メインAPI
├── database.py          # データベースモデルとマネージャー
├── requirements.txt     # 依存関係
├── test_sniper.py      # テストスクリプト
├── example_usage.py    # 使用例
├── web_test.html       # テスト用Webページ
├── history.html        # 履歴表示用Webページ
├── fuzzer_requests.db  # SQLiteデータベース
└── README.md           # このファイル
```

## ライセンス

MIT License 

### 基本的な使用例

**Sniper攻撃の例:**

```json
{
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
```

### 変異機能（Mutations）

辞書的な値に加えて、長大な文字列を生成するためのrepeat機能をサポートしています。

**変異機能の使用例:**

```json
{
  "template": "GET /api/test?param=<<X>> HTTP/1.1\nHost: example.com",
  "mutations": [
    {
      "token": "<<X>>",
      "strategy": "dictionary",
      "values": [
        "<script>",
        "' OR 1=1 --",
        {
          "value": "A",
          "repeat": 1000
        },
        {
          "value": "ABC",
          "repeat": 500
        }
      ]
    }
  ]
}
```

**複数トークンの例:**

```json
{
  "template": "GET /api/test?param1=<<X>>&param2=<<Y>> HTTP/1.1\nHost: example.com",
  "mutations": [
    {
      "token": "<<X>>",
      "strategy": "dictionary",
      "values": [
        "test1",
        {
          "value": "A",
          "repeat": 100
        }
      ]
    },
    {
      "token": "<<Y>>",
      "strategy": "dictionary",
      "values": [
        "test2",
        {
          "value": "B",
          "repeat": 50
        }
      ]
    }
  ]
}
```

**エンドポイント:** `POST /api/mutations` 