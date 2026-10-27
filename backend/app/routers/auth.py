from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.errors import error_response
from app.models.user import User
from app.rate_limit import limiter, login_attempts_allowed, record_failed_login
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import create_token, decode_token, verify_password
from app.services.users import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Auth"])

REFRESH_COOKIE = "refresh_token"
# The refresh cookie is only ever sent to the auth endpoints
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _issue_tokens(response: Response, user: User) -> TokenResponse:
    """Set a fresh refresh cookie and return a new access token."""
    settings = get_settings()
    refresh_token, refresh_lifetime = create_token(user.id, "refresh", user.token_version)
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=refresh_lifetime,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        path=REFRESH_COOKIE_PATH,
    )
    access_token, access_lifetime = create_token(user.id, "access", user.token_version)
    return TokenResponse(
        access_token=access_token,
        expires_in=access_lifetime,
        user=UserResponse.model_validate(user),
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        httponly=True,
    )


def _user_from_refresh_token(db: Session, token: str | None) -> User | None:
    payload = decode_token(token, "refresh") if token else None
    if payload is None:
        return None
    try:
        user = db.get(User, UUID(payload["sub"]))
    except ValueError:
        return None
    if user is None or user.token_version != payload["ver"]:
        return None
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(lambda: get_settings().rate_limit_auth)
def register(request: Request, data: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    """Create an account (with the default categories) and sign in."""
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists")
    user = create_user(db, data.email, data.password)
    db.commit()
    db.refresh(user)
    return _issue_tokens(response, user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(lambda: get_settings().rate_limit_auth)
def login(request: Request, data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Sign in with email and password."""
    # Per-account brute-force guard; works even when client IPs can't be trusted
    email_key = data.email.strip().lower()
    if not login_attempts_allowed(email_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts for this account. Please try again later.",
        )

    user = get_user_by_email(db, data.email)
    # Always verify (against a dummy hash when the user doesn't exist) so timing is equal
    password_ok = verify_password(user.password_hash if user else None, data.password)
    if user is None or not password_ok:
        record_failed_login(email_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return _issue_tokens(response, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Exchange the refresh cookie for a new access token (and rotate the cookie)."""
    user = _user_from_refresh_token(db, refresh_token)
    if user is None:
        # Returned (not raised) so the cookie-clearing header is kept
        expired = error_response(401, "Session expired, please log in again")
        _clear_refresh_cookie(expired)
        return expired
    return _issue_tokens(response, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    """Sign out everywhere: revokes all tokens for the user and clears the cookie."""
    user = _user_from_refresh_token(db, refresh_token)
    if user is not None:
        user.token_version += 1
        db.commit()
    _clear_refresh_cookie(response)
    return None


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Get the signed-in user."""
    return current_user
