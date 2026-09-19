from app.database import Base


class User(Base):
    """A registered user."""

    __tablename__ = "users"
