# -*- coding: utf-8 -*-
"""
Cross-Market Arbitrage Tool - Business-Grade Multi-Tab Dashboard

Professional dashboard with modular architecture for multi-ecommerce monitoring.
Built for scalability with MediaMarkt as the first source, ready for future expansion.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# Import page modules
from src.dashboard.pages import overview, products, alerts, analytics, sources, settings, monitoring
from src.dashboard.components.navigation import NavigationManager
from src.dashboard.utils.mongodb_loader import get_mongodb_loader
from src.dashboard.utils.styling import apply_custom_styling, load_theme_config
from src.dashboard.utils.state_management import initialize_session_state, get_page_state

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Arbitrage Control Center",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/arbitrage-tool',
        'Report a bug': 'https://github.com/your-repo/arbitrage-tool/issues',
        'About': 'Cross-Market Arbitrage Tool v1.0 - Professional ecommerce monitoring platform'
    }
)

class ArbitrageDashboard:
    """Main dashboard orchestrator for the arbitrage monitoring system."""
    
    def __init__(self):
        """Initialize the dashboard with all required components."""
        self.data_loader = get_mongodb_loader()
        self.nav_manager = NavigationManager()
        
        # Page registry for the multi-tab system
        self.pages = {
            "overview": {
                "title": "🏠 Overview",
                "module": overview,
                "description": "Main dashboard with KPIs and activity feed",
                "order": 1
            },
            "products": {
                "title": "📦 Products",
                "module": products,
                "description": "Browse and search product catalog",
                "order": 2
            },
            "alerts": {
                "title": "🚨 Alerts",
                "module": alerts,
                "description": "Manage arbitrage opportunities",
                "order": 3
            },
            "analytics": {
                "title": "📈 Analytics",
                "module": analytics,
                "description": "Business intelligence and insights",
                "order": 4
            },
            "sources": {
                "title": "🏪 Sources",
                "module": sources,
                "description": "Manage ecommerce sources",
                "order": 5
            },
            "settings": {
                "title": "⚙️ Settings",
                "module": settings,
                "description": "System configuration",
                "order": 6
            },
            "monitoring": {
                "title": "🔧 Monitoring",
                "module": monitoring,
                "description": "System health and performance",
                "order": 7
            }
        }
    
    def run(self):
        """Main dashboard execution flow."""
        try:
            # Initialize session state and styling
            initialize_session_state()
            apply_custom_styling()
            
            # Check database connectivity
            if not self._check_system_health():
                self._render_error_page()
                return
            
            # Render main dashboard
            self._render_dashboard()
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            st.error("⚠️ Dashboard Error")
            st.exception(e)
    
    def _check_system_health(self) -> bool:
        """Check if core systems are operational."""
        try:
            # Test database connection
            stats = self.data_loader.get_system_stats()
            if stats is None:
                st.error("🔴 Database connection failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            st.error(f"⚠️ System health check failed: {e}")
            return False
    
    def _render_error_page(self):
        """Render error page when system is unavailable."""
        st.title("🚨 System Unavailable")
        st.error("The arbitrage monitoring system is currently unavailable.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔧 Troubleshooting Steps")
            st.markdown("""
            1. **Check MongoDB Connection**: Verify database credentials
            2. **Check Network**: Ensure internet connectivity
            3. **Restart Services**: Try restarting the application
            4. **Check Logs**: Review system logs for errors
            """)
        
        with col2:
            st.subheader("📞 Support")
            st.markdown("""
            - **Documentation**: [Setup Guide](docs/setup-guide.md)
            - **Troubleshooting**: [Common Issues](docs/troubleshooting.md)
            - **Support**: Contact system administrator
            """)
        
        if st.button("🔄 Retry Connection"):
            st.rerun()
    
    def _render_dashboard(self):
        """Render the main dashboard interface."""
        # Header with branding and status
        self._render_header()
        
        # Navigation and page content
        self._render_navigation()
        
        # Main content area
        self._render_page_content()
        
        # Footer with system info
        self._render_footer()
    
    def _render_header(self):
        """Render professional header with branding and status."""
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown("""
            <div style="display: flex; align-items: center;">
                <h1 style="margin: 0; color: #1f77b4;">💰 Arbitrage Control Center</h1>
                <span style="margin-left: 15px; padding: 4px 8px; background-color: #28a745; color: white; border-radius: 4px; font-size: 12px;">LIVE</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Real-time status indicators
            stats = self.data_loader.get_system_stats()
            if stats:
                st.metric(
                    "🎯 Active Alerts", 
                    stats.get('active_alerts', 0),
                    delta=None
                )
        
        with col3:
            # Quick actions
            if st.button("🔄 Refresh", help="Refresh all data"):
                self.data_loader.clear_cache()
                st.rerun()
    
    def _render_navigation(self):
        """Render professional sidebar navigation."""
        with st.sidebar:
            st.markdown("### 📊 Navigation")
            
            # Page selection
            current_page = st.session_state.get('current_page', 'overview')
            
            # Create navigation buttons
            for page_key, page_info in sorted(self.pages.items(), key=lambda x: x[1]['order']):
                if st.button(
                    page_info['title'],
                    key=f"nav_{page_key}",
                    help=page_info['description'],
                    use_container_width=True
                ):
                    st.session_state.current_page = page_key
                    st.rerun()
            
            st.markdown("---")
            
            # System status sidebar
            self._render_sidebar_status()
    
    def _render_sidebar_status(self):
        """Render system status in sidebar."""
        st.markdown("### 🔋 System Status")
        
        try:
            stats = self.data_loader.get_system_stats()
            if stats:
                # Database status
                st.success("🟢 Database Online")
                
                # Quick stats
                st.metric("📦 Products", f"{stats.get('total_products', 0):,}")
                st.metric("💰 Profit Potential", f"€{stats.get('total_profit_potential', 0):,.2f}")
                
                # Last update
                now = datetime.now()
                st.caption(f"Updated: {now.strftime('%H:%M:%S')}")
            else:
                st.error("🔴 System Issues")
                
        except Exception as e:
            st.error("⚠️ Status Error")
            st.caption(str(e))
    
    def _render_page_content(self):
        """Render the selected page content."""
        current_page = st.session_state.get('current_page', 'overview')
        
        # Get page configuration
        page_config = self.pages.get(current_page)
        if not page_config:
            st.error(f"Page '{current_page}' not found")
            return
        
        # Render breadcrumb
        st.markdown(f"**{page_config['title']}** > {page_config['description']}")
        
        try:
            # Load and render the page module
            page_module = page_config['module']
            page_module.render(self.data_loader)
            
        except Exception as e:
            logger.error(f"Error rendering page {current_page}: {e}")
            st.error(f"⚠️ Error loading {page_config['title']}")
            
            with st.expander("Error Details"):
                st.exception(e)
    
    def _render_footer(self):
        """Render footer with system information."""
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.caption("🏢 **MediaMarkt.pt**")
            st.caption("Primary source active")
        
        with col2:
            st.caption("⚡ **Performance**")
            st.caption("~3.5 products/second")
        
        with col3:
            st.caption("🔄 **Last Scan**")
            st.caption("2 minutes ago")
        
        with col4:
            st.caption("📊 **Version**")
            st.caption("v1.0.0 Professional")


def main():
    """Main application entry point."""
    try:
        dashboard = ArbitrageDashboard()
        dashboard.run()
        
    except Exception as e:
        logger.error(f"Critical dashboard error: {e}")
        st.error("🚨 Critical Error")
        st.error("The dashboard encountered a critical error. Please contact support.")
        
        if st.checkbox("Show technical details"):
            st.exception(e)


if __name__ == "__main__":
    main() 