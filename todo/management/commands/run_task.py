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
import re
import string
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from todo.emoji import select_emoji
from todo.models import Agent, Todo, TodoList


class LiteralDumper(yaml.SafeDumper):
    pass


def str_representer(dumper, data):
    if "\n" in data:
        # 改行を含む文字列は必ず | で出す
        return dumper.represent_scalar(
            "tag:yaml.org,2002:str",
            data,
            style="|",
        )
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str",
        data,
    )


LiteralDumper.add_representer(str, str_representer)


def sanitize_prompt(text: str) -> str:
    """
    文字列をjinja2テンプレートとして展開しても同等のものに変換する。
    具体的には、jinja2のテンプレート構文を開始する文字列をエスケープする。

    - {# → {{ "{#" }}
    - {% → {{ "{%" }}
    - {{ → {{ "{{" }}

    Args:
        text: エスケープ対象の文字列

    Returns:
        エスケープされた文字列
    """
    result = text
    # result = result.replace("{{", '{{ "{{" }}')
    # result = result.replace("{%", '{{ "{%" }}')
    # result = result.replace("{#", '{{ "{#" }}')
    ENDRAW_RE = re.compile(r"{%\s*-?\s*endraw\s*-?\s*%}")

    def repl(m):
        tag = m.group(0)
        return "{% endraw %}{% raw %}" + tag[:5] + "{% endraw %}{% raw %}" + tag[5:]

    result = ENDRAW_RE.sub(repl, result)
    result = result.replace("{% endraw %}", '{% endraw %}{{ "{" }}% endraw %}{% raw %}')
    return "{% raw %}" + result.replace("\r\n", "\n") + "{% endraw %}"


class Command(BaseCommand):
    help = "AIエージェントを実行してタスクを完了する"

    def add_arguments(self, parser):
        parser.add_argument("--todo-pk", type=int, help="実行するTodoのPK")
        parser.add_argument("--agent-pk", type=int, help="使用するAgentのPK（DBに保存された設定を使用）")
        parser.add_argument(
            "--worktree-root", type=str, default="~/work/worktrees", help="worktreeのルートディレクトリ"
        )
        parser.add_argument("--inplace", action="store_true", help="workdir内で実行する")
        parser.add_argument("--agent-quiet", action="store_true", help="AIエージェントの出力を表示しない")
        parser.add_argument("--dump-recipe", action="store_true", help="レシピファイルのみを出力して終了")

    def handle(
        self,
        todo_pk: int,
        agent_pk: int | None,
        worktree_root: str,
        inplace: bool,
        agent_quiet: bool,
        dump_recipe: bool = False,
        **options,
    ):
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
        else:
            agent = Agent.objects.all().first()
        assert agent is not None
        assert agent is not None

        self.stdout.write(self.style.SUCCESS("Using Agent: {}".format(agent.name)))

        # dump_recipe オプションが指定された場合はレシピのみ出力して終了
        if dump_recipe:
            recipe = self.build_recipe(todo, agent)
            print(recipe)
            return

        self.stdout.write(self.style.SUCCESS("Workdir: {}".format(workdir)))
        self.stdout.write(self.style.SUCCESS("Todo: {}...".format(todo.prompt[:50])))
        self.stdout.write(self.style.SUCCESS("Agent command: {}".format(agent)))

        # 1. Gitリポジトリかどうか確認
        if not self.is_git_repo(workdir):
            raise CommandError("{} はGitリポジトリではありません".format(workdir))

        # 2. 作業ディレクトリがクリーンか確認
        stash_id = None
        if inplace and (not self.is_clean(workdir)):
            if not todo.auto_stash:
                raise CommandError("{} はダーティです。変更をコミットしてください".format(workdir))
            self.stdout.write("作業ディレクトリはダーティです。stashします")
            stash_id = self.create_stash(workdir)

        try:
            # 3. ブランチ名生成（既存のbranch_nameがあれば再利用）
            branch_name = todo.branch_name if todo.branch_name else self.generate_branch_name()

            if inplace:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=workdir,
                )
                current_branch_name = result.stdout.strip()

                self.stdout.write("ブランチ作成: {}".format(branch_name))
                if self.check_branch_exists(workdir, branch_name):
                    if self.is_current_branch(workdir, branch_name):
                        pass
                    else:
                        subprocess.run(
                            ["git", "switch", branch_name], cwd=workdir, capture_output=True, text=True
                        )
                else:
                    self.stdout.write("ブランチ作成: {}".format(branch_name))
                    subprocess.run(["git", "switch", "-c", branch_name, "HEAD"], cwd=workdir, check=True)

                # 4. Resumeの場合：stashを復元
                if todo.stash_id:
                    self.restore_stash(workdir, todo.stash_id)
                    # stash_idをクリア
                    todo.stash_id = ""
                    todo.interrupted_files = []
                    todo.save(update_fields=["stash_id", "interrupted_files"])

                try:
                    # 5. 指示ファイル作成
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        recipe = self.build_recipe(todo, agent)
                        print(recipe)
                        f.write(recipe)
                        f.flush()

                        # 6. AIエージェント実行
                        stdout_output = self.run_agent(workdir, f.name, agent_quiet)

                        # 7. コミット
                        self.commit_changes(workdir, todo, stdout_output)

                finally:
                    if current_branch_name != branch_name:
                        subprocess.run(["git", "switch", current_branch_name], cwd=workdir, check=True)

            else:
                # 4. ブランチとworktree作成
                worktree_path = self.create_worktree(workdir, worktree_root, branch_name)

                # Resumeの場合：stashを復元
                if todo.stash_id:
                    self.restore_stash(worktree_path, todo.stash_id)
                    # stash_idをクリア
                    todo.stash_id = ""
                    todo.interrupted_files = []
                    todo.save(update_fields=["stash_id", "interrupted_files"])

                try:
                    # 5. 指示ファイル作成
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        f.write(self.build_recipe(todo, agent))
                        # 6. AIエージェント実行
                        stdout_output = self.run_agent(worktree_path, f.name, agent_quiet)

                        # 7. コミット
                        self.commit_changes(worktree_path, todo, stdout_output)

                finally:
                    # 8. worktree削除
                    self.cleanup_worktree(worktree_path, workdir)
        finally:
            if stash_id:
                self.restore_stash(workdir, stash_id)

        self.stdout.write(self.style.SUCCESS("完了しました"))

    def is_git_repo(self, path):
        """Gitリポジトリかどうか確認"""
        result = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, capture_output=True)
        return result.returncode == 0

    def is_clean(self, path):
        """作業ディレクトリがクリーンか確認"""
        result = subprocess.run(["git", "status", "--porcelain"], cwd=path, capture_output=True, text=True)
        return result.returncode == 0 and result.stdout.strip() == ""

    def generate_branch_name(self):
        """ブランチ名を生成"""
        now = datetime.now()
        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return "ai/{}/{}/{}".format(now.strftime("%Y-%m-%d/%H-%M-%S"), random_suffix)

    def is_current_branch(self, workdir, target_branch):
        try:
            # 現在のブランチ名を取得
            result = subprocess.run(
                ["git", "symbolic-ref", "--short", "HEAD"],
                cwd=workdir,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

            return result == target_branch
        except subprocess.CalledProcessError:
            # HEADがデタッチされている場合（ブランチにいない状態）などはエラーになる
            return False

    def check_branch_exists(self, workdir, branch_name):
        # --verify で存在確認、--quiet で出力を抑制
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name], cwd=workdir, capture_output=True, text=True
        )

        # 終了ステータスが 0 なら存在、それ以外なら存在しない
        return result.returncode == 0

    def create_worktree(self, workdir, worktree_root, branch_name):
        """ブランチとworktreeを作成"""
        # worktreeパスを生成
        rel_path = os.path.relpath(workdir, os.path.expanduser("~/"))
        path_slug = rel_path.replace("/", "-").replace(".", "")
        branch_slug = branch_name.replace("/", "-")
        worktree_path = os.path.join(worktree_root, "{}-{}".format(path_slug, branch_slug))

        # ブランチ作成
        if self.check_branch_exists(workdir, branch_name):
            if self.is_current_branch(workdir, branch_name):
                pass
            else:
                subprocess.run(["git", "switch", branch_name], cwd=workdir, capture_output=True, text=True)
        else:
            self.stdout.write("ブランチ作成: {}".format(branch_name))
            subprocess.run(["git", "branch", branch_name, "HEAD"], cwd=workdir, check=True)

        # worktree作成
        self.stdout.write("Worktree作成: {}".format(worktree_path))
        subprocess.run(["git", "worktree", "add", worktree_path, branch_name], cwd=workdir, check=True)

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
        if todo.ref_files:
            parts.append("## 参照用ファイル（読み込みのみ）")
            for f in todo.ref_files:
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
        yaml.dump(
            {
                "title": "タスク実行",
                "description": "",
                "instructions": sanitize_prompt(agent.system_message),
                "prompt": sanitize_prompt(self.build_instruction(todo)),
                "extensions": [{"type": "builtin", "name": "developer", "timeout": 300, "bundled": True}],
            },
            sio,
            allow_unicode=True,
            Dumper=LiteralDumper,
            sort_keys=False,
        )
        return sio.getvalue()

    def run_agent(self, worktree_path, recipe_file, agent_quiet):
        """AIエージェントを実行（stderrリアルタイム表示、stdoutを文字列として返す）"""
        self.stdout.write("AIエージェント実行中...")

        # 出力をため込むStringIO
        output_buffer = io.StringIO()

        cmd = ["goose", "run", "--recipe", recipe_file]
        if agent_quiet:
            cmd.append("-q")

        # Popenでstdout/stderrを別々に扱う
        process = subprocess.Popen(
            cmd,
            cwd=worktree_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # リアルタイムでstdout/stderrを出力
        import select
        import sys

        while True:
            # 読み込み可能なfdを監視
            reads = [process.stdout.fileno(), process.stderr.fileno()]
            readable, _, _ = select.select(reads, [], [])

            if process.stdout.fileno() in readable:
                line = process.stdout.readline()
                if line:
                    self.stdout.write(line, ending="")
                    output_buffer.write(line)

            if process.stderr.fileno() in readable:
                line = process.stderr.readline()
                if line:
                    self.stderr.write(line, ending="")

            # プロセスが終了した場合
            if process.poll() is not None:
                # 残りの出力を読み込む
                remaining_stdout = process.stdout.read()
                if remaining_stdout:
                    self.stdout.write(remaining_stdout, ending="")
                    output_buffer.write(remaining_stdout)

                remaining_stderr = process.stderr.read()
                if remaining_stderr:
                    self.stderr.write(remaining_stderr, ending="")
                break

        returncode = process.returncode

        if returncode != 0:
            self.stderr.write(
                self.style.ERROR("エージェントがエラーで終了しました（終了コード: {}）".format(returncode))
            )
            raise CommandError("エージェントがエラーで終了しました")

        # stdoutの内容を文字列として返す
        return output_buffer.getvalue()

    def commit_changes(self, worktree_path, todo, stdout_output):
        """変更をコミット"""
        # 変更を追加
        subprocess.run(["git", "add", "-A"], cwd=worktree_path, check=True)

        emoji = ":robot:"
        try:
            emoji = select_emoji(
                "\n".join(["# {}".format(todo.title), "# 修正内容", todo.prompt, "# 結果", stdout_output])
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR("絵文字選択エラー: {}".format(e)))
        message = todo.title or "AI Generated Update"
        if len(message) > 50:
            message = message[:47] + "..."

        # コミットメッセージ作成
        commit_msg = f"{emoji} {message}\n\n"
        commit_msg += "Todo ID: {}\n".format(todo.id)
        commit_msg += "Output: {}\n".format(stdout_output[-200:])
        # commit_msg += "Prompt: {}".format(todo.prompt[:100])

        # コミット
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg], cwd=worktree_path, capture_output=True, text=True
        )

        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("コミット完了"))
        else:
            self.stdout.write(self.style.WARNING("コミットする変更がありませんでした"))

        todo.output = stdout_output
        todo.save()

    def cleanup_worktree(self, worktree_path, workdir):
        """worktreeを削除"""
        self.stdout.write("Worktreeクリーンアップ...")
        subprocess.run(["git", "worktree", "remove", worktree_path], cwd=workdir, check=True)
        self.stdout.write(self.style.SUCCESS("Worktreeを削除しました"))

    def create_stash(self, workdir):
        self.stdout.write("Stash作成...")
        subprocess.run(["git", "stash", "push", "-u", "-m", "避難"], cwd=workdir, check=True)

        result = subprocess.run(
            ["git", "rev-parse", "stash@{0}"], cwd=workdir, capture_output=True, text=True
        )
        if result.returncode == 0:
            self.stdout.write(self.style.SUCCESS("Stashを作成しました"))
        else:
            self.stdout.write(self.style.WARNING("Stashに失敗しました"))
            raise Exception("Stashに失敗しました")

        return result.stdout.strip()

    def restore_stash(self, workdir, stash_hash):
        """stashを復元"""
        self.stdout.write("Stashを復元...")
        try:
            subprocess.run(["git", "stash", "pop", stash_hash], cwd=workdir, check=True)
            self.stdout.write(self.style.SUCCESS("Stashを復元しました"))
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Stashを復元できませんでした: {e}"))
            # stashが既に適用されている場合もある
            try:
                subprocess.run(["git", "stash", "drop", stash_hash], cwd=workdir, capture_output=True)
            except:
                pass
