"""
AIエージェントを実行するDjango管理コマンド

使用方法:
    python manage.py run_task <todo_pk> [--agent-pk AGENT_PK] [--agent-cmd AGENT_CMD]

引数:
    todo_pk: 実行するTodoのPK

オプション:
    --agent-pk: 使用するAgentのPK（DBに保存されたエージェントを使用）
    --agent-cmd: 使用するAIエージェントコマンド (デフォルト: Agent設定または claude --dangerously-skip-permissions -p)
    --instruction: 指示ファイルのパス
    --prompt: 直接指示を渡す
    --worktree-root: worktreeのルートディレクトリ
"""

import io
import os
import random
import string
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from todo.models import Agent, Todo, TodoList


class Command(BaseCommand):
    help = "AIエージェントを実行してタスクを完了する"

    def add_arguments(self, parser):
        parser.add_argument("--todo-pk", type=int, help="実行するTodoのPK")
        parser.add_argument("--agent-pk", type=int, help="使用するAgentのPK（DBに保存された設定を使用）")
        parser.add_argument(
            "--worktree-root", type=str, default="~/work/worktrees", help="worktreeのルートディレクトリ"
        )

    def handle(self, todo_pk: int, agent_pk: int | None, **options):
        todo_pk = options["todo_pk"]
        agent_pk = options["agent_pk"]
        worktree_root = os.path.expanduser(options["worktree_root"])

        # Todo取得
        try:
            todo = Todo.objects.select_related("todo_list", "agent").get(pk=todo_pk)
        except Todo.DoesNotExist:
            raise CommandError("Todo {} が存在しません".format(todo_pk))

        todo_list = todo.todo_list
        workdir = todo_list.workdir

        # Agent解決: 引数 > Todo.agent > デフォルト
        agent = None

        if agent_pk:
            try:
                agent = Agent.objects.get(pk=agent_pk)
            except Agent.DoesNotExist:
                raise CommandError("Agent {} が存在しません".format(agent_pk))
        elif todo.agent:
            agent = todo.agent
        assert agent is not None

        self.stdout.write(self.style.SUCCESS("Using Agent: {}".format(agent.name)))

        self.stdout.write(self.style.SUCCESS("Workdir: {}".format(workdir)))
        self.stdout.write(self.style.SUCCESS("Todo: {}...".format(todo.prompt[:50])))
        self.stdout.write(self.style.SUCCESS("Agent command: {}".format(agent)))

        # 1. Gitリポジトリかどうか確認
        if not self.is_git_repo(workdir):
            raise CommandError("{} はGitリポジトリではありません".format(workdir))

        # 3. ブランチ名生成
        branch_name = self.generate_branch_name() if not todo.branch_name else todo.branch_name

        # 4. ブランチとworktree作成
        worktree_path = self.create_worktree(workdir, worktree_root, branch_name)

        try:
            # 5. 指示ファイル作成
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write(self.build_recipe(todo, agent))
                # 6. AIエージェント実行
                self.run_agent(worktree_path, f.name)

                # 7. コミット
                self.commit_changes(worktree_path, todo)

        finally:
            # 8. worktree削除
            self.cleanup_worktree(worktree_path, branch_name)

        self.stdout.write(self.style.SUCCESS("完了しました"))

    def is_git_repo(self, path):
        """Gitリポジトリかどうか確認"""
        result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, capture_output=True)
        return result.returncode == 0

    def generate_branch_name(self):
        """ブランチ名を生成"""
        now = datetime.now()
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return "ai/{}/{}/{}".format(now.strftime("%Y-%m-%d/%H-%M-%S"), random_suffix)

    def create_worktree(self, workdir, worktree_root, branch_name):
        """ブランチとworktreeを作成"""
        # worktreeパスを生成
        rel_path = os.path.relpath(workdir, os.path.expanduser("~/"))
        path_slug = rel_path.replace("/", "-").replace(".", "")
        branch_slug = branch_name.replace("/", "-")
        worktree_path = os.path.join(worktree_root, "{}-{}".format(path_slug, branch_slug))

        # ブランチ作成
        self.stdout.write("ブランチ作成: {}".format(branch_name))
        subprocess.run(["git", "branch", branch_name, "HEAD"], cwd=workdir, check=True)

        # worktree作成
        self.stdout.write("Worktree作成: {}".format(worktree_path))
        subprocess.run(["git", "worktree", "add", worktree_path, branch_name], check=True)

        return worktree_path

    def build_instruction(self, todo):
        """指示内容を構築"""
        parts = []

        # # システムメッセージ
        # if system_message:
        #     parts.append("## システムメッセージ")
        #     parts.append(system_message)
        #     parts.append("")

        # ファイル読み込み指示
        if todo.files:
            parts.append("## 参照用ファイル（読み込みのみ）")
            for f in todo.files:
                parts.append("- {}".format(f))
            parts.append("")

        if todo.edit_files:
            parts.append("## 編集対象ファイル")
            for f in todo.edit_files:
                parts.append("- {}".format(f))
            parts.append("")

        # コンテキスト
        if todo.context:
            parts.append("## コンテキスト")
            parts.append(todo.context)
            parts.append("")

        # プロンプト
        parts.append("## タスク")
        parts.append(todo.prompt)
        parts.append("")

        # validation_command
        if todo.validation_command:
            parts.append("## 完了判断")
            parts.append("次のコマンドが成功したら完了: `{}`".format(todo.validation_command))
            parts.append("")

        # # 追加指示（ファイルから）
        # if instruction_file and os.path.exists(instruction_file):
        #     with open(instruction_file) as f:
        #         parts.append("## 追加指示")
        #         parts.append(f.read())
        #     parts.append("")

        # # 追加指示（プロンプトから）
        # if prompt:
        #     parts.append("## 追加指示")
        #     parts.append(prompt)

        return "\n".join(parts)

    def build_recipe(self, todo: Todo, agent: Agent):
        sio = io.StringIO()
        yaml.safe_dump(
            {
                "title": "タスク実行",
                "description": "",
                "instructions": agent.system_message,
                "prompt": self.build_instruction(todo),
                "extensions": [{"type": "builtin", "name": "developer", "timeout": 300, "bundled": True}],
            },
            sio,
        )
        return sio.getvalue()

    def run_agent(self, worktree_path, recipe_file):
        """AIエージェントを実行"""
        self.stdout.write("AIエージェント実行中...")

        # エージェント実行
        result = subprocess.run(
            ["goose", "run", "--recipe", recipe_file],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            self.stderr.write(self.style.ERROR("エージェントエラー: {}".format(result.stderr)))

        self.stdout.write(result.stdout)

    def commit_changes(self, worktree_path, todo):
        """変更をコミット"""
        # 変更を追加
        subprocess.run(["git", "add", "-A"], cwd=worktree_path, check=True)

        # コミットメッセージ作成
        commit_msg = ":robot: AI Generated Update\n\n"
        commit_msg += "Todo ID: {}\n".format(todo.id)
        commit_msg += "Prompt: {}".format(todo.prompt[:100])

        # コミット
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg], cwd=worktree_path, capture_output=True, text=True
        )

        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("コミット完了"))
        else:
            self.stdout.write(self.style.WARNING("コミットする変更がありませんでした"))

    def cleanup_worktree(self, worktree_path, branch_name):
        """worktreeを削除"""
        self.stdout.write("Worktreeクリーンアップ...")
        subprocess.run(["git", "worktree", "remove", worktree_path], check=True)
        self.stdout.write(self.style.SUCCESS("Worktreeを削除しました"))
