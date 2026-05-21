import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/auth", tags=["auth"])

_SECRET = "stock-analysis-jwt-secret-2024-internal"
_ALGORITHM = "HS256"
_EXPIRE_HOURS = 24 * 30  # 30 days

_USERNAME = os.getenv("APP_USERNAME")
_PASSWORD = os.getenv("APP_PASSWORD")


class LoginRequest(BaseModel):
    username: str
    password: str


def create_token(username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": exp}, _SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> bool:
    try:
        jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return True
    except JWTError:
        return False


@router.post("/login")
async def login(body: LoginRequest) -> dict:
    if body.username != _USERNAME or body.password != _PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(body.username), "username": body.username}
