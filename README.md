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
- **機能**: リクエスト履歴の表示・管理・統計情報

### API エンドポイント

#### POST /replace-placeholders
プレースホルダを指定された戦略に応じて置き換え、データベースに保存します。

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
  ],
  "request_id": 1
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