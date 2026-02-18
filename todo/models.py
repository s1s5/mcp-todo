from django.db import models


class TodoList(models.Model):
    """Todoリスト（リポジトリごとに分類）"""

    workdir = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.workdir


class Agent(models.Model):
    """AIエージェントの設定"""

    name = models.CharField(max_length=100, unique=True, help_text="エージェント名")
    system_message = models.TextField(blank=True, help_text="システムメッセージ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Todo(models.Model):
    """個別のTodoタスク"""

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        ERROR = "error", "Error"

    todo_list = models.ForeignKey(TodoList, on_delete=models.CASCADE, related_name="todos")
    agent = models.ForeignKey(
        Agent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
        help_text="使用するエージェント",
    )
    ref_files = models.JSONField(default=list, help_text="参照用ファイルリスト")
    edit_files = models.JSONField(default=list, help_text="編集対象ファイルリスト")
    prompt = models.TextField(help_text="タスク内容")
    context = models.TextField(blank=True, help_text="動的に注入するコンテキスト")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
        help_text="タスクのステータス",
    )
    output = models.TextField(null=True, blank=True, help_text="実行結果")
    validation_command = models.CharField(max_length=500, blank=True, help_text="完了判断用コマンド")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    branch_name = models.CharField(max_length=255, default="")

    def __str__(self):
        return self.prompt[:50]
