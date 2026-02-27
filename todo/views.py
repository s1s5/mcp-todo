from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import get_object_or_404
import subprocess
import logging
import os
from django.conf import settings
from .models import Todo, TodoList, Agent, Extension
from .serializers import TodoSerializer, TodoListSerializer, AgentSerializer, ExtensionSerializer
from .utils import get_or_create_todolist_with_parent


logger = logging.getLogger(__name__)


def check_git_repository(workdir):
    """
    指定されたパスがgit repositoryかどうかをチェックする
    
    Args:
        workdir: チェック対象のパス
        
    Returns:
        bool: git repositoryの場合はTrue
        
    Raises:
        ValueError: git repositoryでない場合
    """
    logging.info(f"check_git_repository called with workdir: {workdir}")
    
    # workdir が None や空の場合のチェック
    if not workdir:
        logger.error(f"workdirがNoneまたは空です: {workdir}")
        raise ValueError("workdirが指定されていません")
    
    # パスが存在しない場合のチェック
    if not os.path.exists(workdir):
        logger.error(f"指定されたパスが存在しません: {workdir}")
        raise ValueError(f"指定されたパスが存在しません: {workdir}")
    
    try:
        result = subprocess.run(
            ['git', '-C', workdir, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True,
            timeout=30
        )

        # git コマンドのエラーログ出力
        if result.returncode != 0:
            logger.error(f"git rev-parse failed in {workdir}: {result.stderr}")
        if result.stderr:
            logger.warning(f"git rev-parse stderr in {workdir}: {result.stderr}")
        
        if result.returncode != 0 or result.stdout.strip() != 'true':
            raise ValueError(f"指定されたパスはgit repositoryではありません: {workdir}")
        
        return True
        
    except subprocess.TimeoutExpired:
        raise ValueError(f"git repositoryのチェックがタイムアウトしました: {workdir}")
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"指定されたパスはgit repositoryではありません: {workdir}")


def get_git_worktrees(workdir):
    """
    指定されたworkdirで git worktree list を実行し、結果を取得する
    
    Args:
        workdir: gitリポジトリのルートディレクトリ
        
    Returns:
        list: [{"path": "...", "branch": "..."}, ...] のリスト
              エラー発生時は空リストを返す
        
    Raises:
        ValueError: git repositoryでない場合
    """
    logging.info(f"get_git_worktrees called with workdir: {workdir}")
    
    # まずgit repositoryかどうかをチェック
    check_git_repository(workdir)
    
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
                branch = line[7:].strip()  # "branch " を除去
                # refs/heads/ プレフィックスを除去
                if branch.startswith('refs/heads/'):
                    branch = branch[11:]
                current_entry['branch'] = branch
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

def get_git_branches(workdir):
    """
    指定されたworkdirで git branch を実行し、ローカルブランチ名一覧を取得する
    
    Args:
        workdir: gitリポジトリのルートディレクトリ
        
    Returns:
        list: ローカルブランチ名のリスト（'* 'は除去）
              エラー発生時は空リストを返す
    """
    try:
        result = subprocess.run(
            ['git', 'branch'],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"git branch failed in {workdir}: {result.stderr}")
            return []
        
        branches = []
        for line in result.stdout.splitlines():
            branch = line.strip()
            # 先頭の '* ' または '+ ' を除去
            # '* ' = 現在のチェックアウトブランチ
            # '+ ' = 別のワークツリーでチェックアウトされているブランチ
            if branch.startswith('* '):
                branch = branch[2:]
            elif branch.startswith('+ '):
                branch = branch[2:]
            branches.append(branch)
        
        return branches
        
    except subprocess.TimeoutExpired:
        logger.error(f"git branch timeout in {workdir}")
        return []
    except Exception as e:
        logger.error(f"git branch error in {workdir}: {e}")
        return []

