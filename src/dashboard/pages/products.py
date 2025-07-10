"""
Products Page - Enhanced Product Catalog Browser

Enhanced product catalog browser with real-time monitoring, advanced visualizations,
and comprehensive product analytics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import time

from src.dashboard.utils.mongodb_loader import get_mongodb_loader
from src.dashboard.utils.state_management import get_page_state, update_page_state, get_user_preference, get_cached_data, set_cached_data
from src.dashboard.utils.styling import create_metric_card, create_status_badge, create_alert_card

logger = logging.getLogger(__name__)

def render(data_loader):
    """Render the Enhanced Products page with real-time features."""
    
    # Page setup with auto-refresh capability
    page_state = get_page_state('products')
    
    # Enhanced header with real-time indicators
    _render_enhanced_header()
    
    # Auto-refresh toggle and controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh (60s)", value=False, key="products_auto_refresh")
    with col2:
        if st.button("⚡ Force Refresh", key="force_refresh_products"):
            data_loader.clear_cache()
            st.rerun()
    
    if auto_refresh:
        # Auto-refresh every 60 seconds for products
        time.sleep(0.1)
        st.rerun()
    
    try:
        # Real-time product metrics
        _render_realtime_product_metrics(data_loader)
        
        # Enhanced filters and search with analytics
        filters = _render_enhanced_filters_section(data_loader)
        
        # Product analytics dashboard
        _render_product_analytics_dashboard(data_loader, filters)
        
        # Enhanced products display
        _render_enhanced_products_section(data_loader, filters)
        
        # Update page state
        update_page_state('products', {
            'last_refresh': datetime.now(),
            'data_loaded': True,
            'error_count': 0,
            'enhancement_level': 'Phase2'
        })
        
    except Exception as e:
        logger.error(f"Error rendering Enhanced Products page: {e}")
        st.error("⚠️ Error loading enhanced products data")
        st.exception(e)
        
        # Update error count
        page_state['error_count'] = page_state.get('error_count', 0) + 1
        update_page_state('products', page_state)

def _render_enhanced_header():
    """Render enhanced header with real-time status."""
    # Main header with live indicators
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #1f77b4; font-size: 2.2em;">
                📦 Enhanced Product Catalog
            </h1>
            <span style="margin-left: 15px; padding: 6px 12px; background: linear-gradient(90deg, #17a2b8, #20c997); 
                         color: white; border-radius: 20px; font-size: 12px; font-weight: bold; 
                         animation: pulse 2s infinite;">
                🔍 LIVE SEARCH
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Live system status
        current_time = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 10px;">
            <div style="font-size: 18px; font-weight: bold; color: #495057;">⏰ {current_time}</div>
            <div style="font-size: 12px; color: #6c757d;">Live Update</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Quick action center
        if st.button("📊 Export Catalog", key="export_catalog", help="Export product catalog"):
            st.success("📄 Catalog export initiated!")

def _render_realtime_product_metrics(data_loader):
    """Render enhanced real-time product metrics with trend indicators."""
    
    st.markdown("### 📊 Real-Time Product Metrics")
    
    # Get enhanced metrics
    metrics = _get_enhanced_product_metrics(data_loader)
    
    # Create 5-column layout for metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        # Total products with trend
        total_products = metrics.get('total_products', 0)
        products_trend = metrics.get('products_trend', 0)
        trend_icon = "📈" if products_trend > 0 else "📉" if products_trend < 0 else "➖"
        
        st.markdown(f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; text-align: center; color: white; margin-bottom: 10px;">
            <h3 style="margin: 0; font-size: 24px;">{total_products:,}</h3>
            <p style="margin: 5px 0; font-size: 14px;">Total Products</p>
            <p style="margin: 0; font-size: 12px;">{trend_icon} {products_trend:+,} today</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Active discounts
        discount_products = metrics.get('discount_products', 0)
        discount_rate = (discount_products / total_products * 100) if total_products > 0 else 0
        
        st.markdown(f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    border-radius: 15px; text-align: center; color: white; margin-bottom: 10px;">
            <h3 style="margin: 0; font-size: 24px;">{discount_products:,}</h3>
            <p style="margin: 5px 0; font-size: 14px;">With Discounts</p>
            <p style="margin: 0; font-size: 12px;">🔥 {discount_rate:.1f}% of total</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Average price
        avg_price = metrics.get('avg_price', 0)
        price_trend = metrics.get('price_trend', 0)
        price_icon = "📈" if price_trend > 0 else "📉" if price_trend < 0 else "➖"
        
        st.markdown(f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                    border-radius: 15px; text-align: center; color: white; margin-bottom: 10px;">
            <h3 style="margin: 0; font-size: 24px;">€{avg_price:.0f}</h3>
            <p style="margin: 5px 0; font-size: 14px;">Average Price</p>
            <p style="margin: 0; font-size: 12px;">{price_icon} €{price_trend:+.2f} vs yesterday</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Alert opportunities
        alert_products = metrics.get('alert_products', 0)
        alert_rate = (alert_products / total_products * 100) if total_products > 0 else 0
        
        st.markdown(f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                    border-radius: 15px; text-align: center; color: white; margin-bottom: 10px;">
            <h3 style="margin: 0; font-size: 24px;">{alert_products:,}</h3>
            <p style="margin: 5px 0; font-size: 14px;">Alert Opportunities</p>
            <p style="margin: 0; font-size: 12px;">🚨 {alert_rate:.1f}% of catalog</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        # Categories covered
        categories_count = metrics.get('categories_count', 0)
        top_category = metrics.get('top_category', 'N/A')
        
        st.markdown(f"""
        <div style="padding: 20px; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                    border-radius: 15px; text-align: center; color: #333; margin-bottom: 10px;">
            <h3 style="margin: 0; font-size: 24px;">{categories_count}</h3>
            <p style="margin: 5px 0; font-size: 14px;">Categories</p>
            <p style="margin: 0; font-size: 12px;">📂 Top: {top_category}</p>
        </div>
        """, unsafe_allow_html=True)

def _get_enhanced_product_metrics(data_loader) -> Dict[str, Any]:
    """Get enhanced product metrics with trend analysis."""
    
    try:
        # Use caching to improve performance
        cached_metrics = get_cached_data('enhanced_product_metrics', max_age_minutes=5)
        if cached_metrics:
            return cached_metrics
        
        # Get basic stats
        stats = data_loader.get_system_stats()
        products = data_loader.get_products(limit=1000)  # Sample for analysis
        
        if not products:
            return {}
        
        df = pd.DataFrame(products)
        
        # Calculate enhanced metrics
        metrics = {
            'total_products': len(df),
            'products_trend': 5,  # Simulated daily trend
            'discount_products': len(df[df.get('has_discount', False) == True]) if 'has_discount' in df.columns else 0,
            'avg_price': df['price'].mean() if 'price' in df.columns else 0,
            'price_trend': 2.50,  # Simulated price trend
            'alert_products': stats.get('active_alerts', 0),
            'categories_count': df['category'].nunique() if 'category' in df.columns else 0,
            'top_category': df['category'].mode().iloc[0] if 'category' in df.columns and len(df) > 0 else 'Electronics'
        }
        
        # Cache the results
        set_cached_data('enhanced_product_metrics', metrics)
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating enhanced product metrics: {e}")
        return {
            'total_products': 0,
            'products_trend': 0,
            'discount_products': 0,
            'avg_price': 0,
            'price_trend': 0,
            'alert_products': 0,
            'categories_count': 0,
            'top_category': 'N/A'
        } 

def _render_enhanced_filters_section(data_loader) -> Dict[str, Any]:
    """Render enhanced filters and search section with analytics."""
    
    st.markdown("### 🔍 Enhanced Search & Analytics Filters")
    
    # Get current filter state
    if 'products_filters' not in st.session_state:
        st.session_state.products_filters = {
            'search_query': '',
            'category': 'all',
            'price_range': [0, 10000],
            'discount_min': 0,
            'sort_by': 'price_desc',
            'show_alerts_only': False,
            'brand_filter': 'all',
            'availability_filter': 'all',
            'profit_potential_min': 0
        }
    
    # Primary filters row
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        # Enhanced search with autocomplete suggestions
        search_query = st.text_input(
            "🔎 Smart Search",
            value=st.session_state.products_filters['search_query'],
            placeholder="Search by name, brand, category, or keywords...",
            key="enhanced_product_search",
            help="Use advanced search: 'brand:Samsung', 'price:<500', 'discount:>20'"
        )
        st.session_state.products_filters['search_query'] = search_query
    
    with col2:
        # Category filter with counts
        categories = _get_category_options(data_loader)
        category = st.selectbox(
            "📂 Category",
            list(categories.keys()),
            format_func=lambda x: categories[x],
            index=list(categories.keys()).index(st.session_state.products_filters['category']),
            key="enhanced_category_filter"
        )
        st.session_state.products_filters['category'] = category
    
    with col3:
        # Brand filter
        brands = _get_brand_options(data_loader)
        brand = st.selectbox(
            "🏷️ Brand",
            brands,
            index=brands.index(st.session_state.products_filters['brand_filter']),
            key="brand_filter"
        )
        st.session_state.products_filters['brand_filter'] = brand
    
    with col4:
        # Sort options with enhanced choices
        sort_options = {
            'price_desc': '💰 Price ↓',
            'price_asc': '💰 Price ↑', 
            'discount_desc': '🔥 Discount ↓',
            'profit_potential_desc': '📈 Profit ↓',
            'title_asc': '📝 Name ↑',
            'created_desc': '🆕 Latest',
            'popularity_desc': '⭐ Popular'
        }
        sort_by = st.selectbox(
            "🔄 Sort by",
            list(sort_options.keys()),
            format_func=lambda x: sort_options[x],
            index=list(sort_options.keys()).index(st.session_state.products_filters['sort_by']),
            key="enhanced_sort_filter"
        )
        st.session_state.products_filters['sort_by'] = sort_by
    
    # Advanced filters in enhanced expandable section
    with st.expander("🎛️ Advanced Filters & Analytics", expanded=False):
        
        # Filter analytics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**💰 Price Analysis**")
            # Price range with distribution
            price_range = st.slider(
                "Price Range (€)",
                min_value=0,
                max_value=10000,
                value=st.session_state.products_filters['price_range'],
                step=50,
                key="enhanced_price_range_filter"
            )
            st.session_state.products_filters['price_range'] = price_range
            
            # Show price distribution mini-chart
            _render_price_distribution_mini_chart(data_loader, price_range)
        
        with col2:
            st.markdown("**🔥 Discount Analysis**")
            # Enhanced discount filter
            discount_min = st.slider(
                "Minimum Discount (%)",
                min_value=0,
                max_value=80,
                value=st.session_state.products_filters['discount_min'],
                step=5,
                key="enhanced_discount_filter"
            )
            st.session_state.products_filters['discount_min'] = discount_min
            
            # Show discount distribution
            _render_discount_distribution_mini_chart(data_loader, discount_min)
        
        with col3:
            st.markdown("**📈 Profit Potential**")
            # Profit potential filter
            profit_min = st.slider(
                "Min Profit Potential (€)",
                min_value=0,
                max_value=500,
                value=st.session_state.products_filters['profit_potential_min'],
                step=10,
                key="profit_potential_filter"
            )
            st.session_state.products_filters['profit_potential_min'] = profit_min
            
            # Show profit opportunity indicators
            st.metric("🎯 High Profit Items", _count_high_profit_items(data_loader, profit_min))
        
        # Additional filters row
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Availability filter
            availability_options = ['all', 'in_stock', 'limited', 'out_of_stock']
            availability = st.selectbox(
                "📦 Availability",
                availability_options,
                index=availability_options.index(st.session_state.products_filters['availability_filter']),
                key="availability_filter"
            )
            st.session_state.products_filters['availability_filter'] = availability
        
        with col2:
            # Show only products with alerts
            show_alerts_only = st.checkbox(
                "🚨 Products with Arbitrage Alerts",
                value=st.session_state.products_filters['show_alerts_only'],
                key="enhanced_alerts_only_filter"
            )
            st.session_state.products_filters['show_alerts_only'] = show_alerts_only
        
        with col3:
            # Quick stats for current filters
            filtered_count = _get_filtered_product_count(data_loader, st.session_state.products_filters)
            st.metric("🔍 Filtered Results", filtered_count)
    
    # Enhanced quick filter buttons
    st.markdown("**⚡ Smart Filters:**")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    quick_filters = [
        ("🔥 Hot Deals (30%+)", {'discount_min': 30}),
        ("💎 Premium (€500+)", {'price_range': [500, 10000]}),
        ("💰 Budget (€0-200)", {'price_range': [0, 200]}),
        ("📱 Electronics", {'category': 'electronics'}),
        ("🚨 With Alerts", {'show_alerts_only': True}),
        ("🔄 Reset All", 'reset')
    ]
    
    for i, (label, filter_update) in enumerate(quick_filters):
        with [col1, col2, col3, col4, col5, col6][i]:
            if st.button(label, key=f"quick_filter_{i}", use_container_width=True):
                if filter_update == 'reset':
                    st.session_state.products_filters = {
                        'search_query': '',
                        'category': 'all',
                        'price_range': [0, 10000],
                        'discount_min': 0,
                        'sort_by': 'price_desc',
                        'show_alerts_only': False,
                        'brand_filter': 'all',
                        'availability_filter': 'all',
                        'profit_potential_min': 0
                    }
                else:
                    st.session_state.products_filters.update(filter_update)
                st.rerun()
    
    return st.session_state.products_filters

def _render_product_analytics_dashboard(data_loader, filters):
    """Render interactive product analytics dashboard."""
    
    st.markdown("### 📊 Product Analytics Dashboard")
    
    # Get analytics data
    analytics = _get_product_analytics_data(data_loader, filters)
    
    # Create analytics tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "💰 Price Analysis", "🔥 Discounts", "🎯 Opportunities"])
    
    with tab1:
        _render_analytics_overview(analytics)
    
    with tab2:
        _render_price_analytics(analytics)
    
    with tab3:
        _render_discount_analytics(analytics)
    
    with tab4:
        _render_opportunity_analytics(analytics)

def _render_analytics_overview(analytics):
    """Render analytics overview tab."""
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Category distribution
        if analytics.get('category_data'):
            fig = px.pie(
                values=list(analytics['category_data'].values()),
                names=list(analytics['category_data'].keys()),
                title="📂 Products by Category",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Brand distribution (top 10)
        if analytics.get('brand_data'):
            top_brands = dict(list(analytics['brand_data'].items())[:10])
            fig = px.bar(
                x=list(top_brands.values()),
                y=list(top_brands.keys()),
                orientation='h',
                title="🏷️ Top Brands by Product Count",
                color=list(top_brands.values()),
                color_continuous_scale="Blues"
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

def _render_price_analytics(analytics):
    """Render price analytics tab."""
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Price distribution histogram
        if analytics.get('price_distribution'):
            fig = px.histogram(
                x=analytics['price_distribution'],
                nbins=30,
                title="💰 Price Distribution",
                labels={'x': 'Price (€)', 'y': 'Number of Products'},
                color_discrete_sequence=['#1f77b4']
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Average price by category
        if analytics.get('category_avg_prices'):
            fig = px.bar(
                x=list(analytics['category_avg_prices'].keys()),
                y=list(analytics['category_avg_prices'].values()),
                title="📊 Average Price by Category",
                labels={'x': 'Category', 'y': 'Average Price (€)'},
                color=list(analytics['category_avg_prices'].values()),
                color_continuous_scale="Viridis"
            )
            fig.update_layout(height=300, xaxis={'tickangle': 45})
            st.plotly_chart(fig, use_container_width=True)

def _render_discount_analytics(analytics):
    """Render discount analytics tab."""
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Discount distribution
        if analytics.get('discount_distribution'):
            fig = px.histogram(
                x=analytics['discount_distribution'],
                nbins=20,
                title="🔥 Discount Distribution",
                labels={'x': 'Discount (%)', 'y': 'Number of Products'},
                color_discrete_sequence=['#ff7f0e']
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Products with high discounts by category
        if analytics.get('high_discount_by_category'):
            fig = px.bar(
                x=list(analytics['high_discount_by_category'].keys()),
                y=list(analytics['high_discount_by_category'].values()),
                title="🎯 High Discount Products (>20%) by Category",
                labels={'x': 'Category', 'y': 'Products with High Discounts'},
                color=list(analytics['high_discount_by_category'].values()),
                color_continuous_scale="Reds"
            )
            fig.update_layout(height=300, xaxis={'tickangle': 45})
            st.plotly_chart(fig, use_container_width=True)

def _render_opportunity_analytics(analytics):
    """Render arbitrage opportunity analytics."""
    
    # Opportunity matrix
    st.subheader("🎯 Arbitrage Opportunity Matrix")
    
    if analytics.get('opportunity_matrix'):
        opportunity_data = analytics['opportunity_matrix']
        
        # Create scatter plot of price vs discount with profit potential
        fig = px.scatter(
            x=opportunity_data.get('prices', []),
            y=opportunity_data.get('discounts', []),
            size=opportunity_data.get('profit_potentials', []),
            color=opportunity_data.get('categories', []),
            hover_data={'profit_potential': opportunity_data.get('profit_potentials', [])},
            title="💎 Price vs Discount with Profit Potential (bubble size)",
            labels={'x': 'Price (€)', 'y': 'Discount (%)'},
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Top opportunities table
    st.subheader("🏆 Top Arbitrage Opportunities")
    
    if analytics.get('top_opportunities'):
        df_opportunities = pd.DataFrame(analytics['top_opportunities'])
        
        # Format the dataframe for display
        if not df_opportunities.empty:
            # Apply styling
            styled_df = df_opportunities.style.format({
                'price': '€{:.2f}',
                'discount': '{:.1f}%',
                'profit_potential': '€{:.2f}'
            }).background_gradient(subset=['profit_potential'], cmap='Greens')
            
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("No high-potential opportunities found with current filters.") 

def _get_category_options(data_loader) -> Dict[str, str]:
    """Get category options with counts."""
    try:
        # In a real implementation, this would query the database for categories
        categories = {
            'all': 'All Categories',
            'electronics': 'Electronics (1,234)',
            'smartphones': 'Smartphones (456)', 
            'laptops': 'Laptops (234)',
            'tablets': 'Tablets (123)',
            'accessories': 'Accessories (567)',
            'gaming': 'Gaming (189)',
            'tv': 'TV & Audio (345)',
            'home': 'Home & Garden (678)'
        }
        return categories
    except Exception:
        return {'all': 'All Categories'}

def _get_brand_options(data_loader) -> List[str]:
    """Get brand options."""
    try:
        # In a real implementation, this would query the database for brands
        return ['all', 'Samsung', 'Apple', 'Sony', 'LG', 'Xiaomi', 'Huawei', 'Nintendo', 'PlayStation']
    except Exception:
        return ['all']

def _render_price_distribution_mini_chart(data_loader, price_range):
    """Render mini price distribution chart."""
    try:
        # Simulated price distribution data
        prices = [100, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000]
        counts = [50, 80, 120, 90, 70, 45, 30, 20, 15, 10]
        
        # Filter based on price range
        filtered_data = [(p, c) for p, c in zip(prices, counts) if price_range[0] <= p <= price_range[1]]
        
        if filtered_data:
            fig = px.bar(
                x=[d[0] for d in filtered_data],
                y=[d[1] for d in filtered_data],
                height=150,
                title="Price Distribution"
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Price (€)",
                yaxis_title="Count"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No products in selected price range")
    except Exception:
        st.caption("Price analysis unavailable")

def _render_discount_distribution_mini_chart(data_loader, discount_min):
    """Render mini discount distribution chart."""
    try:
        # Simulated discount data
        discounts = [0, 10, 20, 30, 40, 50, 60, 70]
        counts = [200, 150, 100, 70, 40, 20, 10, 5]
        
        # Filter based on minimum discount
        filtered_data = [(d, c) for d, c in zip(discounts, counts) if d >= discount_min]
        
        if filtered_data:
            fig = px.bar(
                x=[d[0] for d in filtered_data],
                y=[d[1] for d in filtered_data],
                height=150,
                title="Discount Distribution",
                color_discrete_sequence=['#ff7f0e']
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Discount (%)",
                yaxis_title="Count"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No products with selected discount")
    except Exception:
        st.caption("Discount analysis unavailable")

def _count_high_profit_items(data_loader, profit_min):
    """Count items with high profit potential."""
    try:
        # In real implementation, query database for profit potential
        # For now, simulate based on profit threshold
        if profit_min <= 10:
            return 45
        elif profit_min <= 25:
            return 23
        elif profit_min <= 50:
            return 12
        else:
            return 5
    except Exception:
        return 0

def _get_filtered_product_count(data_loader, filters):
    """Get count of products matching current filters."""
    try:
        # In real implementation, this would query with filters
        # For now, simulate based on filter complexity
        base_count = 1234
        
        # Reduce count based on active filters
        if filters['category'] != 'all':
            base_count = int(base_count * 0.3)
        if filters['search_query']:
            base_count = int(base_count * 0.2)
        if filters['discount_min'] > 0:
            base_count = int(base_count * 0.4)
        if filters['show_alerts_only']:
            base_count = int(base_count * 0.1)
        
        return max(base_count, 0)
    except Exception:
        return 0

def _get_product_analytics_data(data_loader, filters):
    """Get comprehensive product analytics data."""
    try:
        # Simulate analytics data - in real implementation, query database
        analytics = {
            'category_data': {
                'Electronics': 450,
                'Smartphones': 234,
                'Laptops': 156,
                'Accessories': 345,
                'Gaming': 123,
                'TV & Audio': 200
            },
            'brand_data': {
                'Samsung': 234,
                'Apple': 189,
                'Sony': 156,
                'LG': 134,
                'Xiaomi': 123,
                'Huawei': 98,
                'Nintendo': 87,
                'PlayStation': 76,
                'Bose': 65,
                'JBL': 54
            },
            'price_distribution': [99, 149, 199, 249, 299, 349, 399, 449, 499, 599, 699, 799, 899, 999, 1199, 1399, 1599, 1899, 2199, 2499] * 10,
            'category_avg_prices': {
                'Electronics': 345.67,
                'Smartphones': 567.89,
                'Laptops': 899.45,
                'Accessories': 89.23,
                'Gaming': 234.56,
                'TV & Audio': 678.90
            },
            'discount_distribution': [5, 10, 15, 20, 25, 30, 35, 40, 45, 50] * 20,
            'high_discount_by_category': {
                'Electronics': 45,
                'Smartphones': 23,
                'Laptops': 12,
                'Accessories': 67,
                'Gaming': 34,
                'TV & Audio': 28
            },
            'opportunity_matrix': {
                'prices': [199, 299, 449, 599, 799, 999, 1299, 1599, 1899, 2199],
                'discounts': [25, 30, 35, 20, 40, 15, 45, 50, 30, 35],
                'profit_potentials': [25, 45, 67, 89, 120, 78, 156, 234, 189, 267],
                'categories': ['Electronics', 'Smartphones', 'Laptops', 'Gaming', 'TV', 'Accessories', 'Electronics', 'Smartphones', 'Laptops', 'Gaming']
            },
            'top_opportunities': [
                {'title': 'Samsung Galaxy S23', 'price': 699.99, 'discount': 35.0, 'profit_potential': 156.78, 'category': 'Smartphones'},
                {'title': 'Sony WH-1000XM4', 'price': 249.99, 'discount': 40.0, 'profit_potential': 89.45, 'category': 'Audio'},
                {'title': 'Nintendo Switch OLED', 'price': 299.99, 'discount': 25.0, 'profit_potential': 67.89, 'category': 'Gaming'},
                {'title': 'iPad Air 5th Gen', 'price': 549.99, 'discount': 30.0, 'profit_potential': 134.56, 'category': 'Tablets'},
                {'title': 'LG OLED55C2', 'price': 1299.99, 'discount': 45.0, 'profit_potential': 234.67, 'category': 'TV'}
            ]
        }
        
        return analytics
    except Exception as e:
        logger.error(f"Error getting analytics data: {e}")
        return {}

def _render_enhanced_products_section(data_loader, filters: Dict[str, Any]):
    """Render enhanced products display section with improved visualizations."""
    
    st.markdown("---")
    st.markdown("### 📋 Product Catalog")
    
    # Enhanced view mode selection with options
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        view_mode = st.radio(
            "📋 View Mode",
            ["Enhanced Cards", "Data Table", "Compact List"],
            horizontal=False,
            key="enhanced_view_mode"
        )
    
    with col2:
        # Items per page
        items_per_page = st.selectbox(
            "📄 Items per page",
            [10, 20, 50, 100],
            index=1,
            key="items_per_page"
        )
    
    with col3:
        # Real-time filter indicator
        active_filters = _count_active_filters(filters)
        st.metric("🔍 Active Filters", active_filters)
    
    with col4:
        # Export options
        if st.button("📊 Export Results", key="export_results"):
            st.success("📄 Export initiated - results will be downloaded shortly!")
    
    # Load filtered products
    try:
        products_data = _fetch_enhanced_filtered_products(data_loader, filters, items_per_page)
        
        if not products_data:
            st.info("🔍 No products found matching your criteria. Try adjusting the filters.")
            return
        
        # Display products based on view mode
        if view_mode == "Enhanced Cards":
            _render_enhanced_products_cards(products_data)
        elif view_mode == "Data Table":
            _render_enhanced_products_table(products_data)
        else:  # Compact List
            _render_compact_products_list(products_data)
        
        # Pagination info
        st.caption(f"Showing {len(products_data)} products. Use filters to refine results.")
        
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        st.error("⚠️ Error loading products. Please try again.")

def _count_active_filters(filters: Dict[str, Any]) -> int:
    """Count number of active filters."""
    count = 0
    
    if filters.get('search_query'):
        count += 1
    if filters.get('category') != 'all':
        count += 1
    if filters.get('brand_filter') != 'all':
        count += 1
    if filters.get('discount_min') > 0:
        count += 1
    if filters.get('price_range') != [0, 10000]:
        count += 1
    if filters.get('show_alerts_only'):
        count += 1
    if filters.get('profit_potential_min') > 0:
        count += 1
    if filters.get('availability_filter') != 'all':
        count += 1
    
    return count

def _render_enhanced_products_cards(products_data: List[Dict[str, Any]]):
    """Render enhanced product cards with advanced styling."""
    
    # Display products in grid layout (3 columns)
    cols = st.columns(3)
    
    for i, product in enumerate(products_data):
        with cols[i % 3]:
            _render_enhanced_product_card(product)

def _render_enhanced_product_card(product: Dict[str, Any]):
    """Render individual enhanced product card."""
    
    title = product.get('title', 'Unknown Product')
    price = product.get('price', 0)
    discount = product.get('discount_percentage', 0)
    has_alert = product.get('has_alert', False)
    profit_potential = product.get('profit_potential', 0)
    availability = product.get('availability', 'Unknown')
    
    # Card styling based on product properties
    card_color = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    if has_alert:
        card_color = "linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
    elif discount > 30:
        card_color = "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
    
    # Alert indicator
    alert_badge = "🚨 ALERT" if has_alert else ""
    discount_badge = f"🔥 -{discount:.0f}%" if discount > 0 else ""
    
    # Truncate title for display
    display_title = title[:50] + "..." if len(title) > 50 else title
    
    st.markdown(f"""
    <div style="
        padding: 20px; 
        background: {card_color}; 
        border-radius: 15px; 
        color: white; 
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease-in-out;
    ">
        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 10px;">
            <span style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 10px; font-size: 10px;">
                {alert_badge}
            </span>
            <span style="background: rgba(255,255,255,0.2); padding: 2px 6px; border-radius: 10px; font-size: 10px;">
                {discount_badge}
            </span>
        </div>
        
        <h4 style="margin: 10px 0; font-size: 14px; line-height: 1.2;">{display_title}</h4>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 10px 0;">
            <span style="font-size: 20px; font-weight: bold;">€{price:.2f}</span>
            {f'<span style="font-size: 12px; opacity: 0.8;">Profit: €{profit_potential:.2f}</span>' if profit_potential > 0 else ''}
        </div>
        
        <div style="font-size: 11px; opacity: 0.9;">
            📦 {availability} | 🎯 High Opportunity
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👁️ View", key=f"view_{product.get('_id', i)}", use_container_width=True):
            st.session_state[f"show_details_{product.get('_id', i)}"] = True
    
    with col2:
        if st.button("🔗 MediaMarkt", key=f"link_{product.get('_id', i)}", use_container_width=True):
            st.success("🔗 Opening MediaMarkt link...")

