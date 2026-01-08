# Authentication & Role Documentation

Project: Movie Ticket Booking System (FastAPI)  
Version: v1.0  
Last Updated: 15-Nov-2025  

## Overview

This document explains how authentication and role-based access control (RBAC) are implemented in the Movie Ticket Booking backend built with FastAPI.  
It covers the login/registration flow, token management, access enforcement, and permissions for the two roles:

- admin
- user (customer)

The permissions matrix from previous documentation is retained and expanded to reflect domain entities (movies, shows, seats, bookings, pricing, payments, notifications, backups, feedback, etc.).

## Authentication Flow

| Step | Description |
|------|-------------|
| 1. Register | User registers using name/email/phone/password (role defaults to user). |
| 2. Login | Credentials are verified; system issues Access (1h) and Refresh (7d) tokens. |
| 3. Access Token | Short-lived JWT (1 hour) used for authenticated API requests. |
| 4. Refresh Token | Long-lived JWT (7 days) used to obtain new Access tokens via /users/refresh. |
| 5. Token Revocation | Logout invalidates the refresh token (revoked in DB by jti). |
| 6. Protected Routes | Dependencies/middleware validate token and role/ownership before allowing access. |

## JWT Token Example (Access)

```json
{
  "sub": "user_42",
  "user_id": 42,
  "role": "user",
  "type": "access",
  "jti": "6f2c7e0d-9b2a-44f9-8dc3-5ad0a1b4e901",
  "sid": "session_5b913c",
  "ver": 1,
  "scopes": ["booking:create", "seatlock:create"],
  "iat": 1731660000,
  "exp": 1731663600
}
```

Notes:
- `ver` (permission version) enables invalidating all tokens after privilege change.
- `scopes` are optional; pure role-based enforcement works without them.
- Refresh token payload should include `type=refresh` and longer `exp`.

## Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | /users/signup | Register new user (role=user) | No |
| POST | /users/login | Authenticate and receive Access + Refresh tokens | No |
| POST | /users/refresh | Exchange a valid Refresh token for new Access token | Refresh token |
| POST | /users/logout | Revoke current refresh token (recommended addition) | Yes |
| POST | /users/logout-all | Revoke all active refresh sessions (optional) | Yes |
| POST | /users/forgot-password | Request password reset (OTP/email) | No |
| POST | /users/reset-password | Reset password using token/OTP | No |

(If your current implementation uses `/refresh` instead of `/users/refresh`, align it consistently; recommended: keep all auth under `/users/`.)

## Roles

| Role | Description | Typical Capabilities |
|------|-------------|---------------------|
| admin | Full platform control | All CRUD + operational tasks |
| user | Customer booking tickets | Own bookings, seat locks, payments, feedback, notifications |

## Permissions Matrix (Retained & Adapted)

| Resource | Action | admin | user |
|----------|--------|-------|------|
| User | Create | ✅ | Signup only |
| User | Read | ✅ | ✅ (self) |
| User | Update | ✅ | ✅ (self) |
| User | Delete | ✅ | ❌ |
| Movie | Create | ✅ | ❌ |
| Movie | Read | ✅ | ✅ |
| Movie | Update | ✅ | ❌ |
| Movie | Delete | ✅ | ❌ |
| Screen | Create | ✅ | ❌ |
| Screen | Read | ✅ | ✅ |
| Screen | Update | ✅ | ❌ |
| Screen | Delete | ✅ | ❌ |
| Seat | Create (bulk) | ✅ | ❌ |
| Seat | Read | ✅ | ✅ (via availability) |
| Seat | Update | ✅ | ❌ |
| Seat | Delete | ✅ | ❌ |
| Seat Category | Manage | ✅ | ❌ |
| Show | Create | ✅ | ❌ |
| Show | Read | ✅ | ✅ |
| Show | Cancel/Update | ✅ | ❌ |
| Show Category Pricing | CRUD | ✅ | Read (derived) |
| Seat Lock | Create | ✅ | ✅ (own locks) |
| Seat Lock | Read | ✅ | ✅ (own) |
| Seat Lock | Delete | ✅ | ✅ (own) |
| Booking | Create | ✅ | ✅ |
| Booking | Read | ✅ | ✅ (own) |
| Booking | Update (modify seats/status) | ✅ | Limited (cancel if policy allows) |
| Booking | Cancel | ✅ | ✅ (policy) |
| Booking | Delete | ✅ | ❌ |
| Payment | View | ✅ | ✅ (own) |
| Payment | Refund | ✅ | Request-only |
| Discount | CRUD | ✅ | Apply only |
| GST | CRUD | ✅ | ❌ |
| Food Category | CRUD | ✅ | ❌ |
| Food Item | CRUD | ✅ | Read |
| Notification | Send/Global | ✅ | Read own / mark read |
| Backup | Create/List/Delete | ✅ | ❌ |
| Restore | Create/List | ✅ | ❌ |
| Feedback | Reply | ✅ | Create (own booking) |
| Reports / Analytics | Generate | ✅ | ❌ |

Ownership Enforcement: user can only access records tied to their `user_id`.

## Scope Model (Optional Layer)

Scopes can augment or future-proof RBAC (e.g., granting a temporary capability without full admin role):

Example scopes:
- booking:create
- booking:cancel
- seatlock:create
- seatlock:cleanup
- pricing:read
- feedback:reply
- backup:run
- notification:send

If scopes are absent, default to role-based checks.

## Token Validation Pipeline

1. Extract Authorization header: `Bearer <access_token>`.
2. Decode & verify signature (HS256 or RS256).
3. Validate `exp`, `type == "access"`.
4. Load user by `sub` / `user_id`.
5. Check:
   - user active
   - not locked/banned
   - permission version (`ver`)
6. Authorize role or scopes for endpoint.
7. Inject user context into route.

Refresh token validation:
- Type == refresh
- Not expired
- Not revoked (lookup by `jti`)
- Matches stored session (hashed token comparison)
- Optionally rotate on success (issue new refresh, revoke old)

## Example Dependency: Current User

```python
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from models import User
from db import get_db
from settings import JWT_SECRET, JWT_ALG

def get_current_user(db: Session = Depends(get_db), token: str = Depends(get_bearer_token)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Malformed token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or not found")

    # Optional permission version check
    if user.permission_version != payload.get("ver", 1):
        raise HTTPException(status_code=401, detail="Token permission version mismatch")

    return {
        "id": user.id,
        "role": user.role,
        "scopes": payload.get("scopes", [])
    }
```

## Role-Based Wrapper

```python
def roles_allowed(*allowed_roles: str):
    def wrapper(current = Depends(get_current_user)):
        if current["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current
    return wrapper
```

## Scope-Based Wrapper

```python
def require_scope(required_scopes: list[str]):
    def wrapper(current = Depends(get_current_user)):
        user_scopes = set(current.get("scopes", []))
        if not any(scope in user_scopes for scope in required_scopes):
            raise HTTPException(status_code=403, detail="Insufficient scope.")
        return current
    return wrapper
```

## Usage Example

```python
@router.get(
    "/profile",
    description="Retrieve current user's profile.",
    dependencies=[Depends(roles_allowed("admin", "user"))]
)
def profile(db: Session = Depends(get_db), current = Depends(get_current_user)):
    return get_user_by_id(current["id"], db)
```

Admin-only example:

```python
@router.post(
    "/movies",
    dependencies=[Depends(roles_allowed("admin"))],
    description="Create a new movie (admin only)."
)
def create_movie(payload: MovieCreate, db: Session = Depends(get_db)):
    return create_movie_record(payload, db)
```

## Token Expiry Policy (Updated for Project)

| Token Type    | Lifetime  | Storage            | Rotation                    |
|---------------|-----------|--------------------|-----------------------------|
| Access Token  | 1 hour    | In-memory / Header | Renew via refresh endpoint  |
| Refresh Token | 7 days    | DB (hashed) / Cookie optional | Rotate on use (recommended) |

Why 1 hour Access (instead of 5 min):
- Balances UX with security for booking flows (seat selection + payment).
- Shorter lifetimes (e.g., 5–15 min) can be adopted if high-risk operations increase.

## Example Sequence (Login → Access → Refresh → Logout)

1. User logs in → receives Access + Refresh tokens
2. Uses Access token for protected endpoints (seatlocks, bookings)
3. On expiry (401 or proactive timer) → POST /users/refresh with refresh token
4. Receives new Access token
5. User logs out → POST /users/logout → refresh token revoked (cannot be reused)

## Seat Lock + Booking Security Tie-In

- Seat locks must be tied to user `sub` / `user_id`.
- Booking endpoint verifies:
  - Seat lock ownership
  - Lock TTL validity
  - Unbooked status at transaction start
- Access token must not be expired during booking commit.

## Revocation Strategy

Maintain a `refresh_sessions` table (or collection):
| Field | Description |
|-------|-------------|
| jti | Unique token ID |
| user_id | Owning user |
| hashed_refresh | Hashed refresh token value |
| expires_at | Expiration timestamp |
| revoked | Boolean flag |
| created_at | Issued time |
| last_used_at | Last refresh usage |
| user_agent_hash | Optional device fingerprint |
| ip_hash | Optional IP fingerprint |
| permission_version | Version at issuance |

On `/users/logout`:
- Mark the session `revoked = true`.


## Error Responses (Suggested Consistency)

| HTTP Code | Scenario | Example Payload |
|-----------|----------|-----------------|
| 400 | Validation/Domain error | {"detail": "Seat already locked"} |
| 401 | Invalid/expired token | {"detail": "Invalid token"} |
| 403 | Role/scope violation | {"detail": "Insufficient role"} |
| 404 | Resource not found | {"detail": "Booking not found"} |
| 409 | Race/conflict | {"detail": "Seat already booked"} |

## Security Enhancements (Optional)

- Refresh rotation: issue a new refresh token each time `/users/refresh` succeeds.
- Add `nonce` claim for extra replay defense if embedding Access token in WebSocket auth.
- Implement rate limiting on `/users/login`, `/seatlocks/`, `/bookings/`.

