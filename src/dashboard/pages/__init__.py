"""
Dashboard Pages Package

Individual page modules for the multi-tab dashboard.
"""

# Import all page modules for easy access
from . import overview
from . import products  
from . import alerts
from . import analytics
from . import sources
from . import settings
from . import monitoring

__all__ = [
    'overview',
    'products', 
    'alerts',
    'analytics',
    'sources',
    'settings',
    'monitoring'
] 