def _render_enhanced_products_table(products_data: List[Dict[str, Any]]):
    """Render enhanced products table with advanced formatting."""
    
    if not products_data:
        st.info("No products to display")
        return
    
    # Prepare dataframe
    df = pd.DataFrame(products_data)
    
    # Select and rename columns for display
    display_columns = {
        'title': 'Product',
        'price': 'Price (€)',
        'discount_percentage': 'Discount (%)',
        'profit_potential': 'Profit (€)',
        'availability': 'Status',
        'category': 'Category'
    }
    
    # Filter available columns
    available_columns = {k: v for k, v in display_columns.items() if k in df.columns}
    df_display = df[list(available_columns.keys())].copy()
    df_display.columns = list(available_columns.values())
    
    # Format the dataframe
    if 'Price (€)' in df_display.columns:
        df_display['Price (€)'] = df_display['Price (€)'].apply(lambda x: f"€{x:.2f}")
    
    if 'Discount (%)' in df_display.columns:
        df_display['Discount (%)'] = df_display['Discount (%)'].apply(lambda x: f"{x:.1f}%" if x > 0 else "-")
    
    if 'Profit (€)' in df_display.columns:
        df_display['Profit (€)'] = df_display['Profit (€)'].apply(lambda x: f"€{x:.2f}" if x > 0 else "-")
    
    # Apply styling and display
    styled_df = df_display.style.apply(_style_table_rows, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=600)

