from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from celery_app import celery_app
from db.database import get_db, create_tables, ReviewTask, TaskStatus
from models.models import (
    PRAnalysisRequest,
    TaskCreateResponse,
    TaskStatusResponse,
    TaskResultsResponse,
    TaskListResponse,
    TaskStatusEnum,
)
from tasks import analyze_pr_task
from datetime import datetime
import uuid
from typing import Optional

# Create tables on startup
create_tables()

app = FastAPI(
    title="AI Code Review System",
    description="Asynchronous GitHub PR analysis and AI code review system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"message": "AI Code Review System is running", "status": "healthy"}


@app.post("/api/v1/analyze", response_model=TaskCreateResponse, tags=["Analysis"])
async def start_analysis(request: PRAnalysisRequest, db: Session = Depends(get_db)):
    """
    Start PR analysis task

    - **repo_url**: GitHub repository URL (e.g., https://github.com/user/repo)
    - **pr_number**: Pull request number
    - **github_token**: Optional GitHub API token for private repos
    """
    try:
        # Generate task ID
        task_id = str(uuid.uuid4())

        # Create database record
        task_record = ReviewTask(
            id=task_id,
            repo_url=request.repo_url,
            pr_number=request.pr_number,
            status=TaskStatus.PENDING.value,
        )
        db.add(task_record)
        db.commit()

        # Start Celery task
        analyze_pr_task.apply_async(
            args=[request.repo_url, request.pr_number, request.github_token],
            task_id=task_id,
        )

        return TaskCreateResponse(
            task_id=task_id,
            status=TaskStatusEnum.PENDING,
            message="PR analysis started",
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to start analysis: {str(e)}"
        )


@app.get("/api/v1/status/{task_id}", response_model=TaskStatusResponse, tags=["Status"])
async def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """
    Get task status and progress information

    Returns detailed status including progress for running tasks
    """
    # Get from database
    task_record = db.query(ReviewTask).filter_by(id=task_id).first()

    if not task_record:
        raise HTTPException(status_code=404, detail="Task not found")

    response_data = {
        "task_id": task_id,
        "status": TaskStatusEnum(task_record.status),
        "created_at": task_record.created_at,
        "started_at": task_record.started_at,
        "completed_at": task_record.completed_at,
        "repo_url": task_record.repo_url,
        "pr_number": task_record.pr_number,
        "pr_title": task_record.pr_title,
        "author": task_record.author,
        "files_count": task_record.files_count,
        "additions": task_record.additions,
        "deletions": task_record.deletions,
        "error_message": task_record.error_message,
    }

    # Safely get Celery task info with error handling
    try:
        celery_task = celery_app.AsyncResult(task_id)

        # Only try to access state if the task exists in Redis
        if celery_task.state and celery_task.state == "PROGRESS":
            try:
                progress_info = celery_task.info
                if isinstance(progress_info, dict):
                    response_data["progress"] = {
                        "current": progress_info.get("current", 0),
                        "total": progress_info.get("total", 1),
                        "status": progress_info.get("status", "Processing"),
                    }
            except Exception:
                # If we can't get progress info, just continue without it
                pass
    except Exception as e:
        # If there's any issue with Celery task retrieval, log it but don't fail
        print(f"Warning: Could not retrieve Celery task info for {task_id}: {e}")
        # The response will just rely on database info

    return TaskStatusResponse(**response_data)


@app.get(
    "/api/v1/results/{task_id}", response_model=TaskResultsResponse, tags=["Results"]
)
async def get_task_results(task_id: str, db: Session = Depends(get_db)):
    """
    Get completed task results - returns only AI code review results

    Returns only the AI review analysis for completed tasks
    """
    task_record = db.query(ReviewTask).filter_by(id=task_id).first()

    if not task_record:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_record.status != TaskStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current status: {task_record.status}",
        )

    # Extract only the AI review results from the stored data
    results_data = task_record.results
    ai_review_data = results_data.get("ai_review") if results_data else None

    return TaskResultsResponse(
        task_id=task_id,
        status=TaskStatusEnum(task_record.status),
        completed_at=task_record.completed_at,
        results=ai_review_data if ai_review_data else None,
    )


@app.get("/api/v1/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[TaskStatusEnum] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """
    List all tasks with pagination and optional status filtering

    - **page**: Page number (starting from 1)
    - **per_page**: Number of items per page (max 100)
    - **status**: Optional status filter (pending, processing, completed, failed)
    """
    query = db.query(ReviewTask)

    if status:
        query = query.filter_by(status=status.value)

    query = query.order_by(ReviewTask.created_at.desc())

    # Calculate pagination
    total = query.count()
    offset = (page - 1) * per_page
    tasks = query.offset(offset).limit(per_page).all()

    task_list = [
        {
            "task_id": task.id,
            "status": TaskStatusEnum(task.status),
            "repo_url": task.repo_url,
            "pr_number": task.pr_number,
            "created_at": task.created_at,
            "pr_title": task.pr_title,
            "author": task.author,
        }
        for task in tasks
    ]

    return TaskListResponse(
        tasks=task_list,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@app.delete("/api/v1/tasks/{task_id}", tags=["Tasks"])
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """
    Delete a task and its results

    Note: This will not stop a running task, only remove it from the database
    """
    task_record = db.query(ReviewTask).filter_by(id=task_id).first()

    if not task_record:
        raise HTTPException(status_code=404, detail="Task not found")

    # Revoke the Celery task if it's still pending
    if task_record.status == TaskStatus.PENDING.value:
        celery_app.control.revoke(task_id, terminate=True)

    db.delete(task_record)
    db.commit()

    return {"message": f"Task {task_id} deleted successfully"}


@app.get("/api/v1/stats", tags=["Statistics"])
async def get_system_stats(db: Session = Depends(get_db)):
    """
    Get system statistics

    Returns overall statistics about task processing
    """
    total_tasks = db.query(ReviewTask).count()
    pending_tasks = (
        db.query(ReviewTask).filter_by(status=TaskStatus.PENDING.value).count()
    )
    processing_tasks = (
        db.query(ReviewTask).filter_by(status=TaskStatus.PROCESSING.value).count()
    )
    completed_tasks = (
        db.query(ReviewTask).filter_by(status=TaskStatus.COMPLETED.value).count()
    )
    failed_tasks = (
        db.query(ReviewTask).filter_by(status=TaskStatus.FAILED.value).count()
    )

    return {
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "processing_tasks": processing_tasks,
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "success_rate": round(
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2
        ),
    }
