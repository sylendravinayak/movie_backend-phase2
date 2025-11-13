from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response
from schemas.user_schema import UserCreate, UserUpdate
from crud.user_crud import user_crud
from sqlalchemy.orm import Session
from utils.auth.jwt_handler import create_access_token, verify_refresh_token, verify_access_token
from utils.auth.jwt_bearer import getcurrent_user, JWTBearer
from database import get_db
from crud.token_crud import revoke_token, is_token_revoked
from schemas.user_schema import ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        new_user = user_crud.create(db=db, obj_in=user)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
def login(response: Response, email: str, password: str, db: Session = Depends(get_db)):
    user = user_crud.login(response=response, db=db, email=email, password=password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return user

@router.get("/")
def get_all_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    role: str = Query(default="user"),
    current_user: dict = Depends(getcurrent_user("admin"))
):
    users = user_crud.get_all(db=db, skip=skip, limit=limit, filters={"role": role})
    return users

@router.get("/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(JWTBearer())
):
    # Only owner or admin
    if payload.get("role") != "admin" and payload.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    user = user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}")
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(JWTBearer())
):
    if payload.get("role") != "admin" and payload.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    db_user = user_crud.get(db=db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = user_crud.update(db=db, db_obj=db_user, obj_in=user_update)
    return updated_user

@router.post("/refresh")
def generate_new_access_token(request: Request, db: Session = Depends(get_db)):
    # Refresh token could be in Authorization header or cookie
    header = request.headers.get("Authorization")
    token = None
    if header and header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1].strip()
    elif request.cookies.get("refresh_token"):
        token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    payload = None
    try:
        payload = verify_refresh_token(token)
    except HTTPException as exc:
        # Propagate expired refresh token
        raise exc

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    jti = payload.get("jti")
    if jti and is_token_revoked(db, jti):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user_id = payload.get("user_id")
    role = payload.get("role")
    email = payload.get("email")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    access_token = create_access_token({"user_id": user_id, "role": role, "email": email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    header = request.headers.get("Authorization")

    # Try revoke access token if provided
    if header and header.lower().startswith("bearer "):
        access_token = header.split(" ", 1)[1].strip()
        try:
            access_payload = verify_access_token(access_token)
        except HTTPException:
            access_payload = None
        if access_payload:
            revoke_token(db, access_payload.get("jti"), access_payload.get("type") or "access", access_payload.get("user_id"))

    # Try revoke refresh token from cookie or header (if client sent refresh in header)
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token and header and header.lower().startswith("bearer "):
        # If client uses a different header for refresh, adjust here. We skip reusing same header as access token.
        refresh_token = None

    if refresh_token:
        try:
            refresh_payload = verify_refresh_token(refresh_token)
        except HTTPException:
            refresh_payload = None
        if refresh_payload:
            revoke_token(db, refresh_payload.get("jti"), refresh_payload.get("type") or "refresh", refresh_payload.get("user_id"))

    # clear refresh cookie in browser
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}


@router.post("/forgot-password", status_code=200)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Request password reset link via email"""
    return user_crud.forgot_password(db, data.email)


@router.post("/reset-password", status_code=200)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using email token"""
    return user_crud.reset_password(
        db=db,
        token=data.token,
        new_password=data.newPassword
    )


@router.post("/change-password", status_code=200)
def change_password(
    data: ChangePasswordRequest,
    current_user = Depends(JWTBearer()),
    db: Session = Depends(get_db)
):
    """Change password (requires current password)"""
    return user_crud.change_password(
        db=db,
        user_id=current_user.id,
        current_password=data.currentPassword,
        new_password=data.newPassword
    )