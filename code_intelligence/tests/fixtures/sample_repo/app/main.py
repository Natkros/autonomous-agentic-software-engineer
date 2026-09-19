from fastapi import FastAPI

from app.services.auth_service import AuthService

app = FastAPI()
auth_service = AuthService()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/login")
def login(email: str, password: str):
    return auth_service.authenticate_user(email, password)
