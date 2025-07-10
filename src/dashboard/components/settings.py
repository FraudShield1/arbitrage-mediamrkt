"""Settings management component for system configuration."""

import streamlit as st
import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from ..utils.mongodb_loader import MongoDBDataLoader


class SettingsManager:
    """Dashboard component for managing system settings."""
    
    def __init__(self, data_loader: MongoDBDataLoader):
        """Initialize settings manager.
        
        Args:
            data_loader: MongoDBDataLoader instance for data operations
        """
        self.data_loader = data_loader
    
    def render(self) -> None:
        """Render the settings management interface."""
        st.title("⚙️ System Settings")
        st.markdown("Configure system parameters and notification settings")
        
        # Load current settings
        settings = self._load_settings()
        if not settings:
            st.warning("Unable to load settings")
            return
        
        # Settings tabs
        tabs = st.tabs(["🔧 Scraping", "🎯 Matching", "🚨 Alerts", "📢 Notifications", "🔑 API", "🖥️ System", "💾 Backup"])
        
        with tabs[0]:
            self._render_scraping_settings(settings)
        
        with tabs[1]:
            self._render_matching_settings(settings)
        
        with tabs[2]:
            self._render_alert_settings(settings)
        
        with tabs[3]:
            self._render_notification_settings(settings)
        
        with tabs[4]:
            self._render_api_settings(settings)
        
        with tabs[5]:
            self._render_system_settings(settings)
        
        with tabs[6]:
            self._render_backup_restore(settings)
    
    def _load_settings(self) -> Optional[Dict[str, Any]]:
        """Load current system settings."""
        try:
            return self.data_loader.get_settings()
        except Exception as e:
            st.error(f"Error loading settings: {e}")
            return None
    
    def _render_scraping_settings(self, settings: Dict[str, Any]) -> None:
        """Render scraping configuration settings."""
        st.subheader("🕷️ Scraping Settings")
        
        with st.expander("MediaMarkt Scraping Configuration", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                scrape_interval = st.number_input(
                    "Scraping Interval (minutes)",
                    min_value=5,
                    max_value=1440,
                    value=settings.get("scraping", {}).get("interval_minutes", 30),
                    help="How often to scrape MediaMarkt for new products"
                )
                
                max_pages = st.number_input(
                    "Max Pages per Category",
                    min_value=1,
                    max_value=100,
                    value=settings.get("scraping", {}).get("max_pages", 10),
                    help="Maximum pages to scrape per category"
                )
                
                request_delay = st.slider(
                    "Request Delay (seconds)",
                    min_value=1.0,
                    max_value=10.0,
                    value=settings.get("scraping", {}).get("request_delay", 2.0),
                    step=0.5,
                    help="Delay between requests to avoid rate limiting"
                )
            
            with col2:
                retry_attempts = st.number_input(
                    "Retry Attempts",
                    min_value=1,
                    max_value=10,
                    value=settings.get("scraping", {}).get("retry_attempts", 3),
                    help="Number of retry attempts for failed requests"
                )
                
                use_proxies = st.checkbox(
                    "Use Proxy Rotation",
                    value=settings.get("scraping", {}).get("use_proxies", False),
                    help="Enable proxy rotation to avoid IP blocking"
                )
                
                headless_mode = st.checkbox(
                    "Headless Browser Mode",
                    value=settings.get("scraping", {}).get("headless", True),
                    help="Run browser in headless mode for better performance"
                )
            
            # Categories to scrape
            st.markdown("**Categories to Scrape:**")
            available_categories = [
                "Electronics", "Home & Garden", "Sports", "Fashion", 
                "Books", "Gaming", "Health & Beauty", "Automotive"
            ]
            
            selected_categories = st.multiselect(
                "Select Categories",
                options=available_categories,
                default=settings.get("scraping", {}).get("categories", available_categories[:4]),
                help="Categories to scrape from MediaMarkt"
            )
            
            if st.button("💾 Save Scraping Settings"):
                scraping_settings = {
                    "interval_minutes": scrape_interval,
                    "max_pages": max_pages,
                    "request_delay": request_delay,
                    "retry_attempts": retry_attempts,
                    "use_proxies": use_proxies,
                    "headless": headless_mode,
                    "categories": selected_categories
                }
                self._update_settings("scraping", scraping_settings)
    
    def _render_matching_settings(self, settings: Dict[str, Any]) -> None:
        """Render product matching configuration."""
        st.subheader("🔗 Product Matching Settings")
        
        with st.expander("Matching Algorithm Configuration", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                ean_confidence = st.slider(
                    "EAN Match Confidence Threshold",
                    min_value=0.5,
                    max_value=1.0,
                    value=settings.get("matching", {}).get("ean_confidence", 0.95),
                    step=0.01,
                    help="Minimum confidence for EAN-based matches"
                )
                
                fuzzy_confidence = st.slider(
                    "Fuzzy Match Confidence Threshold", 
                    min_value=0.5,
                    max_value=1.0,
                    value=settings.get("matching", {}).get("fuzzy_confidence", 0.85),
                    step=0.01,
                    help="Minimum confidence for fuzzy string matches"
                )
                
                semantic_confidence = st.slider(
                    "Semantic Match Confidence Threshold",
                    min_value=0.5,
                    max_value=1.0,
                    value=settings.get("matching", {}).get("semantic_confidence", 0.80),
                    step=0.01,
                    help="Minimum confidence for semantic matches"
                )
            
            with col2:
                enable_ean = st.checkbox(
                    "Enable EAN Matching",
                    value=settings.get("matching", {}).get("enable_ean", True),
                    help="Use EAN codes for product matching"
                )
                
                enable_fuzzy = st.checkbox(
                    "Enable Fuzzy Matching",
                    value=settings.get("matching", {}).get("enable_fuzzy", True),
                    help="Use fuzzy string matching for products"
                )
                
                enable_semantic = st.checkbox(
                    "Enable Semantic Matching",
                    value=settings.get("matching", {}).get("enable_semantic", True),
                    help="Use AI-powered semantic matching"
                )
                
                max_matches_per_product = st.number_input(
                    "Max Matches per Product",
                    min_value=1,
                    max_value=10,
                    value=settings.get("matching", {}).get("max_matches", 3),
                    help="Maximum Amazon matches to store per MediaMarkt product"
                )
            
            if st.button("💾 Save Matching Settings"):
                matching_settings = {
                    "ean_confidence": ean_confidence,
                    "fuzzy_confidence": fuzzy_confidence,
                    "semantic_confidence": semantic_confidence,
                    "enable_ean": enable_ean,
                    "enable_fuzzy": enable_fuzzy,
                    "enable_semantic": enable_semantic,
                    "max_matches": max_matches_per_product
                }
                self._update_settings("matching", matching_settings)
    
    def _render_alert_settings(self, settings: Dict[str, Any]) -> None:
        """Render alert configuration settings."""
        st.subheader("🚨 Alert Settings")
        
        with st.expander("Alert Criteria Configuration", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                min_profit_amount = st.number_input(
                    "Minimum Profit Amount (€)",
                    min_value=0.0,
                    value=settings.get("alerts", {}).get("min_profit_amount", 10.0),
                    step=1.0,
                    help="Minimum profit required to trigger an alert"
                )
                
                min_roi_percentage = st.slider(
                    "Minimum ROI Percentage",
                    min_value=0,
                    max_value=200,
                    value=settings.get("alerts", {}).get("min_roi_percentage", 30),
                    help="Minimum ROI percentage to trigger an alert"
                )
                
                max_price_limit = st.number_input(
                    "Maximum Product Price (€)",
                    min_value=0.0,
                    value=settings.get("alerts", {}).get("max_price_limit", 1000.0),
                    step=10.0,
                    help="Maximum product price to consider for alerts"
                )
            
            with col2:
                alert_frequency = st.selectbox(
                    "Alert Check Frequency",
                    options=["Every 5 minutes", "Every 15 minutes", "Every 30 minutes", "Hourly"],
                    index=["Every 5 minutes", "Every 15 minutes", "Every 30 minutes", "Hourly"].index(
                        settings.get("alerts", {}).get("frequency", "Every 15 minutes")
                    ),
                    help="How often to check for new arbitrage opportunities"
                )
                
                auto_dismiss_days = st.number_input(
                    "Auto-dismiss Alerts After (days)",
                    min_value=1,
                    max_value=30,
                    value=settings.get("alerts", {}).get("auto_dismiss_days", 7),
                    help="Automatically dismiss alerts after this many days"
                )
                
                duplicate_prevention = st.checkbox(
                    "Prevent Duplicate Alerts",
                    value=settings.get("alerts", {}).get("prevent_duplicates", True),
                    help="Prevent multiple alerts for the same product within 24 hours"
                )
            
            # Priority categories
            st.markdown("**High Priority Categories:**")
            priority_categories = st.multiselect(
                "Categories for Critical Alerts",
                options=["Electronics", "Home & Garden", "Sports", "Fashion", "Books", "Gaming"],
                default=settings.get("alerts", {}).get("priority_categories", ["Electronics"]),
                help="Categories that should generate critical priority alerts"
            )
            
            if st.button("💾 Save Alert Settings"):
                alert_settings = {
                    "min_profit_amount": min_profit_amount,
                    "min_roi_percentage": min_roi_percentage,
                    "max_price_limit": max_price_limit,
                    "frequency": alert_frequency,
                    "auto_dismiss_days": auto_dismiss_days,
                    "prevent_duplicates": duplicate_prevention,
                    "priority_categories": priority_categories
                }
                self._update_settings("alerts", alert_settings)
    
    def _render_notification_settings(self, settings: Dict[str, Any]) -> None:
        """Render notification configuration."""
        st.subheader("📢 Notification Settings")
        
        with st.expander("Notification Channels", expanded=False):
            # Email notifications
            st.markdown("**📧 Email Notifications**")
            col1, col2 = st.columns(2)
            
            with col1:
                enable_email = st.checkbox(
                    "Enable Email Notifications",
                    value=settings.get("notifications", {}).get("email", {}).get("enabled", False)
                )
                
                if enable_email:
                    email_addresses = st.text_area(
                        "Email Addresses (one per line)",
                        value="\n".join(settings.get("notifications", {}).get("email", {}).get("addresses", [])),
                        help="Enter email addresses to receive notifications"
                    )
            
            with col2:
                if enable_email:
                    email_frequency = st.selectbox(
                        "Email Frequency",
                        options=["Immediate", "Hourly Summary", "Daily Summary"],
                        index=["Immediate", "Hourly Summary", "Daily Summary"].index(
                            settings.get("notifications", {}).get("email", {}).get("frequency", "Immediate")
                        )
                    )
                    
                    critical_only = st.checkbox(
                        "Critical Alerts Only",
                        value=settings.get("notifications", {}).get("email", {}).get("critical_only", False)
                    )
            
            # Telegram notifications
            st.markdown("**📱 Telegram Notifications**")
            col3, col4 = st.columns(2)
            
            with col3:
                enable_telegram = st.checkbox(
                    "Enable Telegram Notifications",
                    value=settings.get("notifications", {}).get("telegram", {}).get("enabled", False)
                )
                
                if enable_telegram:
                    telegram_token = st.text_input(
                        "Bot Token",
                        value=settings.get("notifications", {}).get("telegram", {}).get("bot_token", ""),
                        type="password",
                        help="Telegram bot token for sending notifications"
                    )
            
            with col4:
                if enable_telegram:
                    telegram_chat_id = st.text_input(
                        "Chat ID",
                        value=settings.get("notifications", {}).get("telegram", {}).get("chat_id", ""),
                        help="Telegram chat ID to send notifications to"
                    )
            
            # Slack notifications
            st.markdown("**💬 Slack Notifications**")
            col5, col6 = st.columns(2)
            
            with col5:
                enable_slack = st.checkbox(
                    "Enable Slack Notifications",
                    value=settings.get("notifications", {}).get("slack", {}).get("enabled", False)
                )
                
                if enable_slack:
                    slack_webhook = st.text_input(
                        "Webhook URL",
                        value=settings.get("notifications", {}).get("slack", {}).get("webhook_url", ""),
                        type="password",
                        help="Slack webhook URL for sending notifications"
                    )
            
            with col6:
                if enable_slack:
                    slack_channel = st.text_input(
                        "Channel",
                        value=settings.get("notifications", {}).get("slack", {}).get("channel", "#arbitrage"),
                        help="Slack channel to send notifications to"
                    )
            
            if st.button("💾 Save Notification Settings"):
                notification_settings = {
                    "email": {
                        "enabled": enable_email,
                        "addresses": email_addresses.split("\n") if enable_email and email_addresses else [],
                        "frequency": email_frequency if enable_email else "Immediate",
                        "critical_only": critical_only if enable_email else False
                    },
                    "telegram": {
                        "enabled": enable_telegram,
                        "bot_token": telegram_token if enable_telegram else "",
                        "chat_id": telegram_chat_id if enable_telegram else ""
                    },
                    "slack": {
                        "enabled": enable_slack,
                        "webhook_url": slack_webhook if enable_slack else "",
                        "channel": slack_channel if enable_slack else "#arbitrage"
                    }
                }
                self._update_settings("notifications", notification_settings)
    
    def _render_api_settings(self, settings: Dict[str, Any]) -> None:
        """Render API configuration settings."""
        st.subheader("🔑 API Settings")
        
        with st.expander("External API Configuration", expanded=False):
            # Keepa API settings
            st.markdown("**📈 Keepa API**")
            col1, col2 = st.columns(2)
            
            with col1:
                keepa_api_key = st.text_input(
                    "Keepa API Key",
                    value=settings.get("apis", {}).get("keepa", {}).get("api_key", ""),
                    type="password",
                    help="Your Keepa API key for price history data"
                )
                
                keepa_rate_limit = st.number_input(
                    "Rate Limit (requests/minute)",
                    min_value=1,
                    max_value=300,
                    value=settings.get("apis", {}).get("keepa", {}).get("rate_limit", 60),
                    help="Keepa API rate limit"
                )
            
            with col2:
                keepa_timeout = st.number_input(
                    "Request Timeout (seconds)",
                    min_value=5,
                    max_value=60,
                    value=settings.get("apis", {}).get("keepa", {}).get("timeout", 30),
                    help="Timeout for Keepa API requests"
                )
                
                keepa_retry_attempts = st.number_input(
                    "Retry Attempts",
                    min_value=1,
                    max_value=5,
                    value=settings.get("apis", {}).get("keepa", {}).get("retry_attempts", 3),
                    help="Number of retry attempts for failed API calls"
                )
            
            if st.button("💾 Save API Settings"):
                api_settings = {
                    "keepa": {
                        "api_key": keepa_api_key,
                        "rate_limit": keepa_rate_limit,
                        "timeout": keepa_timeout,
                        "retry_attempts": keepa_retry_attempts
                    }
                }
                self._update_settings("apis", api_settings)
    
    def _render_system_settings(self, settings: Dict[str, Any]) -> None:
        """Render system configuration settings."""
        st.subheader("🖥️ System Settings")
        
        with st.expander("System Configuration", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                debug_mode = st.checkbox(
                    "Debug Mode",
                    value=settings.get("system", {}).get("debug", False),
                    help="Enable debug logging and detailed error messages"
                )
                
                log_level = st.selectbox(
                    "Log Level",
                    options=["DEBUG", "INFO", "WARNING", "ERROR"],
                    index=["DEBUG", "INFO", "WARNING", "ERROR"].index(
                        settings.get("system", {}).get("log_level", "INFO")
                    ),
                    help="Minimum log level to record"
                )
                
                max_log_files = st.number_input(
                    "Max Log Files",
                    min_value=1,
                    max_value=100,
                    value=settings.get("system", {}).get("max_log_files", 10),
                    help="Maximum number of log files to keep"
                )
            
            with col2:
                database_pool_size = st.number_input(
                    "Database Pool Size",
                    min_value=1,
                    max_value=50,
                    value=settings.get("system", {}).get("db_pool_size", 10),
                    help="Database connection pool size"
                )
                
                cache_ttl = st.number_input(
                    "Cache TTL (minutes)",
                    min_value=1,
                    max_value=1440,
                    value=settings.get("system", {}).get("cache_ttl", 60),
                    help="Time-to-live for cached data"
                )
                
                cleanup_interval = st.number_input(
                    "Data Cleanup Interval (days)",
                    min_value=1,
                    max_value=365,
                    value=settings.get("system", {}).get("cleanup_interval", 30),
                    help="How often to clean up old data"
                )
            
            if st.button("💾 Save System Settings"):
                system_settings = {
                    "debug": debug_mode,
                    "log_level": log_level,
                    "max_log_files": max_log_files,
                    "db_pool_size": database_pool_size,
                    "cache_ttl": cache_ttl,
                    "cleanup_interval": cleanup_interval
                }
                self._update_settings("system", system_settings)
    
    def _render_backup_restore(self, settings: Dict[str, Any]) -> None:
        """Render backup and restore functionality."""
        st.subheader("💾 Backup & Restore")
        
        with st.expander("Data Management", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📤 Export Settings**")
                
                if st.button("📋 Export All Settings"):
                    settings_json = json.dumps(settings, indent=2)
                    st.download_button(
                        label="💾 Download Settings JSON",
                        data=settings_json,
                        file_name=f"arbitrage_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                if st.button("📊 Export System Data"):
                    self._export_system_data()
            
            with col2:
                st.markdown("**📥 Import Settings**")
                
                uploaded_file = st.file_uploader(
                    "Upload Settings JSON",
                    type=["json"],
                    help="Upload a previously exported settings file"
                )
                
                if uploaded_file is not None:
                    try:
                        imported_settings = json.load(uploaded_file)
                        
                        if st.button("⚠️ Import Settings (This will overwrite current settings)"):
                            self._import_settings(imported_settings)
                            st.success("Settings imported successfully!")
                            st.rerun()
                    
                    except json.JSONDecodeError:
                        st.error("Invalid JSON file")
                
                if st.button("🗑️ Reset to Defaults"):
                    if st.session_state.get("confirm_reset"):
                        self._reset_to_defaults()
                        st.session_state.confirm_reset = False
                        st.success("Settings reset to defaults!")
                        st.rerun()
                    else:
                        st.session_state.confirm_reset = True
                        st.warning("Click again to confirm reset to defaults")
    
    def _update_settings(self, category: str, new_settings: Dict[str, Any]) -> None:
        """Update settings for a specific category."""
        try:
            success = self.data_loader.update_settings(category, new_settings)
            if success:
                st.success(f"✅ {category.title()} settings saved successfully!")
                st.rerun()
            else:
                st.error(f"❌ Failed to save {category} settings")
        except Exception as e:
            st.error(f"Error saving settings: {e}")
    
    def _export_system_data(self) -> None:
        """Export system data for backup."""
        try:
            data = self.data_loader.export_system_data()
            if data:
                st.download_button(
                    label="💾 Download System Data",
                    data=json.dumps(data, indent=2),
                    file_name=f"arbitrage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            else:
                st.error("Failed to export system data")
        except Exception as e:
            st.error(f"Error exporting data: {e}")
    
    def _import_settings(self, settings: Dict[str, Any]) -> None:
        """Import settings from uploaded file."""
        try:
            success = self.data_loader.import_settings(settings)
            if not success:
                st.error("Failed to import settings")
        except Exception as e:
            st.error(f"Error importing settings: {e}")
    
    def _reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        try:
            success = self.data_loader.reset_settings_to_defaults()
            if not success:
                st.error("Failed to reset settings")
        except Exception as e:
            st.error(f"Error resetting settings: {e}")


def render_settings_management(data_loader: MongoDBDataLoader) -> None:
    """Render the settings management component.
    
    Args:
        data_loader: MongoDBDataLoader instance for fetching/updating data
    """
    manager = SettingsManager(data_loader)
    manager.render() 