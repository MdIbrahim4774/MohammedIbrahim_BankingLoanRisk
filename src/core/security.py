from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from src.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# Predefined System Users for Banking Analysts and System Administrators
SYSTEM_USERS: Dict[str, Dict[str, str]] = {
    "admin": {
        "username": "admin",
        "password": "admin123", # For demonstration / local evaluation
        "role": "administrator",
        "full_name": "Senior Risk Director"
    },
    "analyst": {
        "username": "analyst",
        "password": "analyst123",
        "role": "analyst",
        "full_name": "Credit Risk Analyst"
    }
}

def verify_password(plain_password: str, stored_password: str) -> bool:
    return plain_password == stored_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    username = payload.get("sub")
    if username is None or username not in SYSTEM_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return SYSTEM_USERS[username]

def require_role(required_role: str):
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "")
        # Administrator has access to all roles
        if user_role == "administrator":
            return current_user
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Requires role: {required_role}"
            )
        return current_user
    return role_checker

