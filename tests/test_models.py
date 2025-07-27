import pytest
from datetime import datetime
from pydantic import ValidationError
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.models import (
    TaskStatusEnum,
    PRAnalysisRequest,
    TaskCreateResponse,
    ProgressInfo,
    TaskStatusResponse,
    Issue,
    FileResult,
    Summary,
    Results,
    TaskResultsResponse,
    TaskListItem,
    TaskListResponse
)


class TestTaskStatusEnum:
    def test_task_status_enum_values(self):
        """Test TaskStatusEnum values"""
        assert TaskStatusEnum.PENDING == "pending"
        assert TaskStatusEnum.PROCESSING == "processing"
        assert TaskStatusEnum.COMPLETED == "completed"
        assert TaskStatusEnum.FAILED == "failed"


class TestPRAnalysisRequest:
    def test_valid_pr_analysis_request(self):
        """Test valid PRAnalysisRequest creation"""
        request = PRAnalysisRequest(
            repo_url="https://github.com/test/repo",
            pr_number=123,
            github_token="test-token"
        )
        assert request.repo_url == "https://github.com/test/repo"
        assert request.pr_number == 123
        assert request.github_token == "test-token"

    def test_pr_analysis_request_without_token(self):
        """Test PRAnalysisRequest without github_token"""
        request = PRAnalysisRequest(
            repo_url="https://github.com/test/repo",
            pr_number=123
        )
        assert request.repo_url == "https://github.com/test/repo"
        assert request.pr_number == 123
        assert request.github_token is None

    def test_pr_analysis_request_validation_error(self):
        """Test PRAnalysisRequest validation errors"""
        with pytest.raises(ValidationError):
            PRAnalysisRequest(repo_url="https://github.com/test/repo")  # Missing pr_number

        with pytest.raises(ValidationError):
            PRAnalysisRequest(pr_number=123)  # Missing repo_url


class TestTaskCreateResponse:
    def test_task_create_response(self):
        """Test TaskCreateResponse creation"""
        response = TaskCreateResponse(
            task_id="test-task-id",
            status=TaskStatusEnum.PENDING,
            message="Task created successfully"
        )
        assert response.task_id == "test-task-id"
        assert response.status == TaskStatusEnum.PENDING
        assert response.message == "Task created successfully"


class TestProgressInfo:
    def test_progress_info(self):
        """Test ProgressInfo model"""
        progress = ProgressInfo(
            current=5,
            total=10,
            status="Processing files"
        )
        assert progress.current == 5
        assert progress.total == 10
        assert progress.status == "Processing files"


class TestTaskStatusResponse:
    def test_task_status_response_complete(self):
        """Test TaskStatusResponse with all fields"""
        now = datetime.now()
        response = TaskStatusResponse(
            task_id="test-task-id",
            status=TaskStatusEnum.COMPLETED,
            created_at=now,
            started_at=now,
            completed_at=now,
            repo_url="https://github.com/test/repo",
            pr_number=123,
            pr_title="Test PR",
            author="test-author",
            files_count=5,
            additions=100,
            deletions=50,
            progress=ProgressInfo(current=10, total=10, status="Complete"),
            error_message=None
        )
        assert response.task_id == "test-task-id"
        assert response.status == TaskStatusEnum.COMPLETED
        assert response.pr_title == "Test PR"
        assert response.files_count == 5

    def test_task_status_response_minimal(self):
        """Test TaskStatusResponse with minimal required fields"""
        response = TaskStatusResponse(
            task_id="test-task-id",
            status=TaskStatusEnum.PENDING,
            created_at=None,
            started_at=None,
            completed_at=None,
            repo_url="https://github.com/test/repo",
            pr_number=123
        )
        assert response.task_id == "test-task-id"
        assert response.pr_title is None
        assert response.progress is None


