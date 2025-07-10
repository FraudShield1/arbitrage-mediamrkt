"""
Sources Page - Ecommerce Source Management

Manage ecommerce sources and configure scraping for future expansion.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from src.dashboard.utils.mongodb_loader import get_mongodb_loader
from src.dashboard.utils.state_management import get_page_state, update_page_state

logger = logging.getLogger(__name__)

def render():
    """Render the Sources page."""
    
    # Page setup
    page_state = get_page_state('sources')
    
    # Header
    st.markdown("## 🏪 Ecommerce Sources")
    st.markdown("*Manage and configure ecommerce sources for arbitrage monitoring*")
    st.markdown("---")
    
    try:
        # Load data
        data_loader = get_mongodb_loader()
        
        # Current sources overview
        _render_sources_overview()
        
        # Main content tabs
        tab1, tab2, tab3 = st.tabs(["📊 Active Sources", "🔧 Configuration", "➕ Add Source"])
        
        with tab1:
            _render_active_sources(data_loader)
        
        with tab2:
            _render_source_configuration(data_loader)
        
        with tab3:
            _render_add_source_form()
        
        # Update page state
        update_page_state('sources', {
            'last_refresh': datetime.now(),
            'data_loaded': True,
            'error_count': 0
        })
        
    except Exception as e:
        logger.error(f"Error rendering Sources page: {e}")
        st.error("⚠️ Error loading sources data")
        st.exception(e)

def _render_sources_overview():
    """Render sources overview metrics."""
    
    st.markdown("### 📈 Sources Overview")
    
    # Mock data for current system state
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Sources", 1)  # Currently only MediaMarkt
    
    with col2:
        st.metric("Total Products", "696")  # From current system
    
    with col3:
        st.metric("Scraping Success", "100%")
    
    with col4:
        st.metric("Last Update", "2 min ago")

def _render_active_sources(data_loader):
    """Render active sources status."""
    
    st.markdown("### 📊 Active Sources Status")
    
    # Current source: MediaMarkt
    sources_data = [
        {
            'name': 'MediaMarkt',
            'status': 'Active',
            'url': 'https://www.mediamarkt.de',
            'products': 696,
            'success_rate': 100.0,
            'last_scrape': '2 minutes ago',
            'response_time': '145ms',
            'categories': ['smartphones', 'laptops', 'gaming', 'tv', 'audio'],
            'enabled': True
        }
    ]
    
    for source in sources_data:
        with st.expander(f"🏪 {source['name']} - {source['status']}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**URL**: {source['url']}")
                st.markdown(f"**Categories**: {', '.join(source['categories'])}")
                st.markdown(f"**Last Scrape**: {source['last_scrape']}")
                
                # Performance metrics
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Products", source['products'])
                with col_b:
                    st.metric("Success Rate", f"{source['success_rate']:.1f}%")
                with col_c:
                    st.metric("Response Time", source['response_time'])
            
            with col2:
                # Source controls
                st.markdown("**Controls**")
                
                enabled = st.checkbox(
                    "Enable Scraping",
                    value=source['enabled'],
                    key=f"enable_{source['name']}"
                )
                
                col_x, col_y = st.columns(2)
                with col_x:
                    if st.button("🔄 Refresh", key=f"refresh_{source['name']}"):
                        st.success("Refresh triggered")
                
                with col_y:
                    if st.button("⚙️ Configure", key=f"config_{source['name']}"):
                        st.info("Configuration modal would open")

def _render_source_configuration(data_loader):
    """Render source configuration settings."""
    
    st.markdown("### 🔧 Source Configuration")
    
    # MediaMarkt configuration
    st.markdown("#### 🏪 MediaMarkt Settings")
    
    with st.form("mediamarkt_config"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Scraping Settings**")
            
            scrape_interval = st.selectbox(
                "Scraping Interval",
                [1, 2, 5, 10, 15, 30],
                index=1,  # 2 minutes
                format_func=lambda x: f"{x} minute{'s' if x > 1 else ''}",
                help="How often to scrape this source"
            )
            
            max_products = st.number_input(
                "Max Products per Scrape",
                min_value=10,
                max_value=1000,
                value=100,
                step=10,
                help="Maximum products to scrape in one cycle"
            )
            
            timeout = st.slider(
                "Request Timeout (seconds)",
                min_value=5,
                max_value=60,
                value=30,
                help="Timeout for HTTP requests"
            )
        
        with col2:
            st.markdown("**Categories to Monitor**")
            
            all_categories = ['smartphones', 'laptops', 'tablets', 'gaming', 'tv', 'audio', 'accessories']
            selected_categories = st.multiselect(
                "Active Categories",
                all_categories,
                default=['smartphones', 'laptops', 'gaming', 'tv', 'audio'],
                help="Product categories to scrape"
            )
            
            st.markdown("**Alert Thresholds**")
            
            min_discount = st.slider(
                "Minimum Discount for Alerts (%)",
                min_value=10,
                max_value=50,
                value=30,
                help="Minimum discount percentage to trigger alerts"
            )
            
            min_price = st.number_input(
                "Minimum Price for Alerts (€)",
                min_value=10,
                max_value=500,
                value=50,
                help="Minimum product price to consider for alerts"
            )
        
        if st.form_submit_button("💾 Save Configuration", use_container_width=True):
            st.success("✅ MediaMarkt configuration saved successfully!")
            st.info("Configuration would be applied to the scraping system")

def _render_add_source_form():
    """Render form to add new ecommerce source."""
    
    st.markdown("### ➕ Add New Ecommerce Source")
    
    st.info("💡 **Future Expansion**: Add new ecommerce sources to expand arbitrage monitoring beyond MediaMarkt")
    
    with st.form("add_source_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Source Information")
            
            source_name = st.text_input(
                "Source Name",
                placeholder="e.g., Saturn, Amazon, eBay",
                help="Display name for the ecommerce source"
            )
            
            source_url = st.text_input(
                "Base URL",
                placeholder="https://www.example.com",
                help="Base URL of the ecommerce website"
            )
            
            source_type = st.selectbox(
                "Source Type",
                ["Ecommerce Website", "Marketplace", "Price Comparison"],
                help="Type of source for appropriate scraping strategy"
            )
            
            country = st.selectbox(
                "Country",
                ["Germany", "Austria", "Netherlands", "Switzerland", "Other"],
                help="Primary country/market for this source"
            )
        
        with col2:
            st.markdown("#### Scraping Configuration")
            
            categories = st.multiselect(
                "Available Categories",
                ['smartphones', 'laptops', 'tablets', 'gaming', 'tv', 'audio', 'accessories', 'home', 'fashion'],
                default=['smartphones', 'laptops'],
                help="Product categories available from this source"
            )
            
            scraping_method = st.selectbox(
                "Scraping Method",
                ["Playwright (Browser)", "Requests (HTTP)", "API", "RSS/XML Feed"],
                help="Method to use for data extraction"
            )
            
            rate_limit = st.slider(
                "Rate Limit (requests/minute)",
                min_value=1,
                max_value=60,
                value=10,
                help="Maximum requests per minute to avoid blocking"
            )
            
            requires_auth = st.checkbox(
                "Requires Authentication",
                help="Check if this source requires login or API keys"
            )
        
        st.markdown("#### Selectors Configuration")
        
        with st.expander("🔍 CSS Selectors (Advanced)", expanded=False):
            st.markdown("Configure CSS selectors for data extraction:")
            
            col_a, col_b = st.columns(2)
            with col_a:
                product_title_selector = st.text_input(
                    "Product Title Selector",
                    placeholder="h1.product-title, .title",
                    help="CSS selector for product title"
                )
                
                price_selector = st.text_input(
                    "Price Selector", 
                    placeholder=".price, .current-price",
                    help="CSS selector for current price"
                )
            
            with col_b:
                original_price_selector = st.text_input(
                    "Original Price Selector",
                    placeholder=".old-price, .was-price",
                    help="CSS selector for original/crossed-out price"
                )
                
                availability_selector = st.text_input(
                    "Availability Selector",
                    placeholder=".in-stock, .availability",
                    help="CSS selector for stock status"
                )
        
        submitted = st.form_submit_button("🚀 Add Source", use_container_width=True)
        
        if submitted:
            if not source_name or not source_url:
                st.error("Please provide both source name and URL")
            else:
                # Mock source creation
                st.success(f"✅ Source '{source_name}' configuration saved!")
                st.info("🔧 **Implementation Note**: Source would be added to configuration and require backend implementation for scraping logic")
                
                # Show what would be created
                with st.expander("📋 Configuration Preview"):
                    config = {
                        'name': source_name,
                        'url': source_url,
                        'type': source_type,
                        'country': country,
                        'categories': categories,
                        'scraping_method': scraping_method,
                        'rate_limit': rate_limit,
                        'requires_auth': requires_auth,
                        'selectors': {
                            'title': product_title_selector,
                            'price': price_selector,
                            'original_price': original_price_selector,
                            'availability': availability_selector
                        }
                    }
                    st.json(config)

# Future expansion helper
def _render_future_sources_info():
    """Render information about planned future sources."""
    
    st.markdown("---")
    st.markdown("### 🚀 Planned Future Sources")
    
    future_sources = [
        {"name": "Saturn", "status": "Planned", "priority": "High", "market": "Germany"},
        {"name": "Amazon DE", "status": "Research", "priority": "High", "market": "Germany"},
        {"name": "eBay DE", "status": "Planned", "priority": "Medium", "market": "Germany"},
        {"name": "Cyberport", "status": "Research", "priority": "Medium", "market": "Germany"},
        {"name": "Alternate", "status": "Planned", "priority": "Low", "market": "Germany"}
    ]
    
    df = pd.DataFrame(future_sources)
    st.dataframe(df, use_container_width=True)
    
    st.info("💡 **Expansion Strategy**: Gradual rollout starting with major German electronics retailers, then expanding to other European markets.") 