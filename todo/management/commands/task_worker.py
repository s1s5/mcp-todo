"""
タスクワーカ：Django管理コマンド

Todoモデルのstatusがqueuedのものを一つずつ取り出し、
multiprocessingを使って子プロセスでcall_commandを実行する。

処理流程：
1. statusがqueuedのTodoを取得（最も古いもの）
2. statusをrunningに変更
3. call_commandをmultiprocessingの子プロセスで実行
4. 定期的にstatusを確認し、cancelledなら子プロセスを強制終了
5. 子プロセス終了後にstatusをcompleted/errorに設定
6. 1-5を無限ループで繰り返す
"""

import os
import time
from multiprocessing import Pipe, Process

from django.core.management import call_command
from django.core.management.base import BaseCommand

from todo.models import Todo


def run_task_in_subprocess(todo_pk: int, pipe):
    """子プロセスでcall_commandを実行"""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    import io
    import sys

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        call_command(
            "run_task",
            todo_pk=todo_pk,
            inplace=True,
            agent_quiet=True,
            stdout=stdout_buffer,
            stderr=stderr_buffer,
        )
        pipe.send({"returncode": 0, "stdout": stdout_buffer.getvalue(), "stderr": stderr_buffer.getvalue()})
    except Exception as e:
        pipe.send(
            {
                "returncode": 1,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": str(e),
            }
        )
    finally:
        pipe.close()


class Command(BaseCommand):
    help = "タスクワーカー：queuedのTodoを実行する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=2,
            help="ステータス確認の間隔（秒）",
        )

    def handle(self, interval: int, **options):
        self.stdout.write(self.style.SUCCESS("タスクワーカーを開始しました"))

        while True:
            self.process_next_todo(interval)

    def process_next_todo(self, interval: int):
        """次のTodoを取得して処理"""
        # statusがqueuedの最も古いTodoを取得
        try:
            todo = Todo.objects.filter(status=Todo.Status.QUEUED).order_by("created_at").first()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Todo取得エラー: {e}"))
            time.sleep(interval)
            return

        if todo is None:
            self.stdout.write("queuedのTodoがありません。待機中...")
            time.sleep(interval)
            return

        self.stdout.write(self.style.SUCCESS(f"Todo #{todo.id} を処理開始"))

        # ステータスをrunningに変更
        todo.status = Todo.Status.RUNNING
        todo.save()

        # multiprocessingで子プロセスを起動
        self.run_task_with_multiprocessing(todo, interval)

    def run_task_with_multiprocessing(self, todo: Todo, interval: int):
        """multiprocessingを使ってcall_commandを実行"""
        parent_conn, child_conn = Pipe()

        process = Process(target=run_task_in_subprocess, args=(todo.pk, child_conn))
        process.start()

        self.stdout.write(f"Todo #{todo.pk} を子プロセスで実行中 (PID: {process.pid})...")

        try:
            while True:
                # 定期的にステータスを確認
                todo.refresh_from_db()

                # cancelledチェック
                if todo.status == Todo.Status.CANCELLED:
                    self.stdout.write(self.style.WARNING(f"Todo #{todo.id} がcancelledされました"))
                    # 子プロセスを強制終了
                    process.terminate()
                    try:
                        process.join(timeout=5)
                    except:
                        process.kill()
                        process.join()

                    todo.status = Todo.Status.CANCELLED
                    todo.output = "=== CANCELLED ===\nCancelled by user"
                    todo.save()
                    return

                # プロセスが終了したか確認
                if not process.is_alive():
                    # 終了したら出力を取得
                    if parent_conn.poll():
                        result = parent_conn.recv()
                    else:
                        result = {"returncode": -1, "stdout": "", "stderr": ""}

                    self.handle_subprocess_result(todo, result)
                    break

                time.sleep(0.5)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"エラーが発生しました: {e}"))
            todo.status = Todo.Status.ERROR
            todo.output = f"""=== ERROR ===
{str(e)}
"""
            todo.save()

        finally:
            # プロセスがまだ生きている場合は終了させる
            if process.is_alive():
                process.terminate()
                try:
                    process.join(timeout=5)
                except:
                    process.kill()
                    process.join()

    def handle_subprocess_result(self, todo: Todo, result: dict):
        """子プロセスの結果を処理"""
        stdout_text = result.get("stdout", "")
        stderr_text = result.get("stderr", "")
        returncode = result.get("returncode", -1)
        error = result.get("error", "")

        full_output = f"""=== STDOUT ===
{stdout_text}

=== STDERR ===
{stderr_text}"
        if error:
            full_output += f"
=== ERROR ===
{error}"""

        todo.output = full_output

        if todo.status == Todo.Status.CANCELLED:
            todo.status = Todo.Status.CANCELLED
            self.stdout.write(self.style.WARNING(f"Todo #{todo.id} がcancelledされました"))
        elif returncode == 0:
            todo.status = Todo.Status.COMPLETED
            self.stdout.write(self.style.SUCCESS(f"Todo #{todo.id} が正常に完了しました"))
        else:
            todo.status = Todo.Status.ERROR
            self.stdout.write(
                self.style.ERROR(f"Todo #{todo.id} がエラーで終了しました（終了コード: {returncode}）")
            )

        todo.save()
