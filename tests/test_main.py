import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from fastapi.testclient import TestClient
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from models.models import TaskStatusEnum
from db.database import TaskStatus


class TestMainAPI:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Setup test client for each test method"""
        self.client = TestClient(app)

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "AI Code Review System is running", "status": "healthy"}

    def test_start_analysis_missing_fields(self):
        """Test start analysis with missing required fields"""
        response = self.client.post("/api/v1/analyze", json={})
        assert response.status_code == 422  # Unprocessable Entity

    @patch('main.analyze_pr_task')
    @patch('main.get_db')
    def test_start_analysis_success(self, mock_get_db, mock_task):
        """Test successful analysis start"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])  # Make it iterable
        mock_task.apply_async.return_value = MagicMock(id="test-task-id")

        request_data = {
            "repo_url": "https://github.com/test/repo",
            "pr_number": 123,
            "github_token": "test-token"
        }

        response = self.client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "PR analysis started"




    @patch('main.get_db')
    def test_get_task_results_not_found(self, mock_get_db):
        """Test get task results for non-existent task"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_db.return_value = iter([mock_db])

        response = self.client.get("/api/v1/results/nonexistent-task-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"


    @patch('main.get_db')
    def test_list_tasks_with_filters(self, mock_get_db):
        """Test list tasks with status filter"""
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        
        mock_query = mock_db.query.return_value
        mock_query.filter_by.return_value.order_by.return_value.count.return_value = 1
        mock_query.filter_by.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        response = self.client.get("/api/v1/tasks?status=completed&page=2&per_page=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 5



    @patch('main.get_db')
    def test_delete_task_not_found(self, mock_get_db):
        """Test deletion of non-existent task"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_db.return_value = iter([mock_db])

        response = self.client.delete("/api/v1/tasks/nonexistent-task-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"

