"""Tests for mcp_server module"""

import os
import tempfile

import pytest

from todo.mcp_server import validate_branch_name, validate_path


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
