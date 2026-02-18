from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Todo, TodoList, Agent
from .serializers import TodoSerializer, TodoListSerializer, AgentSerializer


class TodoListViewSet(viewsets.ModelViewSet):
    """
    TodoListのCRUD API
    """
    queryset = TodoList.objects.all()
    serializer_class = TodoListSerializer


class AgentViewSet(viewsets.ModelViewSet):
    """
    AgentのCRUD API
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer


class TodoViewSet(viewsets.ModelViewSet):
    """
    TodoのCRUD API
    
    - GET /api/todos/ - 全件取得（workdirでフィルタ可能）
    - POST /api/todos/ - 新規作成
    - GET /api/todos/{id}/ - 詳細取得
    - PUT /api/todos/{id}/ - 更新
    - DELETE /api/todos/{id}/ - 削除
    - POST /api/todos/{id}/start/ - タスク開始
    - POST /api/todos/{id}/cancel/ - タスクキャンセル
    """
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    
    def get_queryset(self):
        queryset = Todo.objects.all()
        workdir = self.request.query_params.get('workdir')
        task_status = self.request.query_params.get('status')
        
        if workdir:
            queryset = queryset.filter(todo_list__workdir=workdir)
        if task_status:
            queryset = queryset.filter(status=task_status)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        # workdirが指定されていれば、コンテキストに渡す
        workdir = request.data.get('workdir')
        if workdir:
            # workdirからtodo_listを取得または作成
            todo_list, _ = TodoList.objects.get_or_create(workdir=workdir)
            request.data['todo_list'] = todo_list.id
        
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """タスクを開始 statusを 'queued' に変更"""
        todo = self.get_object()
        todo.status = Todo.Status.QUEUED
        todo.save()
        serializer = self.get_serializer(todo)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """タスクをキャンセル statusを 'cancelled' に変更"""
        todo = self.get_object()
        todo.status = Todo.Status.CANCELLED
        todo.save()
        serializer = self.get_serializer(todo)
        return Response(serializer.data)
