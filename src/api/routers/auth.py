from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from src.core.security import (
    SYSTEM_USERS, verify_password, create_access_token, get_current_user
)
from src.models.schemas import TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username.lower().strip()
    user = SYSTEM_USERS.get(username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(data={"sub": username, "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "username": username
    }

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"],
        "role": current_user["role"],
        "full_name": current_user["full_name"]
    }

