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
import time
from multiprocessing import Pipe, Process, Queue

from django.core.management import call_command
from django.core.management.base import BaseCommand

from todo.models import Todo


def run_task_in_subprocess(todo_pk: int, pipe, output_queue: Queue):
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

    def handle(self, interval: int, **options):
        self.stdout.write(self.style.SUCCESS("タスクワーカーを開始しました"))
        self.running_workdirs = {}

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
                todos = Todo.objects.filter(
                    status=Todo.Status.QUEUED
                ).exclude(
                    todo_list__workdir__in=running_workdir_list
                ).order_by("-priority", "created_at")
            else:
                todos = Todo.objects.filter(
                    status=Todo.Status.QUEUED
                ).order_by("-priority", "created_at")
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

        # 3. 空いているworkdirがあれば新しいTodoを起動
        self.start_todo(next_todo)

    def check_running_processes(self):
        """実行中のプロセスをチェックし、終了/cancelled/timeoutしたら回収"""
        finished_workdirs = []

        for workdir, info in self.running_workdirs.items():
            process = info['process']
            todo = info['todo']
            start_time = info['start_time']
            parent_conn = info['parent_conn']
            output_queue = info['output_queue']
            stdout_lines = info['stdout_lines']
            stderr_lines = info['stderr_lines']
            timeout_seconds = todo.timeout

            try:
                # DBから最新の状態を取得
                todo.refresh_from_db()

                # cancelledチェック
                if todo.status == Todo.Status.CANCELLED:
                    self.stdout.write(self.style.WARNING(f"Todo #{todo.id} (workdir: {workdir}) がcancelledされました"))
                    self.terminate_process(process)
                    todo.output = "=== CANCELLED ===\nCancelled by user"
                    todo.save()
                    finished_workdirs.append(workdir)
                    continue

                # タイムアウトチェック
                elapsed = time.time() - start_time
                if elapsed >= timeout_seconds:
                    self.stdout.write(self.style.ERROR(f"Todo #{todo.id} (workdir: {workdir}) がタイムアウトしました（{timeout_seconds}秒）"))
                    self.terminate_process(process)
                    todo.status = Todo.Status.TIMEOUT
                    todo.output = f"=== TIMEOUT ===\nTimed out after {timeout_seconds} seconds"
                    todo.save()
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
                    self.handle_subprocess_result(todo, result)
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

        self.stdout.write(self.style.SUCCESS(f"Todo #{todo.id} を処理開始 (workdir: {workdir})"))
        self.stdout.write(f"  タイムアウト: {todo.timeout}秒")

        # ステータスをrunningに変更
        todo.status = Todo.Status.RUNNING
        todo.save()

        # multiprocessingで子プロセスを起動
        self.run_task_with_multiprocessing(todo, workdir)

    def run_task_with_multiprocessing(self, todo: Todo, workdir: str):
        """multiprocessingを使ってcall_commandを実行"""
        parent_conn, child_conn = Pipe()
        output_queue = Queue()

        process = Process(target=run_task_in_subprocess, args=(todo.pk, child_conn, output_queue))
        process.start()

        self.stdout.write(f"Todo #{todo.pk} を子プロセスで実行中 (PID: {process.pid}, workdir: {workdir})...")

        # running_workdirsに追加
        self.running_workdirs[workdir] = {
            'process': process,
            'todo': todo,
            'start_time': time.time(),
            'parent_conn': parent_conn,
            'output_queue': output_queue,
            'stdout_lines': [],
            'stderr_lines': [],
        }

    def handle_subprocess_result(self, todo: Todo, result: dict):
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
            self.stdout.write(self.style.WARNING(f"Todo #{todo.id} がcancelledされました"))
        elif returncode == 0:
            todo.status = Todo.Status.COMPLETED
            self.stdout.write(self.style.SUCCESS(f"Todo #{todo.id} が正常に完了しました"))
        else:
            todo.output = full_output
            todo.status = Todo.Status.ERROR
            self.stdout.write(
                self.style.ERROR(f"Todo #{todo.id} がエラーで終了しました（終了コード: {returncode}）")
            )

        todo.save()
