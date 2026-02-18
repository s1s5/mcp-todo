from django.contrib import admin
from .models import TodoList, Todo


@admin.register(TodoList)
class TodoListAdmin(admin.ModelAdmin):
    list_display = ['repository', 'workdir', 'created_at']
    search_fields = ['repository', 'workdir']


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ['id', 'todo_list', 'prompt', 'completed_at', 'validation_command', 'created_at']
    search_fields = ['prompt', 'output', 'context']
    list_filter = ['completed_at', 'created_at']
    filter_horizontal = []
