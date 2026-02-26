from rest_framework import serializers

from .models import Agent, Extension, Todo, TodoList


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["id", "name", "system_message", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class TodoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoList
        fields = ["id", "name", "workdir", "created_at"]  # nameを追加
        read_only_fields = ["created_at"]


class TodoSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True, allow_null=True)
    workdir = serializers.CharField(source="todo_list.workdir", read_only=True)
    todo_list_name = serializers.CharField(source="todo_list.name", read_only=True)  # 追加
    system_prompt = serializers.CharField(source="agent.system_prompt", read_only=True, allow_null=True)
    auto_stash = serializers.BooleanField(required=False, default=True)
    keep_branch = serializers.BooleanField(required=False, default=False)

    # 明示的なフィールド定義（allow_blank対応）
    context = serializers.CharField(required=False, allow_blank=True, allow_null=False, default="")
    validation_command = serializers.CharField(required=False, allow_blank=True, allow_null=False, default="")

    class Meta:
        model = Todo
        fields = [
            "id",
            "todo_list",
            "workdir",  # todo_list経由で参照（読み取り専用）
            "agent",
            "agent_name",
            "todo_list_name",  # 追加
            "title",
            "ref_files",
            "edit_files",
            "prompt",
            "status",
            "output",
            "timeout",
            "created_at",
            "updated_at",
            "branch_name",
            "system_prompt",
            "auto_stash",
            "keep_branch",
            "context",
            "validation_command",
            "started_at",
            "finished_at",
        ]
        read_only_fields = ["created_at", "updated_at", "output", "workdir", "system_prompt", "started_at", "finished_at"]

    def create(self, validated_data):
        # workdirが指定されている場合は、TodoListを自動作成/取得
        workdir = self.context.get("workdir")
        todo_list = None

        if workdir:
            todo_list, _ = TodoList.objects.get_or_create(workdir=workdir)

        if not todo_list:
            todo_list = validated_data.get("todo_list")

        validated_data["todo_list"] = todo_list
        return super().create(validated_data)

    def validate(self, data):
        # workdirがneither in data nor in instance
        workdir = self.context.get("workdir")
        if not workdir and not self.instance:
            # インスタンスがない場合はtodo_listが必須
            if not data.get("todo_list"):
                raise serializers.ValidationError({"todo_list": "workdirまたはtodo_listのいずれかは必須です"})
        return data


class ExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Extension
        fields = ["id", "name", "type", "cmd", "args", "envs", "timeout", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
