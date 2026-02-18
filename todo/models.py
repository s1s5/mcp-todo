from django.db import models


class TodoList(models.Model):
    """Todoリスト（リポジトリごとに分類）"""
    repository = models.CharField(max_length=255)
    workdir = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.repository


class Todo(models.Model):
    """個別のTodoタスク"""
    todo_list = models.ForeignKey(
        TodoList,
        on_delete=models.CASCADE,
        related_name='todos'
    )
    files = models.JSONField(default=list)
    prompt = models.TextField()
    completed_at = models.BooleanField(default=False)
    output = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.prompt[:50]
