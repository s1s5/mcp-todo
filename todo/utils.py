"""
Todo関連のユーティリティ関数
"""

import os
from pathlib import Path
from typing import Optional

from .models import TodoList


def is_git_worktree(workdir: str) -> bool:
    """指定されたパスがgit worktreeかどうかを判定する
    
    - .git ファイルが存在し、内容が gitdir: を参照している場合はworktree
    
    Args:
        workdir: 判定対象のパス
        
    Returns:
        bool: worktreeの場合はTrue、通常のリポジトリの場合はFalse
    """
    git_path = os.path.join(workdir, ".git")
    
    # .git がファイルで存在する場合は worktree
    if os.path.isfile(git_path):
        try:
            with open(git_path, "r") as f:
                content = f.read().strip()
                return content.startswith("gitdir:")
        except (IOError, OSError):
            return False
    
    return False


def get_parent_workdir(workdir: str) -> Optional[str]:
    """worktreeの母親repositoryのworkdirを返す
    
    - worktreeではない通常のリポジトリならNone
    - 母親repositoryが見つからなければNone
    
    Args:
        workdir: worktreeのパス
        
    Returns:
        str | None: 母親repositoryのworkdir、またはNone
    """
    if not is_git_worktree(workdir):
        return None
    
    git_path = os.path.join(workdir, ".git")
    
    try:
        with open(git_path, "r") as f:
            content = f.read().strip()
            
        if not content.startswith("gitdir:"):
            return None
        
        # gitdir: の後ろのパスを取得
        gitdir = content[8:].strip()  # "gitdir: " を除去
        
        # 絶対パスの場合と相対パスがある場合
        if os.path.isabs(gitdir):
            # 絶対パスから .git のあるディレクトリを逆算
            git_dir = gitdir
        else:
            # 相対パスの場合
            git_dir = os.path.join(workdir, gitdir)
        
        # .git のある場所（worktreeの場合は .git ファイル、中身は actual の .git ディレクトリへのポインタ）
        actual_git_dir = os.path.dirname(git_dir)
        
        # 母親repositoryのworkdirは、actual_git_dir の1つ上のディレクトリ
        # ただし、actual_git_dir が .git ディレクトリ itself の場合がある
        if os.path.basename(actual_git_dir) == ".git":
            parent_workdir = os.path.dirname(actual_git_dir)
        else:
            # ポインタファイルが別の場所にある場合の考慮
            # 通常は workdir の親ディレクトリを辿って通常のリポジトリを探す
            parent_workdir = find_main_repository(workdir)
        
        if parent_workdir and os.path.exists(parent_workdir):
            return parent_workdir
        
        return None
        
    except (IOError, OSError):
        return None


def find_main_repository(workdir: str) -> Optional[str]:
    """親ディレクトリを辿って通常のリポジトリ（.gitディレクトリを持つ）を探す
    
    Args:
        workdir: 起点となるパス
        
    Returns:
        str | None: 通常のリポジトリのworkdir、またはNone
    """
    current = os.path.abspath(workdir)
    
    # 親ディレクトリを辿る上限
    for _ in range(20):  # 最大20階層
        parent = os.path.dirname(current)
        
        # ルートに達した場合
        if parent == current:
            break
        
        git_dir = os.path.join(current, ".git")
        
        # .git がディレクトリとして存在する場合は通常のリポジトリ
        if os.path.isdir(git_dir):
            return current
        
        current = parent
    
    return None


def get_or_create_todolist_with_parent(workdir: str) -> tuple[TodoList, bool]:
    """TodoListを取得または作成し、worktreeの場合はparentを設定する
    
    - worktreeの場合、母親repositoryのTodoListを親として設定
    - 母親repositoryのTodoListがなければ新規作成
    
    Args:
        workdir: TodoListのworkdir
        
    Returns:
        tuple[TodoList, bool]: (todo_list, created: bool)
    """
    # worktreeかどうかを判定
    if is_git_worktree(workdir):
        # 母親repositoryのworkdirを取得
        parent_workdir = get_parent_workdir(workdir)
        
        if parent_workdir:
            # 母親repositoryのTodoListを取得または作成
            parent_todolist, parent_created = TodoList.objects.get_or_create(
                workdir=parent_workdir
            )
            
            # 自分のTodoListを取得または作成
            todo_list, created = TodoList.objects.get_or_create(workdir=workdir)
            
            # parentを設定（既に設定されている場合は更新しない）
            if todo_list.parent is None:
                todo_list.parent = parent_todolist
                todo_list.save()
            
            return todo_list, created
    
    # 通常のリポジトリまたはworktree判定に失敗した場合
    return TodoList.objects.get_or_create(workdir=workdir)
