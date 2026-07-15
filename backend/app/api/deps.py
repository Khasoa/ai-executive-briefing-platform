from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    """Re-export database session dependency for route modules."""
    yield from _get_db()


DbSession = Depends(get_db)
