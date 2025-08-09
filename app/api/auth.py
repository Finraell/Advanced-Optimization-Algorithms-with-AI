"""Authentication and authorization utilities.

This module provides a minimal integration with OAuth/OIDC providers using
``authlib`` and JWT-based sessions.  It defines routes to initiate
authentication flows with third-party providers (e.g. Google, GitHub),
handle callbacks, issue JWTs upon successful login, and helper
dependencies to retrieve the current user and enforce role-based
permissions.  Real deployments should configure client IDs, secrets
and redirect URIs via environment variables and harden token
generation, storage and revocation as needed.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Callable, List, Optional

import jwt  # type: ignore
from authlib.integrations.starlette_client import OAuth  # type: ignore
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models

# Read OAuth client configuration from environment variables.  In
# production, these values should be stored in a secret manager.  The
# REDIRECT_URI must be registered with your OAuth providers.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    oauth.register(
        name="github",
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        access_token_url="https://github.com/login/oauth/access_token",
        access_token_params=None,
        authorize_url="https://github.com/login/oauth/authorize",
        authorize_params=None,
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

router = APIRouter()


def create_access_token(*, user_id: int, role: str) -> str:
    """Generate a signed JWT for a given user.

    Args:
        user_id: The primary key of the authenticated user.
        role: The user's role (admin, editor, viewer).

    Returns:
        Encoded JWT as a string.
    """
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode = {"sub": str(user_id), "role": role, "exp": expire}
    token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


@router.get("/auth/{provider}")
async def auth_start(provider: str, request: Request):
    """Initiate an OAuth login flow for the specified provider.

    This endpoint redirects the user to the provider's authorization
    page.  Supported providers are ``google`` and ``github``.  If
    providers are not configured, a 404 is returned.
    """
    if provider not in oauth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown auth provider")
    redirect_uri = REDIRECT_URI + f"/{provider}"
    return await oauth[provider].authorize_redirect(request, redirect_uri)


@router.get("/auth/callback/{provider}")
async def auth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """Handle the OAuth provider callback and issue a JWT.

    This endpoint exchanges the authorization code for a token, fetches
    the user's profile, creates or updates a local ``User`` record,
    then returns a JWT in the response.  In a real deployment, this
    would also set a secure HTTP-only cookie.
    """
    if provider not in oauth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown auth provider")
    token = await oauth[provider].authorize_access_token(request)
    if provider == "google":
        user_info = await oauth.google.parse_id_token(request, token)
        email = user_info.get("email")
        name = user_info.get("name")
    elif provider == "github":
        user_info = await oauth.github.get("user", token=token)
        email = user_info.json().get("email") or user_info.json().get("login")
        name = user_info.json().get("name") or user_info.json().get("login")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by provider")

    # Create or update the user in the database
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        user = models.User(email=email, name=name, role="viewer")  # default role viewer
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # update name if changed
        updated = False
        if name and user.name != name:
            user.name = name
            updated = True
        if updated:
            db.commit()

    access_token = create_access_token(user_id=user.id, role=user.role)
    return {"access_token": access_token, "token_type": "bearer"}


# OAuth2 scheme for protected API endpoints
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # tokenUrl is unused since we use external providers


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """Retrieve the current user from the JWT.

    Args:
        token: The bearer token from the Authorization header.
        db: Database session dependency.

    Returns:
        The corresponding ``User`` instance.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(roles: List[str]) -> Callable[[models.User], models.User]:
    """Factory to enforce that the current user has one of the required roles.

    Usage::

        @app.get(..., dependencies=[Depends(require_role(["admin", "editor"]))])
        async def protected_endpoint(...):
            ...

    Args:
        roles: A list of roles allowed to access the endpoint.

    Returns:
        A dependency function that yields the current user if authorized.
    """

    def role_dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return role_dependency
