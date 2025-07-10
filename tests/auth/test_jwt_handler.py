"""
Unit tests for JWT authentication handler.
"""

import pytest
from datetime import datetime, timedelta
from jose import JWTError
from src.auth.jwt_handler import (
    JWTHandler, create_access_token, verify_token,
    hash_password, verify_password
)
from src.auth.models import UserRole, TokenData


class TestJWTHandler:
    """Test cases for JWT handler."""
    
    def test_create_access_token(self):
        """Test creating a valid access token."""
        handler = JWTHandler()
        user_id = 1
        username = "testuser"
        role = UserRole.USER
        
        token = handler.create_access_token(
            user_id=user_id,
            username=username,
            role=role
        )
        
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically longer
    
    def test_create_access_token_with_custom_expiry(self):
        """Test creating token with custom expiration."""
        handler = JWTHandler()
        expires_delta = timedelta(minutes=60)
        
        token = handler.create_access_token(
            user_id=1,
            username="testuser",
            role=UserRole.USER,
            expires_delta=expires_delta
        )
        
        assert isinstance(token, str)
        
        # Verify the token contains correct data
        token_data = handler.verify_token(token)
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.user_id == 1
        assert token_data.role == UserRole.USER
    
    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        handler = JWTHandler()
        
        # Create token
        token = handler.create_access_token(
            user_id=42,
            username="validuser",
            role=UserRole.ADMIN
        )
        
        # Verify token
        token_data = handler.verify_token(token)
        
        assert token_data is not None
        assert isinstance(token_data, TokenData)
        assert token_data.username == "validuser"
        assert token_data.user_id == 42
        assert token_data.role == UserRole.ADMIN
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        handler = JWTHandler()
        
        invalid_token = "invalid.jwt.token"
        token_data = handler.verify_token(invalid_token)
        
        assert token_data is None
    
    def test_verify_malformed_token(self):
        """Test verifying a malformed token."""
        handler = JWTHandler()
        
        malformed_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.malformed"
        token_data = handler.verify_token(malformed_token)
        
        assert token_data is None
    
    def test_verify_token_with_invalid_role(self):
        """Test token with invalid role value."""
        handler = JWTHandler()
        
        # Create token with valid structure but invalid role
        from jose import jwt
        
        payload = {
            "sub": "testuser",
            "user_id": 1,
            "role": "invalid_role",  # Invalid role
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, handler.secret_key, algorithm=handler.algorithm)
        token_data = handler.verify_token(token)
        
        assert token_data is None
    
    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        handler = JWTHandler()
        
        refresh_token = handler.create_refresh_token(
            user_id=1,
            username="testuser"
        )
        
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 50
    
    def test_convenience_functions(self):
        """Test convenience functions work correctly."""
        # Test create_access_token function
        token = create_access_token(
            user_id=1,
            username="testuser",
            role=UserRole.USER
        )
        
        assert isinstance(token, str)
        
        # Test verify_token function
        token_data = verify_token(token)
        
        assert token_data is not None
        assert token_data.username == "testuser"
        assert token_data.user_id == 1
        assert token_data.role == UserRole.USER


class TestPasswordHandling:
    """Test cases for password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert hashed != password  # Should be different
        assert len(hashed) > 50  # Bcrypt hashes are long
        assert hashed.startswith("$2b$")  # Bcrypt identifier
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        
        hash1 = hash_password(password1)
        hash2 = hash_password(password2)
        
        assert hash1 != hash2
    
    def test_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "samepassword"
        
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Due to random salt
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenSecurity:
    """Test cases for token security features."""
    
    def test_token_contains_expected_claims(self):
        """Test that tokens contain all expected claims."""
        handler = JWTHandler()
        
        token = handler.create_access_token(
            user_id=1,
            username="testuser",
            role=UserRole.USER
        )
        
        # Decode without verification to check claims
        from jose import jwt
        payload = jwt.get_unverified_claims(token)
        
        assert "sub" in payload  # Subject (username)
        assert "user_id" in payload
        assert "role" in payload
        assert "exp" in payload  # Expiration
        assert "iat" in payload  # Issued at
        assert "type" in payload  # Token type
        
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert payload["role"] == "user"
        assert payload["type"] == "access"
    
    def test_token_expiration(self):
        """Test token expiration handling."""
        handler = JWTHandler()
        
        # Create token with very short expiration
        expired_token = handler.create_access_token(
            user_id=1,
            username="testuser",
            role=UserRole.USER,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        # Should return None for expired token
        token_data = handler.verify_token(expired_token)
        assert token_data is None
    
    def test_token_algorithm_security(self):
        """Test that only expected algorithm is accepted."""
        handler = JWTHandler()
        
        # Create token with different algorithm
        from jose import jwt
        
        payload = {
            "sub": "testuser",
            "user_id": 1,
            "role": "user",
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # Create token with 'none' algorithm (security risk)
        malicious_token = jwt.encode(payload, "", algorithm="none")
        
        # Should not verify
        token_data = handler.verify_token(malicious_token)
        assert token_data is None 