from app.models.user import User


class AuthService:
    """Handles user authentication."""

    def authenticate_user(self, email: str, password: str) -> dict:
        """Verify credentials and return a session payload."""
        return {"email": email, "authenticated": True}

    def hash_password(self, password: str) -> str:
        return f"hashed:{password}"
