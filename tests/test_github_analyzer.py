import pytest
from unittest.mock import patch, MagicMock
import requests
import sys
import os
from dotenv import load_dotenv
load_dotenv()
# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from workers.github_analyzer import GitHubPRAnalyzer


class TestGitHubPRAnalyzer:
    def test_parse_github_url_valid(self):
        """Test parsing valid GitHub URLs"""
        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        assert analyzer.owner == "owner"
        assert analyzer.repo == "repo"
        assert analyzer.pr_number == 123

    def test_parse_github_url_with_trailing_slash(self):
        """Test parsing GitHub URL with trailing slash"""
        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo/", 123)
        assert analyzer.owner == "owner"
        assert analyzer.repo == "repo"

    def test_parse_github_url_invalid(self):
        """Test parsing invalid GitHub URLs"""
        with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
            GitHubPRAnalyzer("https://github.com/owner", 123)

    def test_init_with_token(self):
        """Test initialization with GitHub token"""
        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123, "test-token")
        assert "Authorization" in analyzer.headers
        assert analyzer.headers["Authorization"] == "token test-token"

    def test_init_without_token(self):
        """Test initialization without GitHub token"""
        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        assert "Authorization" not in analyzer.headers
        assert analyzer.headers["Accept"] == "application/vnd.github.v3+json"
        assert analyzer.headers["User-Agent"] == "AI-Code-Review-System"

    @patch('src.workers.github_analyzer.requests.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer._make_request("https://api.github.com/test")

        assert result == {"key": "value"}
        mock_get.assert_called_once_with("https://api.github.com/test", headers=analyzer.headers)

    @patch('src.workers.github_analyzer.requests.get')
    def test_make_request_failure(self, mock_get):
        """Test failed API request"""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        
        with pytest.raises(Exception, match="GitHub API error"):
            analyzer._make_request("https://api.github.com/test")

    @patch.object(GitHubPRAnalyzer, '_make_request')
    def test_get_pr_details(self, mock_make_request):
        """Test getting PR details"""
        mock_make_request.return_value = {
            "title": "Test PR",
            "body": "Test description",
            "user": {"login": "test-user"}
        }

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer.get_pr_details()

        assert result["title"] == "Test PR"
        assert result["body"] == "Test description"
        mock_make_request.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/123"
        )

    @patch.object(GitHubPRAnalyzer, '_make_request')
    def test_get_pr_files(self, mock_make_request):
        """Test getting PR files"""
        mock_make_request.return_value = [
            {
                "filename": "test.py",
                "patch": "@@ -1,3 +1,3 @@\n-old line\n+new line"
            },
            {
                "filename": "test2.js",
                "patch": "@@ -5,2 +5,2 @@\n-console.log('old')\n+console.log('new')"
            }
        ]

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer.get_pr_files()

        assert len(result) == 2
        assert result[0]["filename"] == "test.py"
        assert result[1]["filename"] == "test2.js"
        mock_make_request.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/123/files"
        )

    @patch.object(GitHubPRAnalyzer, '_make_request')
    def test_get_pr_files_empty(self, mock_make_request):
        """Test getting PR files when API returns None"""
        mock_make_request.return_value = None

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer.get_pr_files()

        assert result == []

    @patch('src.workers.github_analyzer.ai_code_review')
    @patch.object(GitHubPRAnalyzer, 'get_pr_files')
    @patch.object(GitHubPRAnalyzer, 'get_pr_details')
    def test_prepare_for_ai_review_success(self, mock_get_pr_details, mock_get_pr_files, mock_ai_code_review):
        """Test successful preparation for AI review"""
        mock_get_pr_details.return_value = {
            "title": "Test PR",
            "body": "Test description"
        }
        mock_get_pr_files.return_value = [
            {
                "filename": "test.py",
                "patch": "@@ -1,3 +1,3 @@\n-old line\n+new line"
            }
        ]
        mock_ai_code_review.return_value = {
            "files": [{"name": "test.py", "issues": []}],
            "summary": {"total_files": 1, "total_issues": 0, "critical_issues": 0}
        }

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer.prepare_for_ai_review()

        assert result["pr_info"]["title"] == "Test PR"
        assert result["pr_info"]["description"] == "Test description"
        assert len(result["code_changes"]) == 1
        assert result["code_changes"][0]["filename"] == "test.py"
        assert result["code_changes"][0]["language"] == "py"
        assert result["ai_review"] is not None

    @patch('workers.github_analyzer.ai_code_review')
    @patch.object(GitHubPRAnalyzer, 'get_pr_files')
    @patch.object(GitHubPRAnalyzer, 'get_pr_details')
    def test_prepare_for_ai_review_ai_failure(self, mock_get_pr_details, mock_get_pr_files, mock_ai_code_review):
        """Test preparation for AI review when AI review fails"""
        mock_get_pr_details.return_value = {
            "title": "Test PR",
            "body": "Test description"
        }
        mock_get_pr_files.return_value = [
            {
                "filename": "test.py",
                "patch": "@@ -1,3 +1,3 @@\n-old line\n+new line"
            }
        ]
        mock_ai_code_review.side_effect = Exception("AI review failed")

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        
        with patch('builtins.print'):  # Mock print to avoid output during tests
            result = analyzer.prepare_for_ai_review()

        assert result["pr_info"]["title"] == "Test PR"
        assert len(result["code_changes"]) == 1
        assert result["ai_review"] is None

    @patch.object(GitHubPRAnalyzer, 'get_pr_files')
    @patch.object(GitHubPRAnalyzer, 'get_pr_details')
    def test_prepare_for_ai_review_file_without_extension(self, mock_get_pr_details, mock_get_pr_files):
        """Test preparation for AI review with file without extension"""
        mock_get_pr_details.return_value = {
            "title": "Test PR",
            "body": "Test description"
        }
        mock_get_pr_files.return_value = [
            {
                "filename": "Dockerfile",
                "patch": "@@ -1,3 +1,3 @@\n-FROM old\n+FROM new"
            }
        ]

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer.prepare_for_ai_review()

        assert result["code_changes"][0]["filename"] == "Dockerfile"
        assert result["code_changes"][0]["language"] == "unknown"

    @patch.object(GitHubPRAnalyzer, 'get_pr_files')
    @patch.object(GitHubPRAnalyzer, 'get_pr_details')
    def test_prepare_for_ai_review_file_no_patch(self, mock_get_pr_details, mock_get_pr_files):
        """Test preparation for AI review with file that has no patch"""
        mock_get_pr_details.return_value = {
            "title": "Test PR",
            "body": "Test description"
        }
        mock_get_pr_files.return_value = [
            {
                "filename": "test.py"
                # No patch field
            }
        ]

        analyzer = GitHubPRAnalyzer("https://github.com/owner/repo", 123)
        result = analyzer.prepare_for_ai_review()

        assert result["code_changes"][0]["filename"] == "test.py"
        assert result["code_changes"][0]["diff"] == ""