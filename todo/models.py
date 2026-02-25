from django.db import models


class TodoList(models.Model):
    """Todoリスト（リポジトリごとに分類）"""

    name = models.CharField(max_length=255, default="", help_text="リスト名")
    workdir = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.workdir


class Extension(models.Model):
    """外部拡張機能"""

    name = models.CharField(max_length=100, unique=True, help_text="拡張機能名")
    type = models.CharField(max_length=20, default="stdio", help_text="拡張機能タイプ")
    cmd = models.CharField(max_length=500, help_text="実行コマンド")
    args = models.JSONField(default=list, help_text="コマンド引数リスト")
    envs = models.JSONField(default=dict, help_text="環境変数マップ")
    timeout = models.IntegerField(default=300, help_text="タイムアウト秒数")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Agent(models.Model):
    """AIエージェントの設定"""

    name = models.CharField(max_length=100, unique=True, help_text="エージェント名")
    system_message = models.TextField(blank=True, help_text="システムメッセージ")
    extensions = models.ManyToManyField(Extension, blank=True, related_name="agents", help_text="使用する拡張機能")
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
        TIMEOUT = "timeout", "Timeout"
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
    title = models.CharField(max_length=255, default="", help_text="タスクのタイトル")
    system_prompt = models.TextField(blank=True, help_text="システムプロンプト")
    ref_files = models.JSONField(default=list, help_text="参照用ファイルリスト", blank=True)
    edit_files = models.JSONField(default=list, help_text="編集対象ファイルリスト", blank=True)
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
    timeout = models.IntegerField(default=3600, help_text="タイムアウト秒数")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    branch_name = models.CharField(max_length=255, default="")
    auto_stash = models.BooleanField(default=True, help_text="自動スタッシュ")
    keep_branch = models.BooleanField(default=False, help_text="ブランチを保持する")

    def __str__(self):
        return self.title if self.title else self.prompt[:50]
