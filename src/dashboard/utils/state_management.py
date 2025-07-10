"""
State Management Utilities

Handles session state, page state, and global application state.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def initialize_session_state():
    """Initialize all session state variables for the dashboard."""
    
    # Core navigation state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'overview'
    
    if 'page_visits' not in st.session_state:
        st.session_state.page_visits = {}
    
    if 'page_last_visited' not in st.session_state:
        st.session_state.page_last_visited = {}
    
    # Dashboard state
    if 'dashboard_initialized' not in st.session_state:
        st.session_state.dashboard_initialized = datetime.now()
    
    if 'refresh_timestamp' not in st.session_state:
        st.session_state.refresh_timestamp = datetime.now()
    
    # Data cache state
    if 'data_cache' not in st.session_state:
        st.session_state.data_cache = {}
    
    if 'cache_timestamps' not in st.session_state:
        st.session_state.cache_timestamps = {}
    
    # User preferences
    if 'user_preferences' not in st.session_state:
        st.session_state.user_preferences = {
            'theme': 'light',
            'auto_refresh': True,
            'refresh_interval': 30,  # seconds
            'show_debug_info': False,
            'items_per_page': 20,
            'default_timeframe': '24h'
        }
    
    # Filter states for different pages
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            'products': {
                'search_query': '',
                'category': 'all',
                'price_range': [0, 10000],
                'discount_min': 0,
                'sort_by': 'price_desc'
            },
            'alerts': {
                'status': 'all',
                'priority': 'all',
                'date_range': 'all',
                'source': 'all'
            },
            'analytics': {
                'timeframe': '7d',
                'metric': 'all',
                'group_by': 'day'
            }
        }
    
    # System monitoring state
    if 'system_status' not in st.session_state:
        st.session_state.system_status = {
            'last_check': None,
            'database_status': 'unknown',
            'scraper_status': 'unknown',
            'alert_system_status': 'unknown'
        }
    
    # Notification state
    if 'notifications' not in st.session_state:
        st.session_state.notifications = []
    
    # Performance tracking
    if 'performance_metrics' not in st.session_state:
        st.session_state.performance_metrics = {
            'page_load_times': {},
            'data_fetch_times': {},
            'cache_hit_ratio': 0.0
        }

def get_page_state(page_key: str) -> Dict[str, Any]:
    """
    Get state data for a specific page.
    
    Args:
        page_key: Page identifier
        
    Returns:
        Page-specific state data
    """
    if 'page_states' not in st.session_state:
        st.session_state.page_states = {}
    
    if page_key not in st.session_state.page_states:
        st.session_state.page_states[page_key] = {
            'initialized': False,
            'last_refresh': None,
            'data_loaded': False,
            'error_count': 0,
            'scroll_position': 0
        }
    
    return st.session_state.page_states[page_key]

def update_page_state(page_key: str, updates: Dict[str, Any]):
    """
    Update state data for a specific page.
    
    Args:
        page_key: Page identifier
        updates: Dictionary of state updates
    """
    page_state = get_page_state(page_key)
    page_state.update(updates)
    st.session_state.page_states[page_key] = page_state

def get_cached_data(cache_key: str, max_age_seconds: int = 300) -> Optional[Any]:
    """
    Get cached data if it's still valid.
    
    Args:
        cache_key: Cache identifier
        max_age_seconds: Maximum age in seconds before cache expires
        
    Returns:
        Cached data or None if expired/missing
    """
    if cache_key not in st.session_state.data_cache:
        return None
    
    if cache_key not in st.session_state.cache_timestamps:
        return None
    
    # Check if cache is still valid
    cache_time = st.session_state.cache_timestamps[cache_key]
    if datetime.now() - cache_time > timedelta(seconds=max_age_seconds):
        # Cache expired, remove it
        del st.session_state.data_cache[cache_key]
        del st.session_state.cache_timestamps[cache_key]
        return None
    
    return st.session_state.data_cache[cache_key]

def set_cached_data(cache_key: str, data: Any):
    """
    Store data in cache with timestamp.
    
    Args:
        cache_key: Cache identifier
        data: Data to cache
    """
    st.session_state.data_cache[cache_key] = data
    st.session_state.cache_timestamps[cache_key] = datetime.now()

def clear_cache(cache_key: str = None):
    """
    Clear cached data.
    
    Args:
        cache_key: Specific cache key to clear, or None to clear all
    """
    if cache_key:
        if cache_key in st.session_state.data_cache:
            del st.session_state.data_cache[cache_key]
        if cache_key in st.session_state.cache_timestamps:
            del st.session_state.cache_timestamps[cache_key]
    else:
        st.session_state.data_cache = {}
        st.session_state.cache_timestamps = {}

def get_user_preference(key: str, default: Any = None) -> Any:
    """
    Get user preference value.
    
    Args:
        key: Preference key
        default: Default value if not found
        
    Returns:
        Preference value
    """
    return st.session_state.user_preferences.get(key, default)

def set_user_preference(key: str, value: Any):
    """
    Set user preference value.
    
    Args:
        key: Preference key
        value: Preference value
    """
    st.session_state.user_preferences[key] = value

def add_notification(message: str, type: str = "info", auto_dismiss: bool = True):
    """
    Add a notification to the notification queue.
    
    Args:
        message: Notification message
        type: Notification type (info/success/warning/error)
        auto_dismiss: Whether to auto-dismiss after timeout
    """
    notification = {
        'id': len(st.session_state.notifications),
        'message': message,
        'type': type,
        'timestamp': datetime.now(),
        'auto_dismiss': auto_dismiss,
        'dismissed': False
    }
    
    st.session_state.notifications.append(notification)

def get_notifications(active_only: bool = True) -> list:
    """
    Get notifications from the queue.
    
    Args:
        active_only: Whether to return only active (non-dismissed) notifications
        
    Returns:
        List of notifications
    """
    notifications = st.session_state.notifications
    
    if active_only:
        # Auto-dismiss old notifications
        now = datetime.now()
        for notification in notifications:
            if (notification['auto_dismiss'] and 
                not notification['dismissed'] and
                now - notification['timestamp'] > timedelta(seconds=5)):
                notification['dismissed'] = True
        
        return [n for n in notifications if not n['dismissed']]
    
    return notifications

def dismiss_notification(notification_id: int):
    """
    Dismiss a notification by ID.
    
    Args:
        notification_id: Notification ID to dismiss
    """
    for notification in st.session_state.notifications:
        if notification['id'] == notification_id:
            notification['dismissed'] = True
            break

def update_system_status(component: str, status: str):
    """
    Update system component status.
    
    Args:
        component: Component name (database/scraper/alert_system)
        status: Status value (online/offline/error/unknown)
    """
    st.session_state.system_status[f'{component}_status'] = status
    st.session_state.system_status['last_check'] = datetime.now()

def get_system_status() -> Dict[str, Any]:
    """
    Get current system status.
    
    Returns:
        System status dictionary
    """
    return st.session_state.system_status

def track_performance(metric_name: str, value: float):
    """
    Track performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Metric value (usually time in seconds)
    """
    if metric_name not in st.session_state.performance_metrics:
        st.session_state.performance_metrics[metric_name] = []
    
    st.session_state.performance_metrics[metric_name].append({
        'timestamp': datetime.now(),
        'value': value
    })
    
    # Keep only last 100 measurements
    if len(st.session_state.performance_metrics[metric_name]) > 100:
        st.session_state.performance_metrics[metric_name] = st.session_state.performance_metrics[metric_name][-100:]

def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics summary.
    
    Returns:
        Performance metrics dictionary
    """
    metrics = st.session_state.performance_metrics
    summary = {}
    
    for metric_name, values in metrics.items():
        if values:
            recent_values = [v['value'] for v in values[-10:]]  # Last 10 measurements
            summary[metric_name] = {
                'avg': sum(recent_values) / len(recent_values),
                'min': min(recent_values),
                'max': max(recent_values),
                'count': len(values)
            }
    
    return summary

def reset_session():
    """Reset all session state (useful for debugging)."""
    keys_to_keep = ['current_page']  # Keep navigation state
    
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    
    initialize_session_state()
    add_notification("Session reset successfully", "success") 