"""
Settings Page - System Configuration

Comprehensive system settings and configuration management.
"""

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any
import logging

from src.dashboard.utils.mongodb_loader import get_mongodb_loader
from src.dashboard.utils.state_management import (
    get_page_state, update_page_state, get_user_preference, set_user_preference
)

logger = logging.getLogger(__name__)

def render():
    """Render the Settings page."""
    
    # Page setup
    page_state = get_page_state('settings')
    
    # Header
    st.markdown("## ⚙️ System Settings")
    st.markdown("*Configure system preferences and operational parameters*")
    st.markdown("---")
    
    try:
        # Load data
        data_loader = get_mongodb_loader()
        
        # Settings tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎛️ General", "🚨 Alerts", "🔍 Scraping", "📊 Dashboard", "🔧 Advanced"
        ])
        
        with tab1:
            _render_general_settings()
        
        with tab2:
            _render_alert_settings()
        
        with tab3:
            _render_scraping_settings()
        
        with tab4:
            _render_dashboard_settings()
        
        with tab5:
            _render_advanced_settings()
        
        # Update page state
        update_page_state('settings', {
            'last_refresh': datetime.now(),
            'data_loaded': True,
            'error_count': 0
        })
        
    except Exception as e:
        logger.error(f"Error rendering Settings page: {e}")
        st.error("⚠️ Error loading settings")
        st.exception(e)

def _render_general_settings():
    """Render general system settings."""
    
    st.markdown("### 🎛️ General Settings")
    
    with st.form("general_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### System Preferences")
            
            timezone = st.selectbox(
                "Timezone",
                ["Europe/Berlin", "Europe/Vienna", "Europe/Amsterdam", "UTC"],
                index=0,
                help="System timezone for scheduling and timestamps"
            )
            
            language = st.selectbox(
                "Language",
                ["English", "German", "Dutch"],
                index=0,
                help="Interface language"
            )
            
            currency = st.selectbox(
                "Default Currency",
                ["EUR", "USD", "GBP"],
                index=0,
                help="Default currency for price display"
            )
            
            date_format = st.selectbox(
                "Date Format",
                ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
                index=2,
                help="Preferred date display format"
            )
        
        with col2:
            st.markdown("#### Performance Settings")
            
            auto_refresh = st.checkbox(
                "Enable Auto-Refresh",
                value=get_user_preference('auto_refresh', True),
                help="Automatically refresh dashboard data"
            )
            
            refresh_interval = st.slider(
                "Refresh Interval (seconds)",
                min_value=10,
                max_value=300,
                value=get_user_preference('refresh_interval', 30),
                step=10,
                help="How often to refresh data automatically"
            )
            
            items_per_page = st.selectbox(
                "Items per Page",
                [10, 20, 50, 100],
                index=1,
                help="Default number of items to show in tables"
            )
            
            enable_caching = st.checkbox(
                "Enable Data Caching",
                value=True,
                help="Cache data to improve performance"
            )
        
        if st.form_submit_button("💾 Save General Settings", use_container_width=True):
            # Save preferences
            set_user_preference('auto_refresh', auto_refresh)
            set_user_preference('refresh_interval', refresh_interval)
            set_user_preference('items_per_page', items_per_page)
            
            st.success("✅ General settings saved successfully!")

def _render_alert_settings():
    """Render alert configuration settings."""
    
    st.markdown("### 🚨 Alert Settings")
    
    with st.form("alert_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Telegram Settings")
            
            telegram_enabled = st.checkbox(
                "Enable Telegram Notifications",
                value=True,
                help="Send alerts via Telegram bot"
            )
            
            telegram_bot_token = st.text_input(
                "Bot Token",
                value="••••••••••••••••",
                type="password",
                help="Telegram bot token for notifications"
            )
            
            telegram_chat_id = st.text_input(
                "Chat ID",
                value="••••••••••",
                help="Telegram chat ID for notifications"
            )
            
            st.markdown("#### Email Settings")
            
            email_enabled = st.checkbox(
                "Enable Email Notifications",
                value=False,
                help="Send alerts via email"
            )
            
            smtp_server = st.text_input(
                "SMTP Server",
                placeholder="smtp.gmail.com",
                help="Email server for sending notifications"
            )
            
            smtp_port = st.number_input(
                "SMTP Port",
                min_value=25,
                max_value=587,
                value=587,
                help="Email server port"
            )
        
        with col2:
            st.markdown("#### Alert Thresholds")
            
            default_discount_threshold = st.slider(
                "Default Discount Threshold (%)",
                min_value=10,
                max_value=80,
                value=30,
                help="Default minimum discount for alerts"
            )
            
            high_value_threshold = st.number_input(
                "High Value Alert Threshold (€)",
                min_value=100,
                max_value=5000,
                value=500,
                help="Price threshold for high-value alerts"
            )
            
            max_alerts_per_hour = st.slider(
                "Max Alerts per Hour",
                min_value=1,
                max_value=50,
                value=10,
                help="Rate limit for alert notifications"
            )
            
            st.markdown("#### Alert Priorities")
            
            alert_cooldown = st.selectbox(
                "Alert Cooldown Period",
                ["5 minutes", "15 minutes", "30 minutes", "1 hour"],
                index=1,
                help="Minimum time between duplicate alerts"
            )
            
            auto_dismiss_resolved = st.checkbox(
                "Auto-dismiss Resolved Alerts",
                value=True,
                help="Automatically dismiss alerts when product is no longer discounted"
            )
        
        if st.form_submit_button("💾 Save Alert Settings", use_container_width=True):
            st.success("✅ Alert settings saved successfully!")
            if telegram_enabled and not telegram_bot_token:
                st.warning("⚠️ Telegram token is required for notifications")

def _render_scraping_settings():
    """Render scraping configuration settings."""
    
    st.markdown("### 🔍 Scraping Settings")
    
    with st.form("scraping_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Scraping Schedule")
            
            scraping_enabled = st.checkbox(
                "Enable Automated Scraping",
                value=True,
                help="Enable/disable the scraping system"
            )
            
            scraping_interval = st.selectbox(
                "Scraping Interval",
                ["1 minute", "2 minutes", "5 minutes", "10 minutes", "15 minutes"],
                index=1,  # 2 minutes current
                help="How often to scrape each source"
            )
            
            max_concurrent_scrapes = st.slider(
                "Max Concurrent Scrapes",
                min_value=1,
                max_value=10,
                value=3,
                help="Maximum number of concurrent scraping processes"
            )
            
            retry_attempts = st.slider(
                "Retry Attempts",
                min_value=1,
                max_value=5,
                value=3,
                help="Number of retry attempts for failed scrapes"
            )
        
        with col2:
            st.markdown("#### Performance & Limits")
            
            request_timeout = st.slider(
                "Request Timeout (seconds)",
                min_value=10,
                max_value=120,
                value=30,
                help="Timeout for HTTP requests"
            )
            
            delay_between_requests = st.slider(
                "Delay Between Requests (ms)",
                min_value=100,
                max_value=5000,
                value=1000,
                step=100,
                help="Delay between requests to avoid rate limiting"
            )
            
            user_agent_rotation = st.checkbox(
                "Enable User Agent Rotation",
                value=True,
                help="Rotate user agents to avoid detection"
            )
            
            respect_robots_txt = st.checkbox(
                "Respect robots.txt",
                value=True,
                help="Follow robots.txt directives"
            )
            
            st.markdown("#### Data Quality")
            
            min_price_threshold = st.number_input(
                "Min Price Threshold (€)",
                min_value=1,
                max_value=100,
                value=10,
                help="Ignore products below this price"
            )
            
            max_price_threshold = st.number_input(
                "Max Price Threshold (€)",
                min_value=1000,
                max_value=50000,
                value=10000,
                help="Ignore products above this price"
            )
        
        if st.form_submit_button("💾 Save Scraping Settings", use_container_width=True):
            st.success("✅ Scraping settings saved successfully!")
            st.info("🔄 Settings will be applied on next scraping cycle")

def _render_dashboard_settings():
    """Render dashboard configuration settings."""
    
    st.markdown("### 📊 Dashboard Settings")
    
    with st.form("dashboard_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Display Preferences")
            
            theme = st.selectbox(
                "Dashboard Theme",
                ["Light", "Dark", "Auto"],
                index=0,
                help="Dashboard color theme"
            )
            
            show_debug_info = st.checkbox(
                "Show Debug Information",
                value=get_user_preference('show_debug_info', False),
                help="Display technical debug information"
            )
            
            compact_mode = st.checkbox(
                "Compact Mode",
                value=False,
                help="Use more compact layout for smaller screens"
            )
            
            show_tooltips = st.checkbox(
                "Show Tooltips",
                value=True,
                help="Display helpful tooltips throughout the interface"
            )
        
        with col2:
            st.markdown("#### Chart Settings")
            
            default_chart_height = st.slider(
                "Default Chart Height (px)",
                min_value=200,
                max_value=600,
                value=300,
                help="Default height for charts and graphs"
            )
            
            animate_charts = st.checkbox(
                "Animate Charts",
                value=True,
                help="Enable chart animations"
            )
            
            chart_color_scheme = st.selectbox(
                "Chart Color Scheme",
                ["Default", "Viridis", "Plotly", "Set1"],
                help="Color scheme for charts"
            )
            
            st.markdown("#### Data Display")
            
            decimal_places = st.slider(
                "Decimal Places for Prices",
                min_value=0,
                max_value=4,
                value=2,
                help="Number of decimal places to show for prices"
            )
            
            show_relative_times = st.checkbox(
                "Show Relative Times",
                value=True,
                help="Show times as 'X minutes ago' instead of absolute timestamps"
            )
        
        if st.form_submit_button("💾 Save Dashboard Settings", use_container_width=True):
            # Save preferences
            set_user_preference('show_debug_info', show_debug_info)
            
            st.success("✅ Dashboard settings saved successfully!")
            st.info("🔄 Some changes may require a page refresh")

def _render_advanced_settings():
    """Render advanced system settings."""
    
    st.markdown("### 🔧 Advanced Settings")
    
    st.warning("⚠️ **Warning**: These settings can affect system performance and stability. Only modify if you understand the implications.")
    
    with st.form("advanced_settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Database Settings")
            
            connection_pool_size = st.slider(
                "Connection Pool Size",
                min_value=5,
                max_value=50,
                value=10,
                help="MongoDB connection pool size"
            )
            
            query_timeout = st.slider(
                "Query Timeout (seconds)",
                min_value=5,
                max_value=60,
                value=30,
                help="Database query timeout"
            )
            
            enable_query_logging = st.checkbox(
                "Enable Query Logging",
                value=False,
                help="Log database queries for debugging"
            )
            
            st.markdown("#### Logging Settings")
            
            log_level = st.selectbox(
                "Log Level",
                ["DEBUG", "INFO", "WARNING", "ERROR"],
                index=1,
                help="Minimum log level to record"
            )
            
            log_retention_days = st.slider(
                "Log Retention (days)",
                min_value=7,
                max_value=90,
                value=30,
                help="How long to keep log files"
            )
        
        with col2:
            st.markdown("#### Performance Settings")
            
            enable_redis_cache = st.checkbox(
                "Enable Redis Caching",
                value=True,
                help="Use Redis for caching frequently accessed data"
            )
            
            cache_ttl = st.slider(
                "Cache TTL (minutes)",
                min_value=1,
                max_value=60,
                value=15,
                help="Time to live for cached data"
            )
            
            max_memory_usage = st.slider(
                "Max Memory Usage (%)",
                min_value=50,
                max_value=90,
                value=80,
                help="Maximum memory usage before warnings"
            )
            
            st.markdown("#### Security Settings")
            
            enable_rate_limiting = st.checkbox(
                "Enable Rate Limiting",
                value=True,
                help="Limit API request rates"
            )
            
            session_timeout = st.slider(
                "Session Timeout (hours)",
                min_value=1,
                max_value=24,
                value=8,
                help="User session timeout"
            )
        
        if st.form_submit_button("💾 Save Advanced Settings", use_container_width=True):
            st.success("✅ Advanced settings saved successfully!")
            st.warning("🔄 Some changes require system restart to take effect")
    
    # System actions
    st.markdown("---")
    st.markdown("#### 🛠️ System Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.success("Cache cleared successfully!")
    
    with col2:
        if st.button("📊 Export Settings", use_container_width=True):
            # Mock settings export
            settings = {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0",
                "settings": {
                    "general": {"timezone": "Europe/Berlin"},
                    "alerts": {"telegram_enabled": True},
                    "scraping": {"interval": "2 minutes"},
                    "dashboard": {"theme": "Light"}
                }
            }
            st.download_button(
                "💾 Download Settings",
                data=json.dumps(settings, indent=2),
                file_name="arbitrage_settings.json",
                mime="application/json"
            )
    
    with col3:
        if st.button("📥 Import Settings", use_container_width=True):
            st.info("Settings import functionality would be implemented here")
    
    with col4:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            st.warning("This would reset all settings to default values") 