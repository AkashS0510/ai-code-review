from celery import current_task
from celery_app import celery_app
from db.database import SessionLocal, ReviewTask, TaskStatus
from workers.github_analyzer import GitHubPRAnalyzer
from config import Config
from datetime import datetime
import traceback
from typing import Dict, List


@celery_app.task(bind=True)
def analyze_pr_task(self, repo_url: str, pr_number: int, github_token: str = None):
    """Celery task to analyze a GitHub PR with AI code review"""
    task_id = self.request.id
    db_session = SessionLocal()
    task_record = None

    try:
        # Update task status to processing
        task_record = db_session.query(ReviewTask).filter_by(id=task_id).first()
        if task_record:
            task_record.status = TaskStatus.PROCESSING.value
            task_record.started_at = datetime.utcnow()
            db_session.commit()

        # Update task progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 1, "total": 4, "status": "Initializing GitHub analyzer"},
        )

        # Initialize analyzer
        analyzer = GitHubPRAnalyzer(
            repo_url=repo_url, pr_number=pr_number, github_token=github_token
        )

        self.update_state(
            state="PROGRESS",
            meta={"current": 2, "total": 4, "status": "Fetching PR data"},
        )

        # Get PR details for metadata
        pr_details = analyzer.get_pr_details()
        files = analyzer.get_pr_files()

        self.update_state(
            state="PROGRESS",
            meta={"current": 3, "total": 4, "status": "Running AI code review"},
        )

        # Get comprehensive review data with AI analysis
        review_data = analyzer.prepare_for_ai_review()

        self.update_state(
            state="PROGRESS",
            meta={"current": 4, "total": 4, "status": "Saving results"},
        )

        # Update database record with enhanced metadata
        if task_record:
            task_record.status = TaskStatus.COMPLETED.value
            task_record.completed_at = datetime.utcnow()
            task_record.results = review_data
            task_record.pr_title = pr_details.get("title") if pr_details else None
            task_record.author = (
                pr_details.get("user", {}).get("login") if pr_details else None
            )
            task_record.files_count = len(files)
            task_record.additions = sum(f.get("additions", 0) for f in files)
            task_record.deletions = sum(f.get("deletions", 0) for f in files)
            db_session.commit()

        self.update_state(
            state="SUCCESS",
            meta={"current": 4, "total": 4, "status": "Completed with AI review"},
        )

        return review_data

    except Exception as e:
        error_msg = str(e)

        try:
            # Update task status to failed in database
            if task_record:
                task_record.status = TaskStatus.FAILED.value
                task_record.error_message = error_msg
                task_record.completed_at = datetime.utcnow()
                db_session.commit()
        except Exception as db_error:
            print(f"Failed to update database with error: {db_error}")

        # Don't include traceback in Celery state to avoid serialization issues
        self.update_state(
            state="FAILURE", meta={"error": error_msg, "task_id": task_id}
        )

        # Re-raise the exception for Celery
        raise Exception(error_msg)

    finally:
        if db_session:
            db_session.close()
