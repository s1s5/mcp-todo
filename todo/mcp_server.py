"""
Todo MCP Server
起動時のCWDと同じTodoListを使用してLLMがTodoを管理できる
"""

import os
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

def get_todo_list_or_create() -> TodoList:
    """CWDと同じTodoListを取得、なければ自動作成"""
    cwd = os.getcwd()
    todo_list, created = TodoList.objects.get_or_create(workdir=cwd, defaults={"repository": Path(cwd).name})
    return todo_list


def validate_path(workdir: str, file_path: str) -> str:
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
    real_resolved = os.path.realpath(os.path.dirname(resolved))

    # ファイル自体をチェック
    if not real_resolved.startswith(real_workdir):
        raise ValueError(f"workdir外のパスは指定できません: {file_path}")

    # ファイルが実際に存在するか確認
    if not os.path.exists(resolved):
        raise ValueError(f"ファイルが存在しません: {file_path}")

    # workdirからの相対パスを返す
    rel_path = os.path.relpath(resolved, workdir)
    return rel_path




@mcp.tool()
@sync_to_async
def pushExternalTask(
    ref_files: list[str], edit_files: list[str], prompt: str, context: str = "", validation_command: str = ""
) -> dict:
    """外部エージェントが実行する新しいタスクを追加する

    Args:
        ref_files: 参照用ファイルリスト（CWDからの相対パス）
        edit_files: 編集対象ファイルリスト（CWDからの相対パス）
        prompt: タスク内容
        context: 動的に注入するコンテキスト
        validation_command: 完了判断用コマンド

    Returns:
        追加されたタスクの情報

    Raises:
        ValueError: 無効なパスが指定された場合
    """
    todo_list = get_todo_list_or_create()
    workdir = todo_list.workdir

    # パスを検証して正規化
    validated_ref_files = []
    for f in ref_files:
        validated_ref_files.append(validate_path(workdir, f))

    validated_edit_files = []
    for f in edit_files:
        validated_edit_files.append(validate_path(workdir, f))

    todo = Todo.objects.create(
        todo_list=todo_list,
        ref_files=validated_ref_files,
        edit_files=validated_edit_files,
        prompt=prompt,
        context=context,
        validation_command=validation_command,
        completed_at=False,
    )
    return {
        "id": todo.id,
        "ref_files": todo.ref_files,
        "edit_files": todo.edit_files,
        "prompt": todo.prompt,
        "context": todo.context,
        "validation_command": todo.validation_command,
        "status": "pending",
    }


# @mcp.tool()
# def popTodo() -> dict:
#     """未完了タスクを1件取得する（古い順）
#
#     Returns:
#         処理中のTodo情報。未完了タスクがない場合はメッセージのみ
#     """
#     todo_list = get_todo_list_or_create()
#     todo = Todo.objects.filter(
#         todo_list=todo_list,
#         completed_at=False
#     ).order_by('created_at').first()
#
#     if todo is None:
#         return {"message": "未完了のタスクはありません"}
#
#     return {
#         "id": todo.id,
#         "ref_files": todo.ref_files,
#         "edit_files": todo.edit_files,
#         "prompt": todo.prompt,
#         "context": todo.context,
#         "validation_command": todo.validation_command,
#         "status": "processing"
#     }
#
#
# @mcp.tool()
# def completeTodo(todo_id: int, output: str) -> dict:
#     """Todoを完了状態にする
#
#     Args:
#         todo_id: 完了するTodoのID（popTodoで取得したID）
#         output: 処理結果/出力
#
#     Returns:
#         完了状态になったTodoの情報
#     """
#     todo = Todo.objects.get(id=todo_id)
#     todo.completed_at = True
#     todo.output = output
#     todo.save()
#     return {
#         "id": todo.id,
#         "status": "completed"
#     }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
