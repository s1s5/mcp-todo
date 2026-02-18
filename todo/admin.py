from django.contrib import admin
from .models import TodoList, Agent, Todo


@admin.register(TodoList)
class TodoListAdmin(admin.ModelAdmin):
    list_display = ['repository', 'workdir', 'created_at']
    search_fields = ['repository', 'workdir']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'command', 'created_at', 'updated_at']
    search_fields = ['name', 'command', 'system_message']


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ['id', 'todo_list', 'agent', 'prompt', 'completed_at', 'validation_command', 'created_at']
    search_fields = ['prompt', 'output', 'context']
    list_filter = ['completed_at', 'created_at', 'agent']
    filter_horizontal = []