def get_current_branch(workdir):
    """
    指定されたworkdirで現在のチェックアウト中のブランチ名を取得する
    
    Args:
        workdir: gitリポジトリのルートディレクトリ
        
    Returns:
        str: 現在のブランチ名（エラー発生時は空文字列を返す）
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"git rev-parse --abbrev-ref HEAD failed in {workdir}: {result.stderr}")
            return ''
        
        return result.stdout.strip()
        
    except subprocess.TimeoutExpired:
        logger.error(f"git rev-parse timeout in {workdir}")
        return ''
    except Exception as e:
        logger.error(f"git rev-parse error in {workdir}: {e}")
        return ''

def is_branch_merged(workdir, branch):
    """
    指定されたブランチが現在のブランチにマージ済みかどうかをチェックする
    
    Args:
        workdir: gitリポジトリのルートディレクトリ
        branch: チェック対象のブランチ名
        
    Returns:
        bool: マージ済みの場合はTrue
    """
    try:
        result = subprocess.run(
            ['git', 'merge-base', '--is-ancestor', branch, 'HEAD'],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # 終了コード0 = branchがHEADの祖先 = マージ済み
        return result.returncode == 0
        
    except Exception as e:
        logger.error(f"git merge-base error in {workdir}: {e}")
        return False


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

    def get_queryset(self):
        queryset = super().get_queryset()
        # parentが設定されているTodolistも一覧に表示する（parent.nameを表示）
        # queryset = queryset.filter(parent__isnull=True)
        return queryset

    @action(detail=True, methods=['get'], url_path='worktrees')
    def worktrees(self, request, pk=None):
        """指定されたTodoListのworkdirでgit worktree listを実行し、結果を取得"""
        todolist = self.get_object()
        try:
            worktrees = get_git_worktrees(todolist.workdir)
            return Response({'workdir': todolist.workdir, 'worktrees': worktrees})
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """指定されたTodoListのworkdirでgit branch -aを実行し、ブランチ名一覧を取得"""
        todolist = self.get_object()
        workdir = todolist.workdir
        
        # 現在のブランチを取得
        current_branch = get_current_branch(workdir)
        
        # 関連するworktreeのブランチ一覧を取得
        worktrees = get_git_worktrees(workdir)
        worktree_branches = set()
        for wt in worktrees:
            if 'branch' in wt:
                worktree_branches.add(wt['branch'])
        
        # ブランチ一覧を取得
        branch_names = get_git_branches(workdir)
        
        # 各ブランチについて削除可能フラグを付与
        branches = []
        for branch in branch_names:
            # 現在のブランチの場合は削除不可
            # worktreeで使用されているブランチも削除不可
            # マージ済みのブランチのみ削除可能
            can_delete = branch != current_branch and branch not in worktree_branches and is_branch_merged(workdir, branch)
            branches.append({'name': branch, 'can_delete': can_delete})
        
        return Response({'branches': branches})

    @action(detail=True, methods=['post'], url_path='create_branch')
    def create_branch(self, request, pk=None):
        """
        新しいブランチを作成
        
        Request body: {"new_branch_name": "新しいブランチ名", "base_branch": "ベースのブランチ名"}
        - new_branch_name: 必須、英数字、ハイフン、アンダースコアのみ許可
        - base_branch: 必須、既存のブランチ名である必要がある
        """
        import re

        todolist = self.get_object()
        new_branch_name = request.data.get('new_branch_name', '').strip()
        base_branch = request.data.get('base_branch', '').strip()

        # バリデーション: new_branch_name 必须
        if not new_branch_name:
            return Response(
                {'error': 'new_branch_nameは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バリデーション: new_branch_name は英数字、ハイフン、アンダースコアのみ許可
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_branch_name):
            return Response(
                {'error': 'new_branch_nameは英数字、ハイフン、アンダースコアのみ使用できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バリデーション: base_branch 必须
        if not base_branch:
            return Response(
                {'error': 'base_branchは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        workdir = todolist.workdir

        # 既存のブランチ一覧を取得
        existing_branches = get_git_branches(workdir)

        # バリデーション: 新しいブランチ名が既に存在するか
        if new_branch_name in existing_branches:
            return Response(
                {'error': f'ブランチ "{new_branch_name}" は既に存在します'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バリデーション: ベースブランチが存在するか
        if base_branch not in existing_branches:
            return Response(
                {'error': f'ベースブランチ "{base_branch}" が存在しません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ブランチを作成
        try:
            result = subprocess.run(
                ['git', 'branch', new_branch_name, base_branch],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"git branch failed: {result.stderr}")
                return Response(
                    {'error': f'ブランチの作成に失敗しました: {result.stderr}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                'new_branch_name': new_branch_name,
                'base_branch': base_branch,
                'message': f'ブランチ "{new_branch_name}" を作成しました'
            })

        except Exception as e:
            logger.error(f"create branch error: {e}")
            return Response(
                {'error': f'ブランチの作成に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='worktrees/add')
    def add_worktree(self, request, pk=None):
        """
        新しいworktreeを追加
        
        Request body: {"name": "ディレクトリ名", "branch": "ブランチ名"}
        - name: 必須、/ が含まれないこと
        - branch: 必須
        """
        import re

        todolist = self.get_object()
        worktree_name = request.data.get('name', '').strip()
        branch = request.data.get('branch', '').strip()

        # バリデーション: name 必须
        if not worktree_name:
            return Response(
                {'error': 'nameは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バリデーション: name に / が含まれないこと
        if '/' in worktree_name:
            return Response(
                {'error': 'nameに / を含めることはできません'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バリデーション: name は英数字、ハイフン、アンダースコアのみ許可
        if not re.match(r'^[a-zA-Z0-9_-]+$', worktree_name):
            return Response(
                {'error': 'nameは英数字、ハイフン、アンダースコアのみ使用できます'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # バリデーション: branch 必须
        if not branch:
            return Response(
                {'error': 'branchは必須です'},
                status=status.HTTP_400_BAD_REQUEST
            )

        worktree_root = settings.WORKTREE_ROOT
        worktree_path = os.path.join(worktree_root, worktree_name)

        # バリデーション: 同名ディレクトリが存在しないこと
        if os.path.exists(worktree_path):
            return Response(
                {'error': f'同名ディレクトリが既に存在します: {worktree_path}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        branch_created = False

        # worktreeを作成
        try:
            # ブランチが存在するか確認
            existing_branches = get_git_branches(todolist.workdir)
            if branch not in existing_branches:
                # ブランチが存在しない場合は作成
                # ベースブランチを取得（現在のチェックアウト中のブランチ）
                base_result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=todolist.workdir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                base_branch = base_result.stdout.strip() if base_result.returncode == 0 else 'main'

                # ブランチを作成
                branch_result = subprocess.run(
                    ['git', 'branch', branch, base_branch],
                    cwd=todolist.workdir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if branch_result.returncode != 0:
                    return Response(
                        {'error': f'ブランチの作成に失敗しました: {branch_result.stderr}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                branch_created = True
            result = subprocess.run(
                ['git', 'worktree', 'add', worktree_path, branch],
                cwd=todolist.workdir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"git worktree add failed: {result.stderr}")
                return Response(
                    {'error': f'worktreeの作成に失敗しました: {result.stderr}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            response_data = {
                'name': worktree_name,
                'path': worktree_path,
                'branch': branch,
                'message': f'worktree "{worktree_name}" を作成しました'
            }
            if branch_created:
                response_data['branch_created'] = True

            return Response(response_data)

        except Exception as e:
            logger.error(f"add worktree error: {e}")
            return Response(
                {'error': f'worktreeの作成に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'], url_path=r'worktrees/(?P<name>[^/]+)/')
    def remove_worktree(self, request, pk=None, name=None):
        """
        worktreeを削除
        
        URL: /api/todolists/{id}/worktrees/{name}/
        """
        todolist = self.get_object()
        worktree_name = name

        worktree_root = settings.WORKTREE_ROOT
        worktree_path = os.path.join(worktree_root, worktree_name)

        # バリデーション: worktreeが存在すること
        if not os.path.exists(worktree_path):
            return Response(
                {'error': f'worktreeが存在しません: {worktree_path}'},
                status=status.HTTP_404_NOT_FOUND
            )

        # worktreeを削除
        try:
            result = subprocess.run(
                ['git', 'worktree', 'remove', worktree_path, '--force'],
                cwd=todolist.workdir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"git worktree remove failed: {result.stderr}")
                return Response(
                    {'error': f'worktreeの削除に失敗しました: {result.stderr}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"remove worktree error: {e}")
            return Response(
                {'error': f'worktreeの削除に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            # workdirからtodo_listを取得または作成（worktreeの場合はparentを設定）
            todo_list, _ = get_or_create_todolist_with_parent(workdir)
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
        
        # todo_listの存在チェック
        if not todo.todo_list:
            logger.info(f"todo {pk} has no todo_list")
            return Response(
                {'error': 'このTodoにはTodoListが紐づいていません'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workdir = todo.todo_list.workdir
        
        # workdirの存在チェック
        if not workdir:
            logger.info(f"todo_list {todo.todo_list.id} has no workdir")
            return Response(
                {'error': 'TodoListにworkdirが設定されていません'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"todo.todo_list.workdir = {workdir}")
        
        try:
            worktrees = get_git_worktrees(workdir)
            return Response({'workdir': workdir, 'worktrees': worktrees})
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """指定されたTodoが所属するTodoListのworkdirでgit branch -aを実行し、ブランチ名一覧を取得"""
        todo = self.get_object()
        branches = get_git_branches(todo.todo_list.workdir)
        return Response({'branches': branches})

    @action(detail=True, methods=['post'])
    def create_branch(self, request, pk=None):
        """
        新しいブランチを作成
        
        Request body: {"new_branch_name": "新しいブランチ名"}
        - worktreeが選択されている場合は、そのworktreeのブランチから作成
        - 選択されていない場合は、現在のブランチ（branch_name）から作成
        """
        import re
        
        todo = self.get_object()
        new_branch_name = request.data.get('new_branch_name', '').strip()
        
        # バリデーション: ブランチ名の形式チェック
        if not new_branch_name:
            return Response(
                {'error': 'ブランチ名を入力してください'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # ブランチ名は英数字、ハイフン、アンダースコアのみ許可
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_branch_name):
            return Response(
                {'error': 'ブランチ名は英数字、ハイフン、アンダースコアのみ使用できます'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workdir = todo.todo_list.workdir
        
        # ブランチ作成元の決定
        # worktreeが選択されている場合はそのブランチから、
        # そうでなければ現在のbranch_nameから作成
        base_branch = todo.branch_name
        if not base_branch:
            # branch_nameがない場合は現在のチェックアウト中のブランチを取得
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=workdir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    base_branch = result.stdout.strip()
                else:
                    return Response(
                        {'error': '現在のブランチを取得できませんでした'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                logger.error(f"git rev-parse error: {e}")
                return Response(
                    {'error': f'ブランチ作成元の取得に失敗しました: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # 新しいブランチを作成
        try:
            # まず、新しいブランチ名が既に使用されているか確認
            existing_branches = get_git_branches(workdir)
            if new_branch_name in existing_branches:
                return Response(
                    {'error': f'ブランチ "{new_branch_name}" は既に存在します'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ブランチを作成
            result = subprocess.run(
                ['git', 'branch', new_branch_name, base_branch],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"git branch failed: {result.stderr}")
                return Response(
                    {'error': f'ブランチの作成に失敗しました: {result.stderr}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # 正常に作成されたら、branch_nameを更新
            todo.branch_name = new_branch_name
            todo.save()
            
            return Response({
                'branch_name': new_branch_name,
                'message': f'ブランチ "{new_branch_name}" を作成しました'
            })
            
        except Exception as e:
            logger.error(f"create branch error: {e}")
            return Response(
                {'error': f'ブランチの作成に失敗しました: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