class TestAIReviewModels:
    def test_issue_model(self):
        """Test Issue model"""
        issue = Issue(
            type="bug",
            line=42,
            description="Potential null pointer exception",
            suggestion="Add null check before accessing object"
        )
        assert issue.type == "bug"
        assert issue.line == 42
        assert issue.description == "Potential null pointer exception"
        assert issue.suggestion == "Add null check before accessing object"

    def test_issue_without_line(self):
        """Test Issue model without line number"""
        issue = Issue(
            type="style",
            description="Missing docstring",
            suggestion="Add function docstring"
        )
        assert issue.type == "style"
        assert issue.line is None

    def test_file_result(self):
        """Test FileResult model"""
        issues = [
            Issue(type="bug", description="Test bug", suggestion="Fix it"),
            Issue(type="style", description="Test style", suggestion="Format it")
        ]
        file_result = FileResult(name="test.py", issues=issues)
        assert file_result.name == "test.py"
        assert len(file_result.issues) == 2
        assert file_result.issues[0].type == "bug"

    def test_file_result_no_issues(self):
        """Test FileResult with no issues"""
        file_result = FileResult(name="test.py")
        assert file_result.name == "test.py"
        assert len(file_result.issues) == 0

    def test_summary_model(self):
        """Test Summary model"""
        summary = Summary(
            total_files=5,
            total_issues=10,
            critical_issues=2
        )
        assert summary.total_files == 5
        assert summary.total_issues == 10
        assert summary.critical_issues == 2

    def test_results_model(self):
        """Test Results model"""
        files = [
            FileResult(name="file1.py", issues=[]),
            FileResult(name="file2.py", issues=[
                Issue(type="bug", description="Test", suggestion="Fix")
            ])
        ]
        summary = Summary(total_files=2, total_issues=1, critical_issues=1)
        results = Results(files=files, summary=summary)
        
        assert len(results.files) == 2
        assert results.summary.total_files == 2
        assert results.summary.total_issues == 1


class TestTaskResultsResponse:
    def test_task_results_response_with_results(self):
        """Test TaskResultsResponse with results"""
        now = datetime.now()
        summary = Summary(total_files=1, total_issues=1, critical_issues=0)
        results = Results(
            files=[FileResult(name="test.py", issues=[])],
            summary=summary
        )
        response = TaskResultsResponse(
            task_id="test-task-id",
            status=TaskStatusEnum.COMPLETED,
            completed_at=now,
            results=results
        )
        assert response.task_id == "test-task-id"
        assert response.results is not None
        assert response.results.summary.total_files == 1

    def test_task_results_response_no_results(self):
        """Test TaskResultsResponse without results"""
        now = datetime.now()
        response = TaskResultsResponse(
            task_id="test-task-id",
            status=TaskStatusEnum.FAILED,
            completed_at=now,
            results=None
        )
        assert response.task_id == "test-task-id"
        assert response.results is None


class TestTaskListModels:
    def test_task_list_item(self):
        """Test TaskListItem model"""
        now = datetime.now()
        item = TaskListItem(
            task_id="test-task-id",
            status=TaskStatusEnum.COMPLETED,
            repo_url="https://github.com/test/repo",
            pr_number=123,
            created_at=now,
            pr_title="Test PR",
            author="test-author"
        )
        assert item.task_id == "test-task-id"
        assert item.pr_title == "Test PR"
        assert item.author == "test-author"

    def test_task_list_response(self):
        """Test TaskListResponse model"""
        now = datetime.now()
        tasks = [
            TaskListItem(
                task_id="task-1",
                status=TaskStatusEnum.COMPLETED,
                repo_url="https://github.com/test/repo",
                pr_number=123,
                created_at=now
            )
        ]
        response = TaskListResponse(
            tasks=tasks,
            total=1,
            page=1,
            per_page=10,
            pages=1
        )
        assert len(response.tasks) == 1
        assert response.total == 1
        assert response.page == 1
        assert response.pages == 1