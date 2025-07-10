"""
JWT token handling for authentication and authorization.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import structlog

from src.config.settings import get_settings
from .models import TokenData, UserRole

logger = structlog.get_logger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class JWTHandler:
    """JWT token handler for authentication."""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_minutes = settings.JWT_EXPIRATION_MINUTES
    
    def create_access_token(
        self, 
        user_id: int, 
        username: str, 
        role: UserRole,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User ID
            username: Username
            role: User role
            expires_delta: Custom expiration time
            
        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.expiration_minutes)
        
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "role": role.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.info(
            "Access token created",
            user_id=user_id,
            username=username,
            role=role.value,
            expires_at=expire.isoformat()
        )
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            role_str: str = payload.get("role")
            
            if username is None or user_id is None or role_str is None:
                logger.warning("Invalid token payload", payload=payload)
                return None
            
            # Validate role
            try:
                role = UserRole(role_str)
            except ValueError:
                logger.warning("Invalid role in token", role=role_str)
                return None
            
            token_data = TokenData(
                username=username,
                user_id=user_id,
                role=role
            )
            
            logger.debug("Token verified successfully", username=username, user_id=user_id)
            return token_data
            
        except JWTError as e:
            logger.warning("JWT verification failed", error=str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error during token verification", error=str(e))
            return None
    
    def create_refresh_token(self, user_id: int, username: str) -> str:
        """
        Create a refresh token for token renewal.
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            Refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=7)  # Refresh tokens last 7 days
        
        to_encode = {
            "sub": username,
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.info(
            "Refresh token created",
            user_id=user_id,
            username=username,
            expires_at=expire.isoformat()
        )
        
        return encoded_jwt


# Password utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# Global instance
jwt_handler = JWTHandler()


# Convenience functions
def create_access_token(
    user_id: int, 
    username: str, 
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create access token using global handler."""
    return jwt_handler.create_access_token(user_id, username, role, expires_delta)


def verify_token(token: str) -> Optional[TokenData]:
    """Verify token using global handler."""
    return jwt_handler.verify_token(token)


def create_refresh_token(user_id: int, username: str) -> str:
    """Create refresh token using global handler."""
    return jwt_handler.create_refresh_token(user_id, username) 