"""
Todo MCP Server (REST API版)
REST API経由でTodoを作成するようにしたバージョン
"""

import os
import uuid
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("todo-mcp-rest")

# REST APIのベースURL（環境変数またはデフォルト）
API_BASE_URL = os.environ.get("DJANGO_API_URL", "http://localhost:8000/api")


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
    import os

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


def get_workdir() -> str:
    """現在の作業ディレクトリを取得"""
    return os.getcwd()


@mcp.tool()
def pushExternalTask(
    ref_files: list[str],
    edit_files: list[str],
    prompt: str,
    context: str = "",
    validation_command: str = "",
    branch: str = "",
) -> dict:
    """外部エージェントが実行する新しいタスクを追加する（REST API経由）

    Args:
        ref_files: 参照用ファイルリスト（CWDからの相対パス）
        edit_files: 編集対象ファイルリスト（CWDからの相対パス）
        prompt: タスク内容
        context: 動的に注入するコンテキスト
        validation_command: 完了判断用コマンド
        branch: ブランチ名（英数字、ハイフン、アンダースコアのみ）

    Returns:
        追加されたタスクの情報

    Raises:
        ValueError: 無効なパスまたはブランチ名が指定された場合
    """
    workdir = get_workdir()

    # ブランチ名を検証
    validated_branch = validate_branch_name(branch)

    # パスを検証して正規化
    validated_ref_files = []
    for f in ref_files:
        validated_ref_files.append(validate_path(workdir, f, True))

    validated_edit_files = []
    for f in edit_files:
        validated_edit_files.append(validate_path(workdir, f, False))

    # ブランチ名の生成
    branch_name = "" if validated_branch == "" else f"ai/{validated_branch}-{uuid.uuid4().hex[:6]}"

    # REST APIにPOSTリクエスト
    payload = {
        "workdir": workdir,
        "ref_files": validated_ref_files,
        "edit_files": validated_edit_files,
        "prompt": prompt,
        "context": context,
        "validation_command": validation_command,
        "branch_name": branch_name,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE_URL}/todos/", json=payload)
            response.raise_for_status()
            result = response.json()
            return {
                "id": result.get("id"),
                "ref_files": result.get("ref_files"),
                "edit_files": result.get("edit_files"),
                "prompt": result.get("prompt"),
                "context": result.get("context"),
                "validation_command": result.get("validation_command"),
                "branch_name": result.get("branch_name"),
                "status": result.get("status"),
            }
    except httpx.HTTPError as e:
        return {
            "error": f"APIリクエストに失敗しました: {str(e)}",
            "details": "Djangoサーバーが起動していることを確認してください",
        }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
