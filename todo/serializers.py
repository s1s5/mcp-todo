from rest_framework import serializers
from .models import Todo, TodoList, Agent


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'name', 'system_message', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TodoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TodoList
        fields = ['id', 'workdir', 'created_at']
        read_only_fields = ['created_at']


class TodoSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True, allow_null=True)
    workdir = serializers.CharField(source='todo_list.workdir', read_only=True)
    
    class Meta:
        model = Todo
        fields = [
            'id',
            'todo_list',
            'workdir',  # todo_list経由で参照（読み取り専用）
            'agent',
            'agent_name',
            'ref_files',
            'edit_files',
            'prompt',
            'context',
            'status',
            'output',
            'validation_command',
            'timeout',
            'created_at',
            'updated_at',
            'branch_name',
        ]
        read_only_fields = ['created_at', 'updated_at', 'status', 'output', 'workdir']
    
    def create(self, validated_data):
        # workdirが指定されている場合は、TodoListを自動作成/取得
        workdir = self.context.get('workdir')
        todo_list = None
        
        if workdir:
            todo_list, _ = TodoList.objects.get_or_create(workdir=workdir)
        
        if not todo_list:
            todo_list = validated_data.get('todo_list')
        
        validated_data['todo_list'] = todo_list
        return super().create(validated_data)
    
    def validate(self, data):
        # workdirがneither in data nor in instance
        workdir = self.context.get('workdir')
        if not workdir and not self.instance:
            # インスタンスがない場合はtodo_listが必須
            if not data.get('todo_list'):
                raise serializers.ValidationError({
                    'todo_list': 'workdirまたはtodo_listのいずれかは必須です'
                })
        return super().validate(data)
