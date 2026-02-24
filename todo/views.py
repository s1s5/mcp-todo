from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from .models import Todo, TodoList, Agent
from .serializers import TodoSerializer, TodoListSerializer, AgentSerializer


class TodoPagination(PageNumberPagination):
    """Todo用ページネーション: 1ページ50件"""
    page_size = 50
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 100


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
    
    Query Parameters:
    - workdir: 特定のworkdirでフィルタ
    - status: 特定のステータスでフィルタ
    - order_by: 並び替えフィールド (created_at, -created_at, updated_at, -updated_at, status, -status, id, -id)
    """
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    pagination_class = TodoPagination
    
    def get_queryset(self):
        queryset = Todo.objects.all()
        workdir = self.request.query_params.get('workdir')
        task_status = self.request.query_params.get('status')
        order_by = self.request.query_params.get('order_by')
        
        if workdir:
            queryset = queryset.filter(todo_list__workdir=workdir)
        if task_status:
            queryset = queryset.filter(status=task_status)
        
        # order_by パラメータで並び替え
        if order_by:
            # 安全でない文字を除去（敏感な文字列はエラー）
            forbidden = [';', '--', '/*', '*/', 'xp_', 'sp_', 'exec', 'union']
            if any(f in order_by.lower() for f in forbidden):
                raise ValueError("Invalid order_by parameter")
            
            # 許可するフィールドのみ
            allowed_fields = ['created_at', 'updated_at', 'status', 'id']
            # 先頭の '-' を除去してフィールド名を取得
            field = order_by.lstrip('-')
            
            if field in allowed_fields:
                queryset = queryset.order_by(order_by)
        
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
