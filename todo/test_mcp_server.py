"""Tests for mcp_server module"""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from todo.mcp_server import validate_branch_name, validate_path, sort_priority


class TestValidateBranchName:
    """validate_branch_name のユニットテスト"""

    def test_valid_alphanumeric(self):
        """正常系: 英数字のみOK"""
        assert validate_branch_name("main") == "main"
        assert validate_branch_name("feature123") == "feature123"
        assert validate_branch_name("123abc") == "123abc"

    def test_valid_with_hyphen(self):
        """正常系: ハイフン含むOK"""
        assert validate_branch_name("feature-branch") == "feature-branch"
        assert validate_branch_name("my-feature-123") == "my-feature-123"

    def test_valid_with_underscore(self):
        """正常系: アンダースコア含むOK"""
        assert validate_branch_name("feature_branch") == "feature_branch"
        assert validate_branch_name("my_feature_123") == "my_feature_123"

    def test_valid_combined(self):
        """正常系: 英数字、ハイフン、アンダースコアの組み合わせOK"""
        assert validate_branch_name("feature-branch_name") == "feature-branch_name"
        assert validate_branch_name("ai-task-123_abc") == "ai-task-123_abc"

    def test_empty_string_ok(self):
        """異常系: 空文字はOK（そのまま返回）"""
        assert validate_branch_name("") == ""

    def test_invalid_japanese(self):
        """異常系: 日本語はNG"""
        with pytest.raises(ValueError):
            validate_branch_name("機能")

        with pytest.raises(ValueError):
            validate_branch_name("feature-機能")

    def test_invalid_special_characters(self):
        """異常系: 特殊文字NG"""
        with pytest.raises(ValueError):
            validate_branch_name("feature/task")

        with pytest.raises(ValueError):
            validate_branch_name("feature/task")

        with pytest.raises(ValueError):
            validate_branch_name("feature.name")

        with pytest.raises(ValueError):
            validate_branch_name("feature@branch")

        with pytest.raises(ValueError):
            validate_branch_name("feature#123")

    def test_invalid_space(self):
        """異常系: スペースNG"""
        with pytest.raises(ValueError):
            validate_branch_name("feature branch")

    def test_invalid_dot(self):
        """異常系: ドットNG"""
        with pytest.raises(ValueError):
            validate_branch_name(".hidden")

    def test_invalid_slash(self):
        """異常系: スラッシュNG"""
        with pytest.raises(ValueError):
            validate_branch_name("feature/branch")


class TestValidatePath:
    """validate_path のユニットテスト"""

    @pytest.fixture
    def workdir(self, tmp_path):
        """テスト用の一時ディレクトリを作成"""
        return str(tmp_path)

    def test_valid_relative_path(self, workdir):
        """正常系: 相対パスOK"""
        # ファイル作成
        test_file = os.path.join(workdir, "test.txt")
        open(test_file, "w").close()

        # must_exists=False で検証
        result = validate_path(workdir, "test.txt", False)
        assert result == "test.txt"

    def test_valid_relative_path_subdir(self, workdir):
        """正常系: サブディレクトリ内の相対パスOK"""
        # サブディレクトリ作成
        subdir = os.path.join(workdir, "subdir")
        os.makedirs(subdir)
        test_file = os.path.join(subdir, "test.txt")
        open(test_file, "w").close()

        result = validate_path(workdir, "subdir/test.txt", False)
        assert result == os.path.join("subdir", "test.txt")

    def test_valid_must_exists_true(self, workdir):
        """正常系: ファイル存在確認(must_exists=True) OK"""
        # ファイル作成
        test_file = os.path.join(workdir, "existing.txt")
        open(test_file, "w").close()

        result = validate_path(workdir, "existing.txt", True)
        assert result == "existing.txt"

    def test_valid_path_normalization(self, workdir):
        """正常系: パス正規化（./ は無視される）"""
        test_file = os.path.join(workdir, "test.txt")
        open(test_file, "w").close()

        result = validate_path(workdir, "./test.txt", False)
        assert result == "test.txt"

    def test_error_absolute_path(self, workdir):
        """異常系: 絶対パスNG"""
        with pytest.raises(ValueError) as exc_info:
            validate_path(workdir, "/etc/passwd", False)
        assert "絶対パス" in str(exc_info.value)

    def test_error_parent_directory_single(self, workdir):
        """異常系: 親ディレクトリ参照(..) NG"""
        with pytest.raises(ValueError) as exc_info:
            validate_path(workdir, "../file.txt", False)
        assert "親ディレクトリ参照" in str(exc_info.value)

    def test_error_parent_directory_multiple(self, workdir):
        """異常系: 複数の親ディレクトリ参照(..) NG"""
        with pytest.raises(ValueError) as exc_info:
            validate_path(workdir, "subdir/../../file.txt", False)
        assert "親ディレクトリ参照" in str(exc_info.value)

    def test_error_outside_workdir(self, workdir):
        """異常系: workdir外のパスNG（symlinkを使用）"""
        # workdir外のディレクトリへのsymlinkを作成（ファイルとして）
        parent = os.path.dirname(workdir)
        outside_file = os.path.join(parent, "outside.txt")
        with open(outside_file, "w") as f:
            f.write("outside")

        symlink_path = os.path.join(workdir, "link_to_outside")
        os.symlink(outside_file, symlink_path)

        # symlink経由でworkdir外へのアクセスを試みる
        with pytest.raises(ValueError) as exc_info:
            validate_path(workdir, "link_to_outside", False)
        assert "workdir外" in str(exc_info.value)

    def test_error_must_exists_true_but_not_exist(self, workdir):
        """異常系: ファイル不存在NG(must_exists=True)"""
        with pytest.raises(ValueError) as exc_info:
            validate_path(workdir, "nonexistent.txt", True)
        assert "存在しません" in str(exc_info.value)

    def test_valid_directory_inside_workdir(self, workdir):
        """正常系: ディレクトリ内のパスOK"""
        # ディレクトリ作成（ファイルはなし）
        subdir = os.path.join(workdir, "mydir")
        os.makedirs(subdir)

        result = validate_path(workdir, "mydir", False)
        assert result == "mydir"


class TestSortPriority:
    """sort_priority のユニットテスト"""

    def _create_mock_todo(self, status: str):
        """MockのTodoオブジェクトを作成"""
        todo = MagicMock()
        todo.status = status
        return todo

    def test_running_priority_zero(self):
        """running → 優先度0"""
        todo = self._create_mock_todo("running")
        assert sort_priority(todo) == 0

    def test_queued_priority_one(self):
        """queued → 優先度1"""
        todo = self._create_mock_todo("queued")
        assert sort_priority(todo) == 1

    def test_waiting_priority_two(self):
        """waiting → 優先度2"""
        todo = self._create_mock_todo("waiting")
        assert sort_priority(todo) == 2

    def test_completed_priority_three(self):
        """completed → 優先度3（其他ステータス）"""
        todo = self._create_mock_todo("completed")
        assert sort_priority(todo) == 3

    def test_error_priority_three(self):
        """error → 優先度3（其他ステータス）"""
        todo = self._create_mock_todo("error")
        assert sort_priority(todo) == 3

    def test_cancelled_priority_three(self):
        """cancelled → 優先度3（其他ステータス）"""
        todo = self._create_mock_todo("cancelled")
        assert sort_priority(todo) == 3

    def test_timeout_priority_three(self):
        """timeout → 優先度3（其他ステータス）"""
        todo = self._create_mock_todo("timeout")
        assert sort_priority(todo) == 3

    def test_unknown_status_priority_three(self):
        """未知のステータス → 優先度3"""
        todo = self._create_mock_todo("unknown_status")
        assert sort_priority(todo) == 3

    def test_priority_ordering(self):
        """優先度の順序確認: running < queued < waiting < others"""
        running = self._create_mock_todo("running")
        queued = self._create_mock_todo("queued")
        waiting = self._create_mock_todo("waiting")
        completed = self._create_mock_todo("completed")

        priorities = [
            sort_priority(running),
            sort_priority(queued),
            sort_priority(waiting),
            sort_priority(completed),
        ]

        assert priorities == [0, 1, 2, 3]


class TestListExternalTask:
    """listExternalTask のユニットテスト

    テスト対象:
    - ステータス(workdir)によるフィルタリング
    - ページネーション(offset/limit)
    - 優先度ソート(sort_priority関数利用)
    """

    @pytest.fixture
    def todo_list(self, db):
        """テスト用のTodoListを作成"""
        from todo.models import TodoList
        todo_list = TodoList.objects.create(workdir="/test/workdir")
        return todo_list

    @pytest.fixture
    def todos(self, todo_list):
        """複数のステータスを持つTodoを作成"""
        from todo.models import Todo, Agent

        # Agentを作成
        agent = Agent.objects.create(name="test_agent")

        Todo.objects.create(
            todo_list=todo_list,
            title="Task 1",
            prompt="Running task",
            status="running",
            agent=agent,
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task 2",
            prompt="Queued task",
            status="queued",
            agent=agent,
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task 3",
            prompt="Waiting task 1",
            status="waiting",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task 4",
            prompt="Waiting task 2",
            status="waiting",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task 5",
            prompt="Completed task",
            status="completed",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task 6",
            prompt="Error task",
            status="error",
        )

    @pytest.mark.django_db
    def test_list_all_without_status_filter(self, todos):
        """正常系: ステータスフィルタなしですべて取得"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1, limit=10)
        )

        assert result["total_count"] == 6
        assert result["current_page"] == 1
        assert result["total_pages"] == 1

    @pytest.mark.django_db
    def test_filter_by_status_running(self, todos):
        """正常系: runningステータスでフィルタリング"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="running", page=1, limit=10)
        )

        assert result["total_count"] == 1
        assert result["todos"][0]["status"] == "running"

    @pytest.mark.django_db
    def test_filter_by_status_queued(self, todos):
        """正常系: queuedステータスでフィルタリング"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="queued", page=1, limit=10)
        )

        assert result["total_count"] == 1
        assert result["todos"][0]["status"] == "queued"

    @pytest.mark.django_db
    def test_filter_by_status_waiting(self, todos):
        """正常系: waitingステータスでフィルタリング"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="waiting", page=1, limit=10)
        )

        assert result["total_count"] == 2

    @pytest.mark.django_db
    def test_filter_by_status_completed(self, todos):
        """正常系: completedステータスでフィルタリング"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="completed", page=1, limit=10)
        )

        assert result["total_count"] == 1
        assert result["todos"][0]["status"] == "completed"

    @pytest.mark.django_db
    def test_pagination_first_page(self, todos):
        """正常系: ページネーション - 1ページ目"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1, limit=3)
        )

        assert result["total_count"] == 6
        assert result["total_pages"] == 2
        assert result["current_page"] == 1
        assert result["limit"] == 3
        assert len(result["todos"]) == 3

    @pytest.mark.django_db
    def test_pagination_second_page(self, todos):
        """正常系: ページネーション - 2ページ目"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=2, limit=3)
        )

        assert result["total_count"] == 6
        assert result["total_pages"] == 2
        assert result["current_page"] == 2
        assert result["limit"] == 3
        assert len(result["todos"]) == 3

    @pytest.mark.django_db
    def test_pagination_out_of_range(self, todos):
        """正常系: ページネーション - 範囲外ページ"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=10, limit=10)
        )

        assert result["total_count"] == 6
        assert result["current_page"] == 10
        assert len(result["todos"]) == 0

    @pytest.mark.django_db
    def test_pagination_default_limit(self, todos):
        """正常系: デフォルトlimit（10）"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1)
        )

        assert result["limit"] == 10

    @pytest.mark.django_db
    def test_pagination_limit_max_100(self, todos):
        """正常系: limitが100を超える場合は100に制限"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1, limit=200)
        )

        assert result["limit"] == 100

    @pytest.mark.django_db
    def test_pagination_page_min_1(self, todos):
        """正常系: pageが1未満の場合は1に補正"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=0, limit=10)
        )

        assert result["current_page"] == 1

    @pytest.mark.django_db
    def test_priority_sorting(self, todo_list):
        """正常系: 優先度ソート running > queued > waiting > others

        作成順不同で、返り値の順序が優先度順になることを確認
        """
        from todo.models import Todo

        # 逆順で作成（古い順）
        Todo.objects.create(
            todo_list=todo_list,
            title="Task completed",
            prompt="Completed task",
            status="completed",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task waiting",
            prompt="Waiting task",
            status="waiting",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task queued",
            prompt="Queued task",
            status="queued",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task running",
            prompt="Running task",
            status="running",
        )
        Todo.objects.create(
            todo_list=todo_list,
            title="Task error",
            prompt="Error task",
            status="error",
        )

        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1, limit=10)
        )

        # 優先度順: running(0) > queued(1) > waiting(2) > others(3)
        statuses = [todo["status"] for todo in result["todos"]]

        # running, queued, waiting, completed/error の順になる
        assert statuses[0] == "running"
        assert statuses[1] == "queued"
        assert statuses[2] == "waiting"
        # completedとerrorは同じ優先度(3)なので順序は保証されない

    @pytest.mark.django_db
    def test_priority_sorting_with_filter(self, todos):
        """正常系: ステータスフィルタ適用後の優先度ソート"""
        from todo.mcp_server import listExternalTask

        import asyncio
        # waitingステータスのみを取得
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="waiting", page=1, limit=10)
        )

        # waitingのみなのでソート順は問わない（すべてwaiting）
        assert all(todo["status"] == "waiting" for todo in result["todos"])

    @pytest.mark.django_db
    def test_empty_result(self, todo_list):
        """正常系: 該当するTodoがない場合"""
        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="nonexistent_status", page=1, limit=10)
        )

        assert result["total_count"] == 0
        assert result["todos"] == []
        assert result["total_pages"] == 1

    @pytest.mark.django_db
    def test_prompt_preview_truncation(self, todo_list):
        """正常系: prompt_previewが50文字で省略される"""
        from todo.models import Todo

        long_prompt = "a" * 100
        Todo.objects.create(
            todo_list=todo_list,
            title="Long Prompt Task",
            prompt=long_prompt,
            status="waiting",
        )

        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1, limit=10)
        )

        # prompt_previewは50文字+"..." = 53文字
        assert len(result["todos"][0]["prompt_preview"]) == 53
        assert result["todos"][0]["prompt_preview"].endswith("...")

    @pytest.mark.django_db
    def test_prompt_detail_truncation(self, todo_list):
        """正常系: promptが100文字で省略される"""
        from todo.models import Todo

        long_prompt = "a" * 150
        Todo.objects.create(
            todo_list=todo_list,
            title="Long Prompt Task",
            prompt=long_prompt,
            status="waiting",
        )

        from todo.mcp_server import listExternalTask

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            listExternalTask(status="", page=1, limit=10)
        )

        # promptは100文字+"..." = 103文字
        assert len(result["todos"][0]["prompt"]) == 103
        assert result["todos"][0]["prompt"].endswith("...")
