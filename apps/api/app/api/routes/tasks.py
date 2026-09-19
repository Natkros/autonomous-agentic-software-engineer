from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.repository import Repository
from app.models.task import Task, TaskRunStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead
from app.services.task_service import TaskExecutionError, execute_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    """Submit a natural-language task and run the full agent pipeline
    (Requirement Analyst -> Repository Explorer -> Planner -> Coder ->
    Execution) against the repository. At the default `autonomy_level`
    (1), this proposes a plan and candidate patches only. Raising
    `autonomy_level` lets the execution node actually apply, test, and (at
    4+) commit approved patches inside the throwaway clone this creates —
    see `app/services/task_service.py` for exactly what each level allows.
    """
    repository = db.get(Repository, payload.repository_id)
    if repository is None or repository.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    try:
        final_state = execute_task(repository.url, payload.user_request, payload.autonomy_level)
        task = Task(
            repository_id=repository.id,
            user_request=payload.user_request,
            autonomy_level=payload.autonomy_level,
            status=TaskRunStatus.FAILED if final_state.get("errors") else TaskRunStatus.COMPLETED,
            requirement_analysis=final_state.get("requirement_analysis") or None,
            repository_summary=final_state.get("repository_summary") or None,
            plan=final_state.get("plan") or None,
            patch_proposals=final_state.get("patch_proposals") or None,
            review_results=final_state.get("review_results") or None,
            correction_results=final_state.get("correction_results") or None,
            security_scan_result=final_state.get("security_scan_result") or None,
            approval_requests=final_state.get("approval_requests") or None,
            git_commit=final_state.get("git_commit") or None,
            execution_status=final_state.get("execution_status"),
            errors=final_state.get("errors") or None,
        )
    except TaskExecutionError as exc:
        task = Task(
            repository_id=repository.id,
            user_request=payload.user_request,
            autonomy_level=payload.autonomy_level,
            status=TaskRunStatus.FAILED,
            errors=[str(exc)],
        )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    repository = db.get(Repository, task.repository_id)
    if repository is None or repository.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task
