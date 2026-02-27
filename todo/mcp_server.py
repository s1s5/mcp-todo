"""
Todo MCP Server
起動時のCWDと同じTodoListを使用してLLMがTodoを管理できる
"""

import os
import uuid
from pathlib import Path

import django
from asgiref.sync import sync_to_async
from django.conf import settings

# FastMCPサーバーを作成
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("todo-mcp")

# Djangoセットアップ
# settingsが未設定の場合のみ設定
if not settings.configured:
    BASE_DIR = Path(__file__).resolve().parent.parent
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "todo",
        ],
    )
    django.setup()


from todo.models import Todo, TodoList
from todo.utils import get_or_create_todolist_with_parent


def get_todo_list_or_create() -> TodoList:
    """CWDと同じTodoListを取得、なければ自動作成（worktreeの場合はparentを設定）"""
    cwd = os.getcwd()
    todo_list, created = get_or_create_todolist_with_parent(cwd)
    return todo_list


import re


def validate_branch_name(branch: str) -> str:
    """
    ブランチ名が英数字とハイフン(-)、アンダースコア(_)のみかどうか検証する

    Args:
        branch: 検証するブランチ名

    Returns:
        検証済みのブランチ名

    Raises:
        ValueError: 無効なブランチ名の場合
    """
    if not branch:
        return branch

    # 英数字、ハイフン、アンダースコアのみ許可
    if not re.match(r"^[a-zA-Z0-9_-]+$", branch):
        raise ValueError(f"ブランチ名には英数字、ハイフン(-)、アンダースコア(_)のみ使用できます: {branch}")

    return branch


def validate_path(workdir: str, file_path: str, must_exists: bool) -> str:
    """
    ファイルパスがCWD（workdir）内の相対パスかどうか検証する
    親ディレクトリ参照 (..) や絶対パスはエラーとする

    Args:
        workdir: 基準となるディレクトリ（TodoList.workdir）
        file_path: 検証するファイルパス

    Returns:
        検証済みの相対パス

    Raises:
        ValueError: 無効なパス（親ディレクトリ参照、絶対パス）の場合
    """
    # 絶対パスはエラー
    if os.path.isabs(file_path):
        raise ValueError(f"絶対パスは指定できません: {file_path}")

    # 親ディレクトリ参照はエラー
    if ".." in file_path:
        raise ValueError(f"親ディレクトリ参照は禁止です: {file_path}")

    # 正規化してパスを解決
    resolved = os.path.normpath(os.path.join(workdir, file_path))

    # workdir外に出れていないか確認
    real_workdir = os.path.realpath(workdir)
    real_resolved = os.path.realpath(resolved)

    # ファイル自体をチェック
    if not real_resolved.startswith(real_workdir):
        raise ValueError(f"workdir外のパスは指定できません: {file_path}")

    # ファイルが実際に存在するか確認
    if must_exists and (not os.path.exists(resolved)):
        raise ValueError(f"ファイルが存在しません: {file_path}")

    # workdirからの相対パスを返す
    rel_path = os.path.relpath(resolved, workdir)
    return rel_path


@mcp.tool()
@sync_to_async
def pushExternalTask(
    ref_files: list[str],
    edit_files: list[str],
    prompt: str,
    title: str = "",
    context: str = "",
    validation_command: str = "",
    branch: str = "",
) -> dict:
    """外部エージェントが実行する新しいタスクを追加する

    Args:
        ref_files: 参照用ファイルリスト（CWDからの相対パス）
        edit_files: 編集対象ファイルリスト（CWDからの相対パス）
        prompt: タスク内容
        title: タスクのタイトル
        context: 動的に注入するコンテキスト
        validation_command: 完了判断用コマンド
        branch: ブランチ名（英数字、ハイフン、アンダースコアのみ）

    Returns:
        追加されたタスクの情報

    Raises:
        ValueError: 無効なパスまたはブランチ名が指定された場合
    """
    todo_list = get_todo_list_or_create()
    workdir = todo_list.workdir

    # ブランチ名を検証
    validated_branch = validate_branch_name(branch)

    # パスを検証して正規化
    validated_ref_files = []
    for f in ref_files:
        validated_ref_files.append(validate_path(workdir, f, True))

    validated_edit_files = []
    for f in edit_files:
        validated_edit_files.append(validate_path(workdir, f, False))

    todo = Todo.objects.create(
        todo_list=todo_list,
        title=title,
        ref_files=validated_ref_files,
        edit_files=validated_edit_files,
        prompt=prompt,
        context=context,
        validation_command=validation_command,
        branch_name=validated_branch, # f"ai/{validated_branch}-{uuid.uuid4().hex[:6]}",
    )
    return {
        "id": todo.id,
        "title": todo.title,
        "ref_files": todo.ref_files,
        "edit_files": todo.edit_files,
        "prompt": todo.prompt,
        "context": todo.context,
        "validation_command": todo.validation_command,
        "branch_name": todo.branch_name,
        "status": "pending",
    }


@mcp.tool()
@sync_to_async
def listExternalTask(status: str = "", page: int = 1, limit: int = 10) -> dict:
    """Todo一覧を取得する（ページング対応）

    Args:
        status: ステータスでフィルタリング（waiting, queued, running, completed, error, cancelled, timeout）
               空の場合はすべてのステータスを取得
        page: ページ番号（1から開始、デフォルト1）
        limit: 1ページあたりの件数（デフォルト10、最大100）

    Returns:
        todo一覧とページネーション情報

    Note:
        返り値は created_at の降順（新しい順）
    """
    # パラメータのバリデーション
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    if limit > 100:
        limit = 100

    todo_list = get_todo_list_or_create()

    # ベースクエリ
    todos = Todo.objects.filter(todo_list=todo_list).select_related("todo_list", "agent").order_by("-created_at")

    # ステータスでフィルタリング（ページネーション前の総件数用）
    if status:
        filtered_todos = todos.filter(status=status)
    else:
        filtered_todos = todos

    # 総件数を取得
    total_count = filtered_todos.count()

    # 総ページ数を計算
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    # ページネーション
    offset = (page - 1) * limit
    paginated_todos = filtered_todos[offset:offset + limit]

    # 優先度順にソート: running > queued > waiting > others
    paginated_todos = sorted(paginated_todos, key=sort_priority)

    # 結果を作成
    result = []
    for todo in paginated_todos:
        # promptを50文字程度に丸める
        prompt_preview = todo.prompt[:50] + "..." if len(todo.prompt) > 50 else todo.prompt

        result.append({
            "id": todo.id,
            "status": todo.status,
            "prompt": prompt_detail(todo.prompt),
            "prompt_preview": prompt_preview,
            "todo_list": {
                "id": todo.todo_list.id,
                "name": todo.todo_list.workdir,
            },
            "agent_name": todo.agent.name if todo.agent else None,
            "created_at": todo.created_at.isoformat() if todo.created_at else None,
            "updated_at": todo.updated_at.isoformat() if todo.updated_at else None,
        })

    return {
        "todos": result,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "limit": limit,
    }

def prompt_detail(prompt: str) -> str:
    """promptの詳細を返す（最初の100文字程度）"""
    if len(prompt) <= 100:
        return prompt
    return prompt[:100] + "..."


def sort_priority(todo) -> int:
    """ステータスに応じたソート優先度を返す

    Args:
        todo: Todo モデルインスタンス

    Returns:
        優先度（0=最優先、3=最低優先度）
    """
    priority_map = {
        "running": 0,
        "queued": 1,
        "waiting": 2,
    }
    return priority_map.get(todo.status, 3)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
