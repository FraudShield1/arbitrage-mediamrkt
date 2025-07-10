"""
Authentication middleware and dependencies for FastAPI.
"""

from typing import Optional
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from src.config.database import get_db_session
from .jwt_handler import verify_token
from .models import User, UserRole, TokenData

logger = structlog.get_logger(__name__)

# Security scheme for FastAPI docs
security = HTTPBearer()


class AuthMiddleware:
    """Authentication middleware for request processing."""
    
    def __init__(self):
        self.logger = logger
    
    async def __call__(self, request: Request, call_next):
        """Process request through authentication middleware."""
        # Skip auth for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            response = await call_next(request)
            return response
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            token_data = verify_token(token)
            
            if token_data:
                # Add user info to request state
                request.state.user = token_data
                self.logger.debug(
                    "Request authenticated",
                    user_id=token_data.user_id,
                    username=token_data.username,
                    role=token_data.role.value
                )
            else:
                self.logger.warning("Invalid token in request", path=request.url.path)
        
        response = await call_next(request)
        return response


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP bearer token
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token
    token_data = verify_token(credentials.credentials)
    if not token_data or not token_data.username:
        logger.warning("Invalid token provided")
        raise credentials_exception
    
    # Get user from database
    try:
        stmt = select(User).where(User.username == token_data.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.warning("User not found", username=token_data.username)
            raise credentials_exception
            
        if not user.is_active:
            logger.warning("Inactive user attempted access", username=token_data.username)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        
        logger.debug("User authenticated successfully", user_id=user.id, username=user.username)
        return user
        
    except Exception as e:
        logger.error("Database error during authentication", error=str(e))
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current active user.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Create a dependency that requires a specific role.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            logger.warning(
                "Insufficient permissions",
                user_id=current_user.id,
                user_role=current_user.role.value,
                required_role=required_role.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )
        return current_user
    
    return role_dependency


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency that requires admin role.
    
    Args:
        current_user: Current user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "Admin access required",
            user_id=current_user.id,
            user_role=current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# Convenience function for route decoration
def require_auth(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Simple authentication requirement for routes.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user
    """
    return current_user 