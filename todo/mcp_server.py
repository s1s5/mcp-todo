"""
Todo MCP Server
起動時のCWDと同じTodoListを使用してLLMがTodoを管理できる
"""
import os
import sys
import json
from pathlib import Path

# Djangoセットアップ
import django
from django.conf import settings

# settingsが未設定の場合のみ設定
if not settings.configured:
    BASE_DIR = Path(__file__).resolve().parent.parent
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'todo',
        ],
    )
    django.setup()

from todo.models import TodoList, Todo


def get_todo_list_or_create() -> TodoList:
    """CWDと同じTodoListを取得、なければ自動作成"""
    cwd = os.getcwd()
    todo_list, created = TodoList.objects.get_or_create(
        workdir=cwd,
        defaults={'repository': Path(cwd).name}
    )
    return todo_list


# FastMCPサーバーを作成
from mcp import FastMCP

mcp = FastMCP("todo-mcp")


@mcp.tool()
def pushTodo(
    files: list[str],
    edit_files: list[str],
    prompt: str,
    context: str = "",
    validation_command: str = ""
) -> dict:
    """新しいTodoを追加する
    
    Args:
        files: 参照用ファイルリスト
        edit_files: 編集対象ファイルリスト
        prompt: タスク内容
        context: 動的に注入するコンテキスト
        validation_command: 完了判断用コマンド
    
    Returns:
        追加されたTodoの情報
    """
    todo_list = get_todo_list_or_create()
    todo = Todo.objects.create(
        todo_list=todo_list,
        files=files,
        edit_files=edit_files,
        prompt=prompt,
        context=context,
        validation_command=validation_command,
        completed_at=False
    )
    return {
        "id": todo.id,
        "files": todo.files,
        "edit_files": todo.edit_files,
        "prompt": todo.prompt,
        "context": todo.context,
        "validation_command": todo.validation_command,
        "status": "pending"
    }


@mcp.tool()
def popTodo() -> dict:
    """未完了タスクを1件取得する（古い順）
    
    Returns:
        処理中のTodo情報。未完了タスクがない場合はメッセージのみ
    """
    todo_list = get_todo_list_or_create()
    todo = Todo.objects.filter(
        todo_list=todo_list,
        completed_at=False
    ).order_by('created_at').first()
    
    if todo is None:
        return {"message": "未完了のタスクはありません"}
    
    return {
        "id": todo.id,
        "files": todo.files,
        "edit_files": todo.edit_files,
        "prompt": todo.prompt,
        "context": todo.context,
        "validation_command": todo.validation_command,
        "status": "processing"
    }


@mcp.tool()
def completeTodo(todo_id: int, output: str) -> dict:
    """Todoを完了状態にする
    
    Args:
        todo_id: 完了するTodoのID（popTodoで取得したID）
        output: 処理結果/出力
    
    Returns:
        完了状态になったTodoの情報
    """
    todo = Todo.objects.get(id=todo_id)
    todo.completed_at = True
    todo.output = output
    todo.save()
    return {
        "id": todo.id,
        "status": "completed"
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
