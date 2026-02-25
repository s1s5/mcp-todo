"""Tests for mcp_server module"""

import pytest

from todo.mcp_server import validate_branch_name


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
