from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.repository import Repository
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryRead

router = APIRouter(prefix="/repositories", tags=["repositories"])


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
    repository = db.get(Repository, repository_id)
    if repository is None or repository.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repository
