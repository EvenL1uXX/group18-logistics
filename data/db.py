from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .models import Base


class Database:
    """Owns the engine and hands out request-scoped sessions."""

    def __init__(self, url: str):
        self.engine = create_engine(url, future=True)
        self.session_factory = sessionmaker(bind=self.engine, future=True, expire_on_commit=False)
        self.scoped = scoped_session(self.session_factory)

    def init_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self):
        return self.scoped()

    def remove(self) -> None:
        self.scoped.remove()