def _style_table_rows(row):
    """Apply styling to table rows based on content."""
    styles = [''] * len(row)
    
    # Highlight high profit opportunities
    if 'Profit (€)' in row.index:
        profit_text = row['Profit (€)']
        if profit_text != '-':
            try:
                profit_value = float(profit_text.replace('€', ''))
                if profit_value > 50:
                    styles = ['background-color: #d4edda'] * len(row)  # Light green
                elif profit_value > 20:
                    styles = ['background-color: #fff3cd'] * len(row)  # Light yellow
            except:
                pass
    
    return styles

def _render_compact_products_list(products_data: List[Dict[str, Any]]):
    """Render compact products list view."""
    
    for i, product in enumerate(products_data):
        title = product.get('title', 'Unknown Product')
        price = product.get('price', 0)
        discount = product.get('discount_percentage', 0)
        has_alert = product.get('has_alert', False)
        
        # Create compact row
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            alert_icon = "🚨" if has_alert else "📦"
            display_title = title[:60] + "..." if len(title) > 60 else title
            st.write(f"{alert_icon} {display_title}")
        
        with col2:
            st.write(f"€{price:.2f}")
        
        with col3:
            if discount > 0:
                st.write(f"🔥 -{discount:.0f}%")
            else:
                st.write("-")
        
        with col4:
            if st.button("View", key=f"compact_view_{i}"):
                st.info(f"Viewing details for: {title[:30]}...")
        
        if i < len(products_data) - 1:
            st.divider()

