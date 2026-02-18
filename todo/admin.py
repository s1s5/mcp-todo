from django.contrib import admin

from .models import Agent, Todo, TodoList


@admin.register(TodoList)
class TodoListAdmin(admin.ModelAdmin):
    list_display = ["workdir", "created_at"]
    search_fields = ["workdir"]


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]
    search_fields = ["name", "system_message"]


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ["id", "todo_list", "agent", "prompt", "completed_at", "validation_command", "created_at"]
    search_fields = ["prompt", "output", "context"]
    list_filter = ["completed_at", "created_at", "agent"]
    filter_horizontal = []
