from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PRAnalysisRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    pr_number: int = Field(..., description="Pull request number")
    github_token: Optional[str] = Field(None, description="GitHub API token")


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    message: str


class ProgressInfo(BaseModel):
    current: int
    total: int
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    repo_url: str
    pr_number: int
    pr_title: Optional[str] = None
    author: Optional[str] = None
    files_count: Optional[int] = None
    additions: Optional[int] = None
    deletions: Optional[int] = None
    progress: Optional[ProgressInfo] = None
    error_message: Optional[str] = None


class PRInfo(BaseModel):
    title: str
    description: Optional[str]


class FileChange(BaseModel):
    filename: str
    language: str
    diff: str


# AI Code Review Models
class Issue(BaseModel):
    type: str = Field(
        ..., description="Type of issue (e.g., 'bug', 'performance', 'style')"
    )
    line: Optional[int] = Field(None, description="Line number where the issue occurs")
    description: str = Field(..., description="Description of the issue")
    suggestion: str = Field(..., description="Suggested fix or improvement")


class FileResult(BaseModel):
    name: str = Field(..., description="Name of the file")
    issues: List[Issue] = Field(
        default_factory=list, description="List of issues found in the file"
    )


class Summary(BaseModel):
    total_files: int = Field(..., description="Total number of files reviewed")
    total_issues: int = Field(..., description="Total number of issues found")
    critical_issues: int = Field(..., description="Number of critical issues")


class Results(BaseModel):
    files: List[FileResult] = Field(..., description="List of files with their issues")
    summary: Summary = Field(..., description="Summary of the review")


class TaskResultsResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    completed_at: datetime
    results: Optional[Results] = None


class TaskListItem(BaseModel):
    task_id: str
    status: TaskStatusEnum
    repo_url: str
    pr_number: int
    created_at: datetime
    pr_title: Optional[str] = None
    author: Optional[str] = None


class TaskListResponse(BaseModel):
    tasks: List[TaskListItem]
    total: int
    page: int
    per_page: int
    pages: int
