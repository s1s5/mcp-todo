from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import get_object_or_404
import subprocess
import logging
from .models import Todo, TodoList, Agent, Extension
from .serializers import TodoSerializer, TodoListSerializer, AgentSerializer, ExtensionSerializer


logger = logging.getLogger(__name__)


def get_git_worktrees(workdir):
    """
    指定されたworkdirで git worktree list を実行し、結果を取得する
    
    Args:
        workdir: gitリポジトリのルートディレクトリ
        
    Returns:
        list: [{"path": "...", "branch": "..."}, ...] のリスト
              エラー発生時は空リストを返す
    """
    try:
        result = subprocess.run(
            ['git', 'worktree', 'list', '--porcelain'],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"git worktree list failed in {workdir}: {result.stderr}")
            return []
        
        worktrees = []
        # porcelain format: 各worktreeは "worktree <path>" で始まり、"branch <branch>" が続く
        current_entry = {}
        for line in result.stdout.splitlines():
            if line.startswith('worktree '):
                if current_entry:
                    # 前のエントリを追加
                    worktrees.append(current_entry)
                current_entry = {'path': line[9:].strip()}  # "worktree " を除去
            elif line.startswith('branch '):
                current_entry['branch'] = line[7:].strip()  # "branch " を除去
            elif line == '':
                # 空行はエントリの区切り
                if current_entry:
                    worktrees.append(current_entry)
                    current_entry = {}
        
        # 最後のエントリを追加
        if current_entry:
            worktrees.append(current_entry)
        
        return worktrees
        
    except subprocess.TimeoutExpired:
        logger.error(f"git worktree list timeout in {workdir}")
        return []
    except Exception as e:
        logger.error(f"git worktree list error in {workdir}: {e}")
        return []


class TodoPagination(LimitOffsetPagination):
    """Todo用ページネーション: 1ページ50件"""
    default_limit = 50
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100


class TodoListViewSet(viewsets.ModelViewSet):
    """
    TodoListのCRUD API
    
    - GET /api/todolists/ - 全件取得
    - POST /api/todolists/ - 新規作成
    - GET /api/todolists/{id}/ - 詳細取得
    - PUT /api/todolists/{id}/ - 更新
    - DELETE /api/todolists/{id}/ - 削除
    - GET /api/todolists/{id}/worktrees/ - git worktree一覧取得
    """
    queryset = TodoList.objects.all()
    serializer_class = TodoListSerializer
    
    @action(detail=True, methods=['get'])
    def worktrees(self, request, pk=None):
        """指定されたTodoListのworkdirでgit worktree listを実行し、結果を取得"""
        todolist = self.get_object()
        worktrees = get_git_worktrees(todolist.workdir)
        return Response({'worktrees': worktrees})


class AgentViewSet(viewsets.ModelViewSet):
    """
    AgentのCRUD API
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer


class ExtensionViewSet(viewsets.ModelViewSet):
    """
    ExtensionのCRUD API
    """
    queryset = Extension.objects.all()
    serializer_class = ExtensionSerializer


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
        """タスクをキャンセル 
        - queued → waiting に戻す
        - running → cancelled に変更（task_workerが処理中）
        - その他 → cancelled
        """
        todo = self.get_object()
        
        if todo.status == Todo.Status.QUEUED:
            # queued の場合は waiting に戻す
            todo.status = Todo.Status.WAITING
        else:
            # running / その他は cancelled
            todo.status = Todo.Status.CANCELLED
        
        todo.save()
        serializer = self.get_serializer(todo)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def worktrees(self, request, pk=None):
        """指定されたTodoが所属するTodoListのworkdirでgit worktree listを実行し、結果を取得"""
        todo = self.get_object()
        worktrees = get_git_worktrees(todo.todo_list.workdir)
        return Response({'worktrees': worktrees})
