"""
API Versioning System for Cross-Market Arbitrage Tool

Provides comprehensive API versioning with backward compatibility,
deprecation management, and seamless version transitions.
"""

from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import structlog
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.routing import APIRoute
from pydantic import BaseModel
import warnings

logger = structlog.get_logger(__name__)


class VersionStatus(Enum):
    """API version status."""
    ACTIVE = "active"           # Current active version
    DEPRECATED = "deprecated"   # Deprecated but still supported
    SUNSET = "sunset"          # Will be removed soon
    REMOVED = "removed"        # No longer supported


@dataclass
class APIVersion:
    """API version configuration."""
    version: str
    status: VersionStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    removal_date: Optional[datetime] = None
    description: str = ""
    changelog: List[str] = None
    
    def __post_init__(self):
        if self.changelog is None:
            self.changelog = []


class VersionManager:
    """
    API Version Management System.
    
    Handles version registration, routing, deprecation warnings,
    and backward compatibility management.
    """
    
    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.version_routes: Dict[str, Dict[str, APIRoute]] = {}
        self.default_version: Optional[str] = None
        self.current_version: Optional[str] = None
        
        # Setup initial versions
        self._setup_initial_versions()
    
    def _setup_initial_versions(self):
        """Setup initial API versions."""
        now = datetime.now()
        
        # V1.0 - Initial release
        self.register_version(APIVersion(
            version="v1.0",
            status=VersionStatus.DEPRECATED,
            release_date=now - timedelta(days=180),
            deprecation_date=now - timedelta(days=90),
            sunset_date=now + timedelta(days=90),
            removal_date=now + timedelta(days=180),
            description="Initial API release with basic arbitrage functionality",
            changelog=[
                "Basic product search and comparison",
                "Simple price tracking",
                "Basic authentication"
            ]
        ))
        
        # V1.1 - Enhanced features
        self.register_version(APIVersion(
            version="v1.1",
            status=VersionStatus.ACTIVE,
            release_date=now - timedelta(days=90),
            description="Enhanced API with improved search and analytics",
            changelog=[
                "Advanced product matching algorithms",
                "Enhanced price history tracking",
                "Improved authentication and authorization",
                "Real-time notifications",
                "Dashboard analytics"
            ]
        ))
        
        # V2.0 - Major revision
        self.register_version(APIVersion(
            version="v2.0",
            status=VersionStatus.ACTIVE,
            release_date=now,
            description="Major API revision with breaking changes and new features",
            changelog=[
                "Redesigned API structure",
                "Enhanced data models",
                "Improved performance and scalability",
                "Advanced monitoring and alerting",
                "Comprehensive testing framework"
            ]
        ))
        
        self.set_default_version("v2.0")
        self.set_current_version("v2.0")
    
    def register_version(self, version: APIVersion):
        """Register a new API version."""
        self.versions[version.version] = version
        self.version_routes[version.version] = {}
        
        logger.info(f"Registered API version {version.version}",
                   status=version.status.value,
                   release_date=version.release_date.isoformat())
    
    def set_default_version(self, version: str):
        """Set the default API version."""
        if version not in self.versions:
            raise ValueError(f"Version {version} not registered")
        
        self.default_version = version
        logger.info(f"Set default API version to {version}")
    
    def set_current_version(self, version: str):
        """Set the current active API version."""
        if version not in self.versions:
            raise ValueError(f"Version {version} not registered")
        
        self.current_version = version
        logger.info(f"Set current API version to {version}")
    
    def deprecate_version(self, version: str, sunset_days: int = 90, removal_days: int = 180):
        """Deprecate an API version."""
        if version not in self.versions:
            raise ValueError(f"Version {version} not registered")
        
        now = datetime.now()
        version_obj = self.versions[version]
        version_obj.status = VersionStatus.DEPRECATED
        version_obj.deprecation_date = now
        version_obj.sunset_date = now + timedelta(days=sunset_days)
        version_obj.removal_date = now + timedelta(days=removal_days)
        
        logger.warning(f"Deprecated API version {version}",
                      sunset_date=version_obj.sunset_date.isoformat(),
                      removal_date=version_obj.removal_date.isoformat())
    
    def get_version_from_request(self, request: Request) -> str:
        """Extract API version from request."""
        # Check Accept header (e.g., application/vnd.api+json;version=2.0)
        accept_header = request.headers.get("accept", "")
        if "version=" in accept_header:
            version_part = accept_header.split("version=")[1].split(";")[0].split(",")[0]
            if version_part.startswith("v"):
                return version_part
            else:
                return f"v{version_part}"
        
        # Check custom version header
        version_header = request.headers.get("api-version", "")
        if version_header:
            if version_header.startswith("v"):
                return version_header
            else:
                return f"v{version_header}"
        
        # Check query parameter
        version_param = request.query_params.get("version", "")
        if version_param:
            if version_param.startswith("v"):
                return version_param
            else:
                return f"v{version_param}"
        
        # Check URL path (e.g., /api/v2.0/products)
        path_parts = request.url.path.split("/")
        for part in path_parts:
            if part.startswith("v") and any(c.isdigit() for c in part):
                return part
        
        # Return default version
        return self.default_version
    
    def validate_version(self, version: str) -> APIVersion:
        """Validate and return version information."""
        if version not in self.versions:
            available_versions = list(self.versions.keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid API version",
                    "requested_version": version,
                    "available_versions": available_versions,
                    "current_version": self.current_version
                }
            )
        
        version_obj = self.versions[version]
        
        # Check if version is removed
        if version_obj.status == VersionStatus.REMOVED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "error": f"API version {version} has been removed",
                    "removal_date": version_obj.removal_date.isoformat() if version_obj.removal_date else None,
                    "current_version": self.current_version
                }
            )
        
        return version_obj
    
    def add_deprecation_headers(self, response: Response, version: str):
        """Add deprecation headers to response."""
        version_obj = self.versions.get(version)
        if not version_obj:
            return
        
        if version_obj.status in [VersionStatus.DEPRECATED, VersionStatus.SUNSET]:
            response.headers["Deprecation"] = "true"
            response.headers["API-Version"] = version
            response.headers["Current-Version"] = self.current_version
            
            if version_obj.sunset_date:
                response.headers["Sunset"] = version_obj.sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            # Add link to migration guide
            response.headers["Link"] = f'</api/migration>; rel="successor-version"; version="{self.current_version}"'
    
    def get_version_info(self, version: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed version information."""
        if version:
            if version not in self.versions:
                raise ValueError(f"Version {version} not registered")
            
            version_obj = self.versions[version]
            return {
                "version": version_obj.version,
                "status": version_obj.status.value,
                "release_date": version_obj.release_date.isoformat(),
                "deprecation_date": version_obj.deprecation_date.isoformat() if version_obj.deprecation_date else None,
                "sunset_date": version_obj.sunset_date.isoformat() if version_obj.sunset_date else None,
                "removal_date": version_obj.removal_date.isoformat() if version_obj.removal_date else None,
                "description": version_obj.description,
                "changelog": version_obj.changelog
            }
        else:
            # Return all versions
            return {
                "default_version": self.default_version,
                "current_version": self.current_version,
                "versions": {
                    v: self.get_version_info(v) for v in self.versions.keys()
                }
            }
    
    def get_migration_guide(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """Generate migration guide between versions."""
        if from_version not in self.versions:
            raise ValueError(f"Source version {from_version} not registered")
        if to_version not in self.versions:
            raise ValueError(f"Target version {to_version} not registered")
        
        from_ver = self.versions[from_version]
        to_ver = self.versions[to_version]
        
        # Generate basic migration guide
        guide = {
            "from_version": from_version,
            "to_version": to_version,
            "breaking_changes": [],
            "new_features": [],
            "deprecated_features": [],
            "migration_steps": [],
            "timeline": {}
        }
        
        # Add version-specific migration information
        if from_version == "v1.0" and to_version in ["v1.1", "v2.0"]:
            guide["breaking_changes"] = [
                "Authentication endpoints moved from /auth to /api/v2.0/auth",
                "Product search response structure changed",
                "Error response format updated"
            ]
            guide["new_features"] = [
                "Advanced product matching",
                "Real-time notifications",
                "Enhanced analytics"
            ]
            guide["migration_steps"] = [
                "1. Update authentication endpoints",
                "2. Update product search response parsing",
                "3. Implement new error handling",
                "4. Test with new features"
            ]
        
        if from_version == "v1.1" and to_version == "v2.0":
            guide["breaking_changes"] = [
                "Product model structure updated",
                "Price tracking API redesigned",
                "Dashboard endpoints restructured"
            ]
            guide["new_features"] = [
                "Enhanced monitoring",
                "Improved performance",
                "Advanced testing framework"
            ]
            guide["migration_steps"] = [
                "1. Update product model handling",
                "2. Migrate price tracking integration",
                "3. Update dashboard endpoints",
                "4. Implement new monitoring"
            ]
        
        # Add timeline information
        if from_ver.sunset_date:
            guide["timeline"]["migration_deadline"] = from_ver.sunset_date.isoformat()
        if from_ver.removal_date:
            guide["timeline"]["version_removal"] = from_ver.removal_date.isoformat()
        
        return guide


# Global version manager instance
version_manager = VersionManager()


def get_api_version(request: Request) -> str:
    """Dependency to get API version from request."""
    version = version_manager.get_version_from_request(request)
    version_obj = version_manager.validate_version(version)
    
    # Log usage for analytics
    logger.info("API version used",
               version=version,
               status=version_obj.status.value,
               path=request.url.path,
               method=request.method)
    
    return version


def add_version_headers(version: str = Depends(get_api_version)):
    """Middleware to add version headers to response."""
    def middleware(request: Request, call_next):
        response = call_next(request)
        version_manager.add_deprecation_headers(response, version)
        return response
    return middleware


def versioned_route(version: str):
    """Decorator to mark routes for specific API versions."""
    def decorator(func: Callable):
        func._api_version = version
        return func
    return decorator


class VersionedAPIRoute(APIRoute):
    """Custom API route that handles versioning."""
    
    def __init__(self, *args, **kwargs):
        self.supported_versions = kwargs.pop('supported_versions', None)
        super().__init__(*args, **kwargs)
    
    def matches(self, scope: dict) -> tuple:
        """Check if route matches the request with version consideration."""
        match, child_scope = super().matches(scope)
        
        if match and self.supported_versions:
            # Extract version from scope/request
            request = Request(scope)
            version = version_manager.get_version_from_request(request)
            
            if version not in self.supported_versions:
                return False, {}
        
        return match, child_scope


# Version-specific response models
class BaseVersionedModel(BaseModel):
    """Base model for versioned API responses."""
    
    class Config:
        extra = "forbid"
    
    def dict(self, version: str = None, **kwargs):
        """Return dict representation for specific version."""
        data = super().dict(**kwargs)
        
        if version:
            # Apply version-specific transformations
            data = self._transform_for_version(data, version)
        
        return data
    
    def _transform_for_version(self, data: dict, version: str) -> dict:
        """Transform data for specific API version."""
        # Override in subclasses for version-specific transformations
        return data


class V1ProductResponse(BaseVersionedModel):
    """V1.0 Product response model."""
    id: str
    name: str
    price: float
    url: str
    
    def _transform_for_version(self, data: dict, version: str) -> dict:
        if version == "v1.0":
            # V1.0 format - simple structure
            return {
                "id": data["id"],
                "name": data["name"],
                "price": data["price"],
                "url": data["url"]
            }
        return data


class V2ProductResponse(BaseVersionedModel):
    """V2.0 Product response model."""
    id: str
    name: str
    price: dict  # Enhanced price structure
    metadata: dict
    links: dict
    
    def _transform_for_version(self, data: dict, version: str) -> dict:
        if version == "v1.0":
            # Backward compatibility - flatten to V1 format
            return {
                "id": data["id"],
                "name": data["name"],
                "price": data["price"].get("current", 0),
                "url": data["links"].get("product_url", "")
            }
        elif version == "v1.1":
            # V1.1 format - partial enhancement
            return {
                "id": data["id"],
                "name": data["name"],
                "price": data["price"],
                "url": data["links"].get("product_url", ""),
                "metadata": data["metadata"]
            }
        return data


# Utility functions
def get_version_info(version: Optional[str] = None) -> Dict[str, Any]:
    """Get API version information."""
    return version_manager.get_version_info(version)


def get_migration_guide(from_version: str, to_version: str) -> Dict[str, Any]:
    """Get migration guide between versions."""
    return version_manager.get_migration_guide(from_version, to_version)


def create_versioned_app() -> FastAPI:
    """Create FastAPI app with versioning support."""
    app = FastAPI(
        title="Cross-Market Arbitrage Tool API",
        description="API for finding profitable arbitrage opportunities",
        version=version_manager.current_version
    )
    
    # Add version info endpoint
    @app.get("/api/versions")
    async def api_versions():
        """Get API version information."""
        return get_version_info()
    
    @app.get("/api/migration/{from_version}/{to_version}")
    async def migration_guide(from_version: str, to_version: str):
        """Get migration guide between versions."""
        return get_migration_guide(from_version, to_version)
    
    return app


# Backward compatibility helpers
def ensure_backward_compatibility(data: Any, target_version: str) -> Any:
    """Ensure data is compatible with target version."""
    if hasattr(data, '_transform_for_version'):
        if isinstance(data, BaseVersionedModel):
            return data.dict(version=target_version)
    
    return data


def deprecation_warning(feature: str, version: str, removal_version: str):
    """Issue deprecation warning for features."""
    message = f"{feature} is deprecated in {version} and will be removed in {removal_version}"
    warnings.warn(message, DeprecationWarning, stacklevel=2)
    
    logger.warning("Deprecated feature used",
                  feature=feature,
                  current_version=version,
                  removal_version=removal_version)


# Example usage and integration points
def setup_versioned_routes(app: FastAPI):
    """Setup versioned routes for the application."""
    
    # V1 routes (deprecated)
    @app.get("/api/v1.0/products", response_model=List[V1ProductResponse])
    async def get_products_v1(version: str = Depends(get_api_version)):
        """Get products - V1.0 (deprecated)."""
        deprecation_warning("V1.0 products endpoint", "v1.1", "v2.1")
        # Implementation for V1.0
        pass
    
    # V2 routes (current)
    @app.get("/api/v2.0/products", response_model=List[V2ProductResponse])
    async def get_products_v2(version: str = Depends(get_api_version)):
        """Get products - V2.0 (current)."""
        # Implementation for V2.0
        pass
    
    # Version-agnostic route with automatic versioning
    @app.get("/api/products")
    async def get_products_auto(version: str = Depends(get_api_version)):
        """Get products - automatic versioning."""
        if version == "v1.0":
            return await get_products_v1(version)
        elif version in ["v1.1", "v2.0"]:
            return await get_products_v2(version)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported version: {version}"
            ) 