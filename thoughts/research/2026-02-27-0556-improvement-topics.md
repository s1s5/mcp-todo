---
date: 2026-02-27T05:56:44+00:00
git_commit: e30b9b2c02a865db160939ef4f7639d48a5db3f9
branch: main
repository: mcp-todo
topic: "このツールを改良するのに次に取り組む課題は何だと思う？"
tags: [research, improvement, codebase-analysis]
status: complete
---

# Research: 改良に向けた課題分析

## Research Question
このツールを改良するのに次に取り組む課題は何だと思う？

## Summary

mcp-todo は Django + FastMCP + SvelteKit で構築された AI エージェントタスク管理ツールである。
コードベースを分析した結果、以下の改良課題を特定した：

1. **タスク実行の柔軟性** - 再試行・依存関係・優先度制御の不足
2. **エラー処理の改善** - 空の例外ハンドラの実装
3. **リアルタイム性の欠如** - ポーリング方式の課題
4. **Git 操作の安全策** - 危険な操作への保護
5. **MCP ツールの拡張性** - ツール数の限定
6. **スケーラビリティ** - SQLite の制約

---

## Detailed Findings

### 1. タスク実行の柔軟性

#### 現在の実装
- `todo/models.py:47-95` - Todo モデルは基本的なステータス（waiting/queued/running/completed/error/cancelled/timeout）のみ
- `todo/management/commands/task_worker.py:102-113` - 優先度は `sort_priority()` による簡易的な並び替えのみ

#### 改良余地
- **リトライ機能がない**: 失敗したタスクを再実行する手段がない
- **タスク依存関係の未対応**: 他のタスク完了を待してから実行する機能がない
- **優先度の詳細制御**: ユーザーが明示的に優先度を設定できない

#### 関連ファイル
- `todo/models.py:50-56` - Todo.Status Choices
- `todo/mcp_server.py:237-247` - sort_priority()

---

### 2. エラー処理の改善

#### 現在の実装
複数の箇所で空の例外ハンドラを使用：

| ファイル | 行 | 内容 |
|---------|---|------|
| `todo/management/commands/run_task.py` | 175 | branch 存在チェック後の空処理 |
| `todo/management/commands/run_task.py` | 293 | 例外発生時の空処理 |
| `todo/management/commands/run_task.py` | 511 | stash 復元エラーの空処理 |
| `todo/management/commands/task_worker.py` | 303 | キューフラッシュ中の例外 |

#### 改良余地
- エラー発生時のログ出力が不足
- ユーザーへのエラー通知がない
- リカバリー処理の欠如

---

### 3. リアルタイム性の欠如

#### 現在の実装
- `todo/management/commands/task_worker.py:96-125` - `process_loop()` がポーリング方式
- ポーリング間隔は固定（コード内に明記なし、デフォルト動作）

#### 改良余地
- **WebSocket 通知**: タスク完了時のリアルタイム通知
- **Server-Sent Events (SSE)**: タスク進捗のリアルタイム更新
- **長岡リアルタイム接続**: MCP プロトコルでの双方向通信

---

### 4. Git 操作の安全策

#### 現在の実装
- `todo/views.py:380-395` - worktree 削除時に `--force` を使用
- ブランチ削除の安全策は一部実装（`is_branch_merged()` を使用）

#### 改良余地
- 重要な worktree の誤削除防止
- ブランチ名の規則強化
- dry-run モードの実装

#### 関連ファイル
- `todo/views.py:380` - `git worktree remove --force`
- `todo/views.py:225-240` - is_branch_merged()

---

### 5. MCP ツールの拡張性

#### 現在の実装
MCP サーバーで提供されるツール：
- `pushExternalTask()` - タスク作成
- `listExternalTask()` - タスク一覧取得

#### 改良余地
- `cancelTask()` - タスクキャンセル
- `retryTask()` - タスク再試行
- `getTaskDetails()` - タスク詳細取得
- `updateTaskPriority()` - 優先度更新

#### 関連ファイル
- `todo/mcp_server.py:106-158` - pushExternalTask
- `todo/mcp_server.py:161-224` - listExternalTask

---

### 6. スケーラビリティ

#### 現在の実装
- `config/settings.py` - SQLite を使用
- `todo/management/commands/task_worker.py:63` - メモリ上で `running_workdirs` を管理

#### 改良余地
- PostgreSQL/MySQL への移行（本番環境）
- 分散ロック機構の実装（複数 worker 対応）
- タスクキュー（Celery 等）の導入

---

## Code References

| ファイル | 行 | 説明 |
|---------|---|------|
| `todo/models.py` | 47-95 | Todo モデル定義 |
| `todo/mcp_server.py` | 106-158 | pushExternalTask |
| `todo/mcp_server.py` | 161-224 | listExternalTask |
| `todo/management/commands/run_task.py` | 99-181 | run_task メイン処理 |
| `todo/management/commands/task_worker.py` | 71-93 | task_worker メインループ |
| `todo/views.py` | 380 | worktree 削除 |

---

## Open Questions

1. **優先して実装すべき機能**: リトライ機能、リアルタイム通知、MCP 拡張のどれを先に実装すべきか？
2. **データベースの移行予定**: SQLite から他の DB への移行を検討しているか？
3. **フロントエンドの改善点**: SvelteKit 側の課題（比如、生 UI の改善）も含むか？
