"""
Authentication API routes for user management and JWT token handling.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from src.config.database import get_db_session
from src.auth.models import (
    User, UserCreate, UserUpdate, UserResponse, 
    LoginRequest, LoginResponse, PasswordChangeRequest
)
from src.auth.jwt_handler import (
    create_access_token, create_refresh_token, 
    hash_password, verify_password
)
from src.auth.middleware import (
    get_current_active_user, require_admin, require_auth
)
from src.auth.models import UserRole

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_admin)  # Only admins can create users
):
    """
    Register a new user (admin only).
    
    Args:
        user_data: User creation data
        db: Database session
        current_user: Current admin user
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If username/email already exists
    """
    logger.info("User registration attempt", username=user_data.username, email=user_data.email)
    
    # Check if username already exists
    stmt = select(User).where(User.username == user_data.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        logger.warning("Username already exists", username=user_data.username)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Check if email already exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        logger.warning("Email already exists", email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    logger.info(
        "User created successfully",
        user_id=db_user.id,
        username=db_user.username,
        role=db_user.role.value,
        created_by=current_user.username
    )
    
    return db_user


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    User login with username and password.
    
    Args:
        login_data: Login credentials
        db: Database session
        
    Returns:
        Access token and user information
        
    Raises:
        HTTPException: If credentials are invalid
    """
    logger.info("Login attempt", username=login_data.username)
    
    # Get user from database
    stmt = select(User).where(User.username == login_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        logger.warning("Invalid login credentials", username=login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        logger.warning("Inactive user login attempt", username=login_data.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Update last login time
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role
    )
    
    logger.info(
        "User logged in successfully",
        user_id=user.id,
        username=user.username,
        role=user.role.value
    )
    
    return LoginResponse(
        access_token=access_token,
        user=user
    )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
    """
    Refresh access token.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        New access token
    """
    logger.info("Token refresh", user_id=current_user.id, username=current_user.username)
    
    access_token = create_access_token(
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user information
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update current user information.
    
    Args:
        user_update: User update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user information
    """
    logger.info("User update attempt", user_id=current_user.id, username=current_user.username)
    
    # Update allowed fields
    if user_update.email is not None:
        # Check if email already exists (excluding current user)
        stmt = select(User).where(User.email == user_update.email, User.id != current_user.id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
        current_user.email = user_update.email
    
    # Only admin can change role and active status
    if current_user.role == UserRole.ADMIN:
        if user_update.role is not None:
            current_user.role = user_update.role
        if user_update.is_active is not None:
            current_user.is_active = user_update.is_active
    
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    
    logger.info("User updated successfully", user_id=current_user.id)
    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Change user password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If current password is invalid
    """
    logger.info("Password change attempt", user_id=current_user.id, username=current_user.username)
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        logger.warning("Invalid current password", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    # Hash and update new password
    current_user.hashed_password = hash_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    await db.commit()
    
    logger.info("Password changed successfully", user_id=current_user.id)
    return {"message": "Password changed successfully"}


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all users (admin only).
    
    Args:
        current_user: Current admin user
        db: Database session
        
    Returns:
        List of all users
    """
    logger.info("Users list requested", admin_user_id=current_user.id)
    
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get user by ID (admin only).
    
    Args:
        user_id: User ID
        current_user: Current admin user
        db: Database session
        
    Returns:
        User information
        
    Raises:
        HTTPException: If user not found
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Update user by ID (admin only).
    
    Args:
        user_id: User ID
        user_update: User update data
        current_user: Current admin user
        db: Database session
        
    Returns:
        Updated user information
        
    Raises:
        HTTPException: If user not found
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.email is not None:
        # Check if email already exists (excluding current user)
        stmt = select(User).where(User.email == user_update.email, User.id != user_id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
        user.email = user_update.email
    
    if user_update.role is not None:
        user.role = user_update.role
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    logger.info(
        "User updated by admin",
        user_id=user.id,
        admin_user_id=current_user.id
    )
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Delete user by ID (admin only).
    
    Args:
        user_id: User ID
        current_user: Current admin user
        db: Database session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If user not found or trying to delete self
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    logger.info(
        "User deleted by admin",
        deleted_user_id=user_id,
        admin_user_id=current_user.id
    )
    
    return {"message": "User deleted successfully"} 