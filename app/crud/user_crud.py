from crud.base import CRUDBase
from model.user import User
from schemas.user_schema import UserCreate, UserUpdate
from sqlalchemy.orm import Session
from sqlalchemy import or_
from utils.auth.jwt_handler import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
)
from fastapi import Response, HTTPException, status
from utils.config import settings
from datetime import datetime, timedelta
from typing import Dict, TypedDict
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class ResetTokenData(TypedDict):
    email: str
    expiry: datetime


# Ephemeral in-memory reset token store. Consider replacing with DB-backed store or JWT.
password_reset_tokens: Dict[str, ResetTokenData] = {}


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def create(self, db: Session, obj_in: UserCreate) -> User:
        existing_user = (
            db.query(User)
            .filter(or_(User.email == obj_in.email, User.phone == obj_in.phone))
            .first()
        )
        if existing_user:
            raise ValueError("A user with this email or phone number already exists.")
        new_user = User(
            email=obj_in.email,
            phone=obj_in.phone,
            name=obj_in.name,
            role=obj_in.role,
            password=hash_password(obj_in.password),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def login(self, response: Response, db: Session, email: str, password: str) -> dict:
        user = db.query(User).filter(User.email == email).first()
        if user and verify_password(password, user.password):
            token_data = {
                "user_id": user.user_id,
                "email": user.email,
                "role": user.role,
            }
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                samesite="lax",
                secure=False,  # set to True in production behind HTTPS
            )
            return {
                "access_token": access_token,
                "token_type": "bearer",
            }
        # Return None so the router can handle 401 consistently
        return None

    def forgot_password(self, db: Session, email: str) -> dict:
        """
        Initiate password reset by generating a short-lived reset token
        and sending a reset link to the user's email.
        Does not disclose whether the email exists.
        """
        user = db.query(User).filter(User.email == email).first()

        if user:
            # Generate secure token
            reset_token = secrets.token_urlsafe(32)

            # Store token in memory with expiry (15 minutes)
            expiry = datetime.utcnow() + timedelta(minutes=15)
            password_reset_tokens[reset_token] = {
                "email": email,
                "expiry": expiry,
            }

            # Send email (best-effort; don't reveal errors to client)
            try:
                self._send_reset_email(
                    to_email=user.email,
                    user_name=user.name if hasattr(user, "name") else user.email,
                    reset_token=reset_token,
                )
            except Exception as e:
                # Log and continue without leaking details
                print(f"Error sending reset email to {email}: {e}")

        # Always return generic success to avoid email enumeration
        return {
            "message": "If the email exists, a password reset link has been sent."
        }

    def reset_password(self, db: Session, token: str, new_password: str) -> dict:
        """
        Complete password reset using a previously issued token.
        """
        token_data = password_reset_tokens.get(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        if token_data["expiry"] < datetime.utcnow():
            # Remove expired token
            del password_reset_tokens[token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        # Optional: basic password policy
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters long.",
            )

        # Get user by email
        user = db.query(User).filter(User.email == token_data["email"]).first()
        if not user:
            # Remove token even if user not found
            del password_reset_tokens[token]
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Update password (hashed)
        user.password = hash_password(new_password)
        db.commit()

        # Remove used token
        del password_reset_tokens[token]

        return {
            "message": "Password reset successfully. You can now login with your new password.",
            "email": user.email,
        }

    def change_password(
        self, db: Session, user_id: int, current_password: str, new_password: str
    ) -> dict:
        """
        Change password for an authenticated user.
        """
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not verify_password(current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        if verify_password(new_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password must be at least 8 characters long.",
            )

        user.password = hash_password(new_password)
        db.commit()

        return {
            "message": "Password changed successfully",
            "email": user.email,
        }

    def _send_reset_email(self, to_email: str, user_name: str, reset_token: str) -> None:
        """
        Send password reset email with a link containing the reset token.
        """
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = f"Movie Booking- Password Reset Request"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hi {user_name},</p>
                    <p>We received a request to reset your password.</p>
                    <p>Click the button below to reset your password:</p>
                    <a href="{reset_link}" class="button">Reset Password</a>
                    <p>Or copy this link:</p>
                    <p style="word-break: break-all; color: #007bff;">{reset_link}</p>
                    <p><strong>This link expires in 15 minutes.</strong></p>
                    <p>If you didn't request this, ignore this email.</p>
                    <p>Best regards,<br>Orion Cinemas Team</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.utcnow().year} Orion Cinemas</p>
                </div>
            </div>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM
        message["To"] = to_email

        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, message.as_string())


user_crud = CRUDUser(User, id_field="user_id")