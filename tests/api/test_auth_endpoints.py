"""
Unit tests for authentication API endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User, UserRole
from src.auth.jwt_handler import hash_password


class TestAuthEndpoints:
    """Test cases for authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """Test successful user login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with invalid username."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "password"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, test_user: User):
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        """Test login with inactive user."""
        # Create inactive user
        inactive_user = User(
            username="inactiveuser",
            email="inactive@example.com",
            hashed_password=hash_password("password"),
            role=UserRole.USER,
            is_active=False
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "inactiveuser",
                "password": "password"
            }
        )
        
        assert response.status_code == 403
        assert "Account is inactive" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_current_user_info(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user information."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_get_current_user_info_unauthorized(self, client: AsyncClient):
        """Test getting user info without authentication."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, auth_headers: dict):
        """Test token refresh."""
        response = await client.post(
            "/api/v1/auth/refresh",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful password change."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_change_password_invalid_current(self, client: AsyncClient, auth_headers: dict):
        """Test password change with invalid current password."""
        response = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid current password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_current_user(self, client: AsyncClient, auth_headers: dict):
        """Test updating current user information."""
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={
                "email": "newemail@example.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "newemail@example.com"
        assert data["username"] == "testuser"  # Should not change


class TestAdminEndpoints:
    """Test cases for admin-only endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient, admin_headers: dict):
        """Test successful user registration by admin."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_headers,
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "role": "user"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "user"
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_register_user_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Test user registration by non-admin user."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "role": "user"
            }
        )
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, admin_headers: dict):
        """Test registration with duplicate username."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_headers,
            json={
                "username": "testuser",  # Already exists
                "email": "another@example.com",
                "password": "password123",
                "role": "user"
            }
        )
        
        assert response.status_code == 409
        assert "Username already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, admin_headers: dict):
        """Test registration with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            headers=admin_headers,
            json={
                "username": "anotheruser",
                "email": "test@example.com",  # Already exists
                "password": "password123",
                "role": "user"
            }
        )
        
        assert response.status_code == 409
        assert "Email already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, admin_headers: dict):
        """Test listing all users by admin."""
        response = await client.get(
            "/api/v1/auth/users",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 2  # At least test_user and test_admin
        
        # Check that users are ordered by created_at desc
        usernames = [user["username"] for user in data]
        assert "testadmin" in usernames
        assert "testuser" in usernames
    
    @pytest.mark.asyncio
    async def test_list_users_non_admin(self, client: AsyncClient, auth_headers: dict):
        """Test listing users by non-admin user."""
        response = await client.get(
            "/api/v1/auth/users",
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, client: AsyncClient, admin_headers: dict, test_user: User):
        """Test getting user by ID."""
        response = await client.get(
            f"/api/v1/auth/users/{test_user.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_user.id
        assert data["username"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient, admin_headers: dict):
        """Test getting non-existent user."""
        response = await client.get(
            "/api/v1/auth/users/99999",
            headers=admin_headers
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_user_by_admin(self, client: AsyncClient, admin_headers: dict, test_user: User):
        """Test updating user by admin."""
        response = await client.put(
            f"/api/v1/auth/users/{test_user.id}",
            headers=admin_headers,
            json={
                "email": "updated@example.com",
                "role": "read_only",
                "is_active": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "updated@example.com"
        assert data["role"] == "read_only"
        assert data["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
        """Test successful user deletion."""
        # Create user to delete
        user_to_delete = User(
            username="deleteme",
            email="delete@example.com",
            hashed_password=hash_password("password"),
            role=UserRole.USER
        )
        db_session.add(user_to_delete)
        await db_session.commit()
        await db_session.refresh(user_to_delete)
        
        response = await client.delete(
            f"/api/v1/auth/users/{user_to_delete.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 200
        assert "User deleted successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_delete_self_forbidden(self, client: AsyncClient, admin_headers: dict, test_admin: User):
        """Test that admin cannot delete themselves."""
        response = await client.delete(
            f"/api/v1/auth/users/{test_admin.id}",
            headers=admin_headers
        )
        
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]


class TestAuthenticationFlow:
    """Test cases for complete authentication flows."""
    
    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self, client: AsyncClient, admin_headers: dict):
        """Test complete user lifecycle: create, login, update, delete."""
        # 1. Create user
        create_response = await client.post(
            "/api/v1/auth/register",
            headers=admin_headers,
            json={
                "username": "lifecycle_user",
                "email": "lifecycle@example.com",
                "password": "password123",
                "role": "user"
            }
        )
        assert create_response.status_code == 201
        user_data = create_response.json()
        user_id = user_data["id"]
        
        # 2. Login as new user
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "lifecycle_user",
                "password": "password123"
            }
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        user_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        # 3. Get user info
        me_response = await client.get(
            "/api/v1/auth/me",
            headers=user_headers
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "lifecycle_user"
        
        # 4. Update user info
        update_response = await client.put(
            "/api/v1/auth/me",
            headers=user_headers,
            json={"email": "updated_lifecycle@example.com"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["email"] == "updated_lifecycle@example.com"
        
        # 5. Change password
        password_response = await client.post(
            "/api/v1/auth/change-password",
            headers=user_headers,
            json={
                "current_password": "password123",
                "new_password": "newpassword456"
            }
        )
        assert password_response.status_code == 200
        
        # 6. Login with new password
        new_login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "lifecycle_user",
                "password": "newpassword456"
            }
        )
        assert new_login_response.status_code == 200
        
        # 7. Delete user (admin action)
        delete_response = await client.delete(
            f"/api/v1/auth/users/{user_id}",
            headers=admin_headers
        )
        assert delete_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_token_expiration_handling(self, client: AsyncClient):
        """Test handling of expired tokens."""
        # This would require mocking token expiration
        # For now, we test invalid token format
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        
        response = await client.get(
            "/api/v1/auth/me",
            headers=invalid_headers
        )
        
        assert response.status_code == 401 