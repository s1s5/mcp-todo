"""
タスクワーカ：Django管理コマンド

Todoモデルのstatusがqueuedのものを一つずつ取り出し、
multiprocessingを使って子プロセスでcall_commandを実行する。

todo_list.workdirごとに1つずつ実行可能とし、異なるworkdirのTodoは並列実行できる。

処理流程：
1. 実行中のworkdirを確認し、終了/cancelled/timeoutしたら回収
2. 実行中でないworkdirのqueuedのTodoを取得（最も古いもの）
3. statusをrunningに変更
4. call_commandをmultiprocessingの子プロセスで実行
5. 子プロセス終了後にstatusをcompleted/errorに設定
6. 1-5を無限ループで繰り返す
"""

import os
import subprocess
import time
from multiprocessing import Pipe, Process, Queue

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from todo.models import Todo


def run_task_in_subprocess(todo_pk: int, pipe, output_queue: Queue, worktree_root: str):
    """子プロセスでcall_commandを実行"""
    import sys

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    try:
        # 親プロセスのstdout/stderrを取得
        parent_stdout = sys.stdout
        parent_stderr = sys.stderr

        # pipe.writeをstdoutとして使用する
        call_command(
            "run_task",
            todo_pk=todo_pk,
            inplace=True,
            worktree_root=worktree_root,
            # agent_quiet=True,
            stdout=parent_stdout,
            stderr=parent_stderr,
        )
        pipe.send({"returncode": 0})
    except Exception as e:
        pipe.send(
            {
                "returncode": 1,
                "error": str(e),
            }
        )
    finally:
        pipe.close()


class Command(BaseCommand):
    help = "タスクワーカー：queuedのTodoを実行する"

    # workdirごとの実行情報
    # workdir -> {'process': Process, 'todo': Todo, 'start_time': float, 'parent_conn': Pipe, 'output_queue': Queue, 'stdout_lines': list, 'stderr_lines': list}
    running_workdirs: dict

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=2,
            help="ステータス確認の間隔（秒）",
        )
        parser.add_argument(
            "--worktree-root",
            type=str,
            default="~/work/worktrees",
            help="worktreeのルートディレクトリ",
        )
        parser.add_argument(
            "--max-parallel",
            type=int,
            default=None,
            help="最大並列実行数（環境変数TASK_WORKER_MAX_PARALLELでデフォルト値5を設定可能）",
        )

    def handle(self, interval: int, worktree_root: str, max_parallel: int, **options):
        self.stdout.write(self.style.SUCCESS("タスクワーカーを開始しました"))
        self.running_workdirs = {}
        self.worktree_root = os.path.expanduser(worktree_root)

        # 環境変数またはCLI引数から最大並列数を取得
        self.max_parallel = (
            max_parallel if max_parallel is not None else int(os.environ.get("TASK_WORKER_MAX_PARALLEL", "5"))
        )

        while True:
            self.process_loop(interval)

    def process_loop(self, interval: int):
        """メインループ：実行中プロセスをチェックし、新しいTodoを起動"""
        # 1. 実行中のプロセスをチェックし、終了/cancelled/timeoutしたら回収
        self.check_running_processes()

        # 2. 実行中のworkdirを除いたqueuedのTodoを priority降順・created昇順で取得
        try:
            running_workdir_list = list(self.running_workdirs.keys())
            if running_workdir_list:
                todos = (
                    Todo.objects.filter(status=Todo.Status.QUEUED)
                    .exclude(todo_list__workdir__in=running_workdir_list)
                    .order_by("-priority", "created_at")
                )
            else:
                todos = Todo.objects.filter(status=Todo.Status.QUEUED).order_by("-priority", "created_at")
            next_todo = todos.first()
        except Exception as e:
            import traceback

            self.stdout.write(self.style.ERROR(f"Todo取得エラー: {e}"))
            self.stdout.write(traceback.format_exc())
            time.sleep(interval)
            return

        if next_todo is None:
            time.sleep(interval)
            return

        # 最大並列数に達している場合は実行しない
        if len(self.running_workdirs) >= self.max_parallel:
            time.sleep(interval)
            return

        # 3. 空いているworkdirがあれば新しいTodoを起動
        self.start_todo(next_todo)

    def get_interrupted_files(self, worktree_path: str) -> list:
        """変更ファイルリストを取得（stash保存前）"""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        if not result.stdout.strip():
            return []

        files = []
        for line in result.stdout.strip().split("\n"):
            if line:
                # "M  file.py" → {"status": "M", "path": "file.py"}
                status = line[:2].strip()
                filepath = line[3:].strip()
                files.append({
                    "status": status,
                    "path": filepath
                })

        return files

    def save_to_stash(self, worktree_path: str, workdir: str, todo: Todo) -> str | None:
        """未コミットの変更をstashに保存し、stash IDを返す"""
        # 変更があるか確認
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        if not result.stdout.strip():
            return None  # 変更なし

        # stashに保存
        stash_msg = f"todo-{todo.id}-interrupted"
        subprocess.run(
            ["git", "stash", "push", "-u", "-m", stash_msg],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )

        # stash IDを取得
        result = subprocess.run(
            ["git", "rev-parse", "stash@{0}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout.strip()

    def handle_interruption(self, worktree_path: str, workdir: str, todo: Todo):
        """中断処理: 変更ファイル取得 → stash保存 → worktree削除 → DB更新"""
        stash_id = None
        interrupted_files = []

        if worktree_path and os.path.exists(worktree_path):
            # 1. 変更ファイルリストを取得（stash保存前）
            interrupted_files = self.get_interrupted_files(worktree_path)

            # 2. stashに保存
            if interrupted_files:
                stash_id = self.save_to_stash(worktree_path, workdir, todo)

            # 3. worktreeを削除
            self.cleanup_worktree(worktree_path, workdir)

        # 4. DBを更新
        todo.stash_id = stash_id or ""
        todo.interrupted_files = interrupted_files
        todo.save(update_fields=["stash_id", "interrupted_files"])

        return stash_id, interrupted_files

    def check_running_processes(self):
        """実行中のプロセスをチェックし、終了/cancelled/timeoutしたら回収"""
        finished_workdirs = []

        for workdir, info in self.running_workdirs.items():
            process = info["process"]
            todo = info["todo"]
            start_time = info["start_time"]
            parent_conn = info["parent_conn"]
            output_queue = info["output_queue"]
            stdout_lines = info["stdout_lines"]
            stderr_lines = info["stderr_lines"]
            timeout_seconds = todo.timeout
            worktree_path = info.get("worktree_path")

            try:
                # DBから最新の状態を取得
                todo.refresh_from_db()

                # cancelledチェック
                if todo.status == Todo.Status.CANCELLED:
                    self.stdout.write(
                        self.style.WARNING(f"Todo #{todo.id} (workdir: {workdir}) がcancelledされました")
                    )
                    self.terminate_process(process)

                    # stash保存 + worktree削除 + DB更新
                    stash_id, files = self.handle_interruption(worktree_path, workdir, todo)

                    todo.output = "=== CANCELLED ===\nCancelled by user"
                    if stash_id:
                        todo.output += f"\nStash saved: {stash_id}"
                    if files:
                        todo.output += f"\nInterrupted files: {len(files)} files"
                    todo.save(update_fields=["output"])
                    finished_workdirs.append(workdir)
                    continue

                # タイムアウトチェック
                elapsed = time.time() - start_time
                if elapsed >= timeout_seconds:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Todo #{todo.id} (workdir: {workdir}) がタイムアウトしました（{timeout_seconds}秒）"
                        )
                    )
                    self.terminate_process(process)

                    # stash保存 + worktree削除 + DB更新
                    stash_id, files = self.handle_interruption(worktree_path, workdir, todo)

                    todo.status = Todo.Status.TIMEOUT
                    todo.output = f"=== TIMEOUT ===\nTimed out after {timeout_seconds} seconds"
                    if stash_id:
                        todo.output += f"\nStash saved: {stash_id}"
                    if files:
                        todo.output += f"\nInterrupted files: {len(files)} files"
                    todo.save(update_fields=["status", "output"])
                    finished_workdirs.append(workdir)
                    continue

                # プロセスが終了したか確認
                if not process.is_alive():
                    # 終了したら出力を取得
                    if parent_conn.poll():
                        result = parent_conn.recv()
                    else:
                        result = {"returncode": -1, "stdout": "", "stderr": ""}

                    # 残りの出力をフラッシュ
                    try:
                        while True:
                            stream_name, line = output_queue.get_nowait()
                            if stream_name == "stdout":
                                stdout_lines.append(line)
                            else:
                                stderr_lines.append(line)
                    except:
                        pass

                    result["stdout"] = "".join(stdout_lines)
                    result["stderr"] = "".join(stderr_lines)
                    self.handle_subprocess_result(todo, result, worktree_path, workdir)
                    finished_workdirs.append(workdir)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"プロセス確認中にエラー発生 (workdir: {workdir}): {e}"))
                finished_workdirs.append(workdir)

        # 完了したworkdirを削除
        for workdir in finished_workdirs:
            if workdir in self.running_workdirs:
                del self.running_workdirs[workdir]

    def terminate_process(self, process):
        """プロセスを終了させる"""
        if process.is_alive():
            process.terminate()
            try:
                process.join(timeout=5)
            except:
                process.kill()
                process.join()

    def start_todo(self, todo: Todo):
        """新しいTodoを起動"""
        workdir = todo.todo_list.workdir

        # branch_name が未設定の場合は生成して保存
        if not todo.branch_name:
            import random
            import string
            from datetime import datetime

            now = datetime.now()
            random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
            todo.branch_name = "ai/{}/{}".format(now.strftime("%Y-%m-%d/%H-%M-%S"), random_suffix)
            todo.save(update_fields=["branch_name"])

        self.stdout.write(self.style.SUCCESS(f"Todo #{todo.id} を処理開始 (workdir: {workdir})"))
        self.stdout.write(f"  ブランチ: {todo.branch_name}")
        self.stdout.write(f"  タイムアウト: {todo.timeout}秒")

        # ステータスをrunningに変更
        todo.status = Todo.Status.RUNNING
        todo.started_at = timezone.now()
        todo.save(update_fields=["status", "started_at"])

        # multiprocessingで子プロセスを起動
        self.run_task_with_multiprocessing(todo, workdir)

    def run_task_with_multiprocessing(self, todo: Todo, workdir: str):
        """multiprocessingを使ってcall_commandを実行"""
        parent_conn, child_conn = Pipe()
        output_queue = Queue()

        # worktree パスを計算して保存
        worktree_path = self.get_worktree_path(workdir, todo.branch_name)

        process = Process(
            target=run_task_in_subprocess, args=(todo.pk, child_conn, output_queue, self.worktree_root)
        )
        process.start()

        self.stdout.write(
            f"Todo #{todo.pk} を子プロセスで実行中 (PID: {process.pid}, workdir: {workdir}, worktree: {worktree_path})..."
        )

        # running_workdirsに追加
        self.running_workdirs[workdir] = {
            "process": process,
            "todo": todo,
            "start_time": time.time(),
            "parent_conn": parent_conn,
            "output_queue": output_queue,
            "stdout_lines": [],
            "stderr_lines": [],
            "worktree_path": worktree_path,
        }

    def handle_subprocess_result(self, todo: Todo, result: dict, worktree_path: str = None, workdir: str = None):
        """子プロセスの結果を処理"""
        stdout_text = result.get("stdout", "")
        stderr_text = result.get("stderr", "")
        returncode = result.get("returncode", -1)
        error = result.get("error", "")

        full_output = f"""=== STDOUT ===
{stdout_text}

=== STDERR ===
{stderr_text}"""
        if error:
            full_output += f"""
=== ERROR ===
{error}"""

        if todo.status == Todo.Status.CANCELLED:
            todo.output = full_output
            todo.status = Todo.Status.CANCELLED
            todo.finished_at = timezone.now()
            self.stdout.write(self.style.WARNING(f"Todo #{todo.id} がcancelledされました"))
        elif returncode == 0:
            todo.status = Todo.Status.COMPLETED
            todo.finished_at = timezone.now()
            self.stdout.write(self.style.SUCCESS(f"Todo #{todo.id} が正常に完了しました"))
        else:
            # エラー終了：stash保存を試みる
            stash_id = None
            interrupted_files = []
            if worktree_path and os.path.exists(worktree_path):
                interrupted_files = self.get_interrupted_files(worktree_path)
                if interrupted_files:
                    stash_id = self.save_to_stash(worktree_path, workdir, todo)
                    self.cleanup_worktree(worktree_path, workdir)

            todo.output = full_output
            todo.status = Todo.Status.ERROR
            todo.finished_at = timezone.now()
            todo.stash_id = stash_id or ""
            todo.interrupted_files = interrupted_files
            self.stdout.write(
                self.style.ERROR(f"Todo #{todo.id} がエラーで終了しました（終了コード: {returncode}）")
            )
            if stash_id:
                self.stdout.write(self.style.WARNING(f"Stash saved: {stash_id}"))

        todo.save(update_fields=["status", "output", "finished_at", "stash_id", "interrupted_files"])

    def get_worktree_path(self, workdir: str, branch_name: str) -> str:
        """worktree パスを計算する

        run_task.py の create_worktree メソッドと 동일한 로직
        """
        rel_path = os.path.relpath(workdir, os.path.expanduser("~/"))
        path_slug = rel_path.replace("/", "-").replace(".", "")
        branch_slug = branch_name.replace("/", "-")
        return os.path.join(self.worktree_root, "{}-{}".format(path_slug, branch_slug))

    def cleanup_worktree(self, worktree_path: str, workdir: str):
        """worktree を削除する

        run_task.py の cleanup_worktree 메서드와 동등한 처리
        """
        self.stdout.write(f"Worktree クリーンアップ: {worktree_path}")
        try:
            # worktree が存在するかをチェック
            if os.path.exists(worktree_path):
                subprocess.run(
                    ["git", "worktree", "remove", worktree_path],
                    cwd=workdir,
                    check=True,
                    capture_output=True,
                )
                self.stdout.write(self.style.SUCCESS(f"Worktreeを削除しました: {worktree_path}"))
            else:
                self.stdout.write(self.style.WARNING(f"Worktreeが存在しません: {worktree_path}"))
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"Worktree削除に失敗しました: {e.stderr}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Worktree削除中にエラー発生: {e}"))