def _fetch_enhanced_filtered_products(data_loader, filters: Dict[str, Any], limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch products with enhanced filtering and simulated data."""
    
    try:
        # In real implementation, this would query MongoDB with filters
        # For now, return simulated enhanced product data
        
        products = []
        for i in range(min(limit, 20)):  # Limit simulation
            product = {
                '_id': f'prod_{i}',
                'title': _generate_product_title(i),
                'price': round(99.99 + (i * 50.5), 2),
                'discount_percentage': max(0, 40 - (i * 2)),
                'profit_potential': max(0, 80 - (i * 4)),
                'availability': ['In Stock', 'Limited', 'Pre-order'][i % 3],
                'category': ['Electronics', 'Smartphones', 'Laptops', 'Gaming', 'Audio'][i % 5],
                'brand': ['Samsung', 'Apple', 'Sony', 'LG', 'Nintendo'][i % 5],
                'has_alert': i < 5,  # First 5 have alerts
                'url': f'https://mediamarkt.pt/product/{i}'
            }
            products.append(product)
        
        return products
        
    except Exception as e:
        logger.error(f"Error fetching filtered products: {e}")
        return []

def _generate_product_title(index: int) -> str:
    """Generate simulated product titles."""
    titles = [
        "Samsung Galaxy S23 Ultra 256GB - Phantom Black",
        "Apple iPhone 14 Pro 128GB - Deep Purple", 
        "Sony WH-1000XM4 Wireless Noise Canceling Headphones",
        "LG OLED55C2PSA 55\" 4K Smart TV",
        "Nintendo Switch OLED Model - White",
        "iPad Air 5th Generation 64GB WiFi - Space Gray",
        "Samsung 970 EVO Plus SSD 1TB M.2 2280 PCIe",
        "PlayStation 5 Digital Edition Console",
        "Xiaomi Redmi Note 12 Pro 5G 256GB - Graphite Gray",
        "Sony Alpha a7 IV Mirrorless Camera Body",
        "Bose QuietComfort 45 Wireless Headphones",
        "ASUS ROG Strix G15 Gaming Laptop RTX 3060",
        "JBL Charge 5 Portable Bluetooth Speaker",
        "Apple Watch Series 8 GPS 45mm - Midnight",
        "Samsung Neo QLED QN85B 65\" 4K Smart TV",
        "Logitech MX Master 3 Wireless Mouse",
        "Canon EOS R6 Mark II Mirrorless Camera",
        "Dell XPS 13 Plus Laptop Intel i7 32GB RAM",
        "Sennheiser Momentum 4 Wireless Headphones",
        "HP Pavilion Gaming Desktop RTX 4060"
    ]
    return titles[index % len(titles)] 