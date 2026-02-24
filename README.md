# MCP Todo

AIエージェント向けのタスク管理MCPサーバー。Djangoアプリケーションとして実装されており、GPT Engineerシリーズのgooseエージェントとの連携を目的とする。

## 必要環境

- **Python**: 3.13以上
- **データベース**: SQLite3（開発・本番共通）
- **外部ツール**: git
- **パッケージ管理**: uv

以下のPythonライブラリが必要（pyproject.toml参照）:
- django >= 5.0
- djangorestframework >= 3.16.1
- mcp >= 1.0
- pyyaml >= 6.0.3

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
# または
pip install -e .
```

### 2. データベースマイグレーション

```bash
python manage.py migrate
```

### 3. MCPサーバーの起動確認

```bash
python -m todo.mcp_server
```

または、エディブルインストール後:

```bash
todo-mcp
```

## 開発フロー

### MCPサーバーを起動

```bash
python -m todo.mcp_server
```

### 個別のTodoを実行

```bash
python manage.py run_task <todo_pk> --inplace
```

オプション:
- `--todo-pk`: 実行するTodoのPK
- `--agent-pk`: 使用するAgentのPK（デフォルト: なし）
- `--worktree-root`: worktree配置先ルートディレクトリ
- `--inplace`: 現在のディレクトリで実行（worktreeを作成しない）
- `--agent-quiet`: エージェント出力を抑制

### タスクワーカーを起動（バックグラウンド実行）

```bash
python manage.py task_worker --interval 2
```

statusが`queued`のTodoを自動検出・実行するデーモン。

### Djangoシェル

```bash
python manage.py shell
```

### REST APIの確認

```bash
python manage.py runserver
```

`http://localhost:8000/api/` でREST APIにアクセス可能。

## テスト

```bash
# 全テスト実行
python manage.py test

# 特定のアプリのみ
python manage.py test todo
```

## Lint / Format

このプロジェクトではPython標準のフォーマットツールを使用推奨:

```bash
# フォーマット
python -m black .

# リント
python -m ruff check .
```

## マイグレーション / コード生成

### モデル変更時のマイグレーション

```bash
python manage.py makemigrations
python manage.py migrate
```

### フロー

1. `todo/models.py` を編集
2. `makemigrations` でマイグレーションファイル生成
3. `migrate` で適用
4. 必要に応じてシリアライザー (`serializers.py`) を更新

## 環境変数

Django標準の設定ファイル `config/settings.py` で管理。主要項目:

- `SECRET_KEY`: Djangoシークレットキー
- `DEBUG`: デバッグモード（デフォルト: True）
- `ALLOWED_HOSTS`: 許可ホスト（デフォルト: `['*']`）
- `DATABASE`: SQLite (`db.sqlite3`)

追加の環境変数が必要な場合は `settings.py` に定義を追加すること。

## アーキテクチャ

### データモデル

- **TodoList**: 作業ディレクトリ（workdir）ごとにTodoを分類
- **Agent**: AIエージェントの設定（システムメッセージ、コマンド）
- **Todo**: 個別タスク。以下のステータスを持つ:
  - `waiting`: 作成済み（未キュー）
  - `queued`: キュー済み
  - `running`: 実行中
  - `completed`: 正常完了
  - `cancelled`: キャンセル
  - `timeout`: タイムアウト
  - `error`: エラー

### MCPツール

`todo/mcp_server.py` で提供:

- `pushExternalTask`: 外部エージェントがタスクを追加

### management commands

- `run_task`: TodoをAIエージェントで実行。git worktree対応
- `task_worker`: キューされたTodoをバックグラウンドで処理

## ディレクトリ構成

```
.
├── config/          # Djangoプロジェクト設定
├── todo/            # メインアプリケーション
│   ├── models.py    # データモデル
│   ├── views.py     # REST APIビュー
│   ├── serializers.py
│   ├── mcp_server.py    # MCPサーバ
│   ├── management/commands/
│   │   ├── run_task.py      # タスク実行コマンド
│   │   └── task_worker.py   # バックグラウンドワーカー
│   └── migrations/  # マイグレーションファイル
├── db.sqlite3       # SQLiteデータベース
└── manage.py        # Django管理スクリプト
```

## コントリビューションに関する注意事项

### 入力検証ルール

- **ブランチ名**: `^[a-zA-Z0-9_-]+$` に従う（英数字、ハイフン、アンダースコアのみ）
- **ファイルパス**: workdir相対パス。親ディレクトリ参照（`..`）や絶対パスは禁止
- **worktreeパス**: `~/work/worktrees/{repo}-{branch}`（`--worktree-root`で変更可能）

### エラー処理

- worktree作成失敗時は `cleanup_worktree()` でクリーンアップ
- タスク実行中のキャンセル対応: 親プロセス側で子プロセスを強制終了

## 運用上の注意点

### データベース変更時

1. モデル редакти
2. `makemigrations` でマイグレーション生成
3. `migrate` で適用
4. シリアライザー・ビューも相应更新

### task_workerの運用

- 本番環境では適切なプロセス管理（systemd等）を使用すること
- `--interval` でポーリング間隔を調整可能（デフォルト: 2秒）

### セキュリティ

- `DEBUG = True` のまま本番運用しない
- `SECRET_KEY` は本番環境では変更必須
- `ALLOWED_HOSTS` を適切に設定
