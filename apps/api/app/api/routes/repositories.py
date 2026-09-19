from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.repository import Repository
from app.models.repository_analysis import AnalysisStatus, RepositoryAnalysis
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryRead
from app.schemas.repository_analysis import RepositoryAnalysisRead
from app.services.analysis_service import RepositoryAnalysisError, analyze_repository

router = APIRouter(prefix="/repositories", tags=["repositories"])


def _get_owned_repository(repository_id: str, db: Session, current_user: User) -> Repository:
    repository = db.get(Repository, repository_id)
    if repository is None or repository.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repository


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
def create_repository(
    payload: RepositoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Repository:
    repository = Repository(
        name=payload.name,
        url=payload.url,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repository


@router.get("", response_model=list[RepositoryRead])
def list_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Repository]:
    return db.query(Repository).filter(Repository.owner_id == current_user.id).all()


@router.get("/{repository_id}", response_model=RepositoryRead)
def get_repository(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Repository:
    return _get_owned_repository(repository_id, db, current_user)


@router.post("/{repository_id}/analyze", response_model=RepositoryAnalysisRead, status_code=status.HTTP_201_CREATED)
def analyze_repository_endpoint(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RepositoryAnalysis:
    """Clone and scan the repository's source (Phase 2 code intelligence:
    file tree, dependencies, frameworks, AST-based symbol extraction).

    Runs synchronously on the request thread — there is no background job
    queue yet (Celery/Redis workers are Phase 4), so this call blocks until
    the clone and scan complete. A failed clone (bad URL, no network, auth
    required) is recorded as a FAILED analysis, not a 500 error, since it's
    an expected outcome, not a server bug.
    """
    repository = _get_owned_repository(repository_id, db, current_user)

    try:
        summary = analyze_repository(repository.url)
        analysis = RepositoryAnalysis(
            repository_id=repository.id, status=AnalysisStatus.COMPLETED, summary=summary,
        )
    except RepositoryAnalysisError as exc:
        analysis = RepositoryAnalysis(
            repository_id=repository.id, status=AnalysisStatus.FAILED, error_message=str(exc),
        )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/{repository_id}/analysis", response_model=RepositoryAnalysisRead)
def get_latest_analysis(
    repository_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RepositoryAnalysis:
    repository = _get_owned_repository(repository_id, db, current_user)

    analysis = (
        db.query(RepositoryAnalysis)
        .filter(RepositoryAnalysis.repository_id == repository.id)
        .order_by(desc(RepositoryAnalysis.created_at))
        .first()
    )
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis has been run for this repository yet")
    return analysis
