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
from multiprocessing import Pipe, Process, Queue

from django.core.management import call_command
from django.core.management.base import BaseCommand

from todo.models import Todo


def run_task_in_subprocess(todo_pk: int, pipe, output_queue: Queue):
    """子プロセスでcall_commandを実行"""
    import sys
    import threading

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    # リアルタイム出力を親プロセスに送信するスレッド
    def stream_output(stream_name, stream):
        for line in stream:
            output_queue.put((stream_name, line))

    try:
        import io

        # 親プロセスのstdout/stderrを取得
        parent_stdout = sys.stdout
        parent_stderr = sys.stderr

        # pipe.writeをstdoutとして使用する
        call_command(
            "run_task",
            todo_pk=todo_pk,
            inplace=True,
            agent_quiet=True,
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
            # self.stdout.write("queuedのTodoがありません。待機中...")
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
        output_queue = Queue()

        process = Process(target=run_task_in_subprocess, args=(todo.pk, child_conn, output_queue))
        process.start()

        self.stdout.write(f"Todo #{todo.pk} を子プロセスで実行中 (PID: {process.pid})...")

        # 出力ためる用のバッファ
        stdout_lines = []
        stderr_lines = []

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

                # リアルタイムでQueueから出力を読み取り
                try:
                    while True:
                        try:
                            stream_name, line = output_queue.get_nowait()
                            # 親プロセスのstdout/stderrにリアルタイム出力
                            if stream_name == "stdout":
                                self.stdout.write(line, ending="")
                            else:
                                self.stderr.write(line, ending="")
                            # 結果ため込み
                            if stream_name == "stdout":
                                stdout_lines.append(line)
                            else:
                                stderr_lines.append(line)
                        except:
                            break
                except:
                    pass

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
                                self.stdout.write(line, ending="")
                            else:
                                self.stderr.write(line, ending="")
                            if stream_name == "stdout":
                                stdout_lines.append(line)
                            else:
                                stderr_lines.append(line)
                    except:
                        pass

                    result["stdout"] = "".join(stdout_lines)
                    result["stderr"] = "".join(stderr_lines)
                    self.handle_subprocess_result(todo, result)
                    break

                time.sleep(0.1)

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
