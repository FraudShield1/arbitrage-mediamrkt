"""
Analytics Dashboard Component

Comprehensive analytics dashboard for tracking arbitrage performance,
trends, and insights with interactive charts and metrics.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from src.dashboard.utils.mongodb_loader import get_mongodb_loader
from src.dashboard.utils.charts import ChartGenerator

logger = logging.getLogger(__name__)


class AnalyticsDashboard:
    """Main analytics dashboard component."""
    
    def __init__(self, data_loader=None):
        """Initialize analytics dashboard."""
        self.data_loader = data_loader or get_mongodb_loader()
        self.chart_generator = ChartGenerator()
        
    def render(self):
        """Render the complete analytics dashboard."""
        st.title("📊 Analytics Dashboard")
        st.markdown("Comprehensive analysis of arbitrage opportunities and performance")
        
        # Time range selector
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_date = st.date_input(
                "Start Date",
                datetime.now() - timedelta(days=30),
                key="analytics_start_date"
            )
        with col2:
            end_date = st.date_input(
                "End Date", 
                datetime.now(),
                key="analytics_end_date"
            )
        with col3:
            if st.button("🔄 Refresh Data", key="refresh_analytics"):
                st.cache_data.clear()
                st.rerun()
        
        # Load analytics data
        analytics_data = self._load_analytics_data(start_date, end_date)
        
        if not analytics_data:
            st.warning("No data available for the selected time range.")
            return
        
        # Main dashboard tabs
        tabs = st.tabs([
            "📈 Overview", 
            "💰 Profit Analysis", 
            "📊 Trends", 
            "🏷️ Categories",
            "🌍 Geographic", 
            "🔍 Competitive Analysis"
        ])
        
        with tabs[0]:
            self._render_overview(analytics_data)
        
        with tabs[1]:
            self._render_profit_analysis(analytics_data)
        
        with tabs[2]:
            self._render_trends_analysis(analytics_data)
        
        with tabs[3]:
            self._render_category_analysis(analytics_data)
        
        with tabs[4]:
            self._render_geographic_analysis(analytics_data)
        
        with tabs[5]:
            self._render_competitive_analysis(analytics_data)
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def _load_analytics_data(self, start_date, end_date) -> Dict[str, Any]:
        """Load and cache analytics data."""
        try:
            # Call the synchronous method directly - no asyncio needed
            return self.data_loader.get_analytics_data(start_date, end_date)
        except Exception as e:
            st.error(f"Error loading analytics data: {str(e)}")
            logger.error(f"Analytics data loading error: {str(e)}", exc_info=True)
            return {}
    
    def _render_overview(self, data: Dict[str, Any]):
        """Render overview metrics section."""
        st.subheader("📋 Key Performance Indicators")
        
        # KPI Metrics
        metrics = data.get('overview', {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "Total Products",
                f"{metrics.get('total_products', 0):,}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Total Alerts",
                f"{metrics.get('total_alerts', 0):,}",
                delta=None
            )
        
        with col3:
            st.metric(
                "Total Savings",
                f"€{metrics.get('total_savings', 0):,.2f}",
                delta=None
            )
        
        with col4:
            st.metric(
                "Avg Discount",
                f"{metrics.get('avg_discount', 0):.1f}%",
                delta=None
            )
        
        # Recent activity overview
        st.subheader("📈 Recent Activity")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Category performance chart
            category_data = data.get('category_performance', [])
            if category_data:
                try:
                    fig = self.chart_generator.create_category_profit_chart(category_data)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info("Category performance chart unavailable")
            else:
                st.info("No category data available")
        
        with col2:
            # Price analytics
            price_data = data.get('price_analytics', {})
            if price_data:
                st.subheader("💰 Price Analytics")
                st.metric("Average Price", f"€{price_data.get('avg_price', 0):.2f}")
                st.metric("Price Range", f"€{price_data.get('min_price', 0):.2f} - €{price_data.get('max_price', 0):.2f}")
            else:
                st.info("No price data available")
    
    def _render_profit_analysis(self, data: Dict[str, Any]):
        """Render profit analysis section."""
        st.subheader("💰 Profit Analysis")
        
        # Overview metrics
        overview = data.get('overview', {})
        if overview:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Savings", f"€{overview.get('total_savings', 0):,.2f}")
            with col2:
                st.metric("Average Savings", f"€{overview.get('avg_savings', 0):.2f}")
            with col3:
                st.metric("Categories", overview.get('categories_count', 0))
        
        # Category performance
        st.subheader("📊 Category Performance")
        category_performance = data.get('category_performance', [])
        if category_performance:
            try:
                fig = self.chart_generator.create_category_profit_chart(category_performance)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display as table too
                df = pd.DataFrame(category_performance)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.info("Category performance visualization unavailable")
                # Show raw data as fallback
                df = pd.DataFrame(category_performance)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
        else:
            st.info("No category performance data available")
    
    def _render_trends_analysis(self, data: Dict[str, Any]):
        """Render trends analysis section."""
        st.subheader("📊 Trend Analysis")
        
        # Show overview data as trends
        overview = data.get('overview', {})
        if overview:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 System Metrics")
                st.metric("Total Products", f"{overview.get('total_products', 0):,}")
                st.metric("Total Alerts", f"{overview.get('total_alerts', 0):,}")
                
            with col2:
                st.subheader("💰 Profit Metrics")
                st.metric("Total Savings", f"€{overview.get('total_savings', 0):,.2f}")
                st.metric("Average Savings", f"€{overview.get('avg_savings', 0):.2f}")
        
        # Discount analytics
        discount_data = data.get('discount_analytics', {})
        if discount_data:
            st.subheader("🏷️ Discount Analysis")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Average Discount", f"{discount_data.get('avg_discount', 0):.1f}%")
            with col2:
                st.metric("Maximum Discount", f"{discount_data.get('max_discount', 0):.1f}%")
        
        # Note about limited data
        st.info("📊 Detailed trend analysis requires more historical data. Current view shows latest available metrics.")
    
    def _render_category_analysis(self, data: Dict[str, Any]):
        """Render category analysis section."""
        st.subheader("🏷️ Category Performance")
        
        category_performance = data.get('category_performance', [])
        if category_performance:
            # Display category metrics
            df = pd.DataFrame(category_performance)
            
            if not df.empty:
                # Format the dataframe for better display
                display_df = df.copy()
                
                # Format currency columns
                for col in ['total_savings', 'avg_savings']:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"€{x:.2f}")
                
                # Format percentage columns
                for col in ['avg_discount']:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(display_df, use_container_width=True)
                
                # Try to create a chart
                try:
                    fig = self.chart_generator.create_category_profit_chart(category_performance)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.info("Category chart visualization unavailable")
            else:
                st.info("No category data to display")
        else:
            st.info("No category performance data available")
    
    def _render_geographic_analysis(self, data: Dict[str, Any]):
        """Render geographic analysis section."""
        st.subheader("🌍 Geographic Analysis")
        
        # For now, show a placeholder since we don't have geographic data
        st.info("🗺️ Geographic analysis feature coming soon!")
        st.markdown("""
        **Planned Features:**
        - Regional price comparisons
        - Market penetration by country
        - Shipping cost analysis
        - Currency impact assessment
        """)
    
    def _render_competitive_analysis(self, data: Dict[str, Any]):
        """Render competitive analysis section."""
        st.subheader("🔍 Competitive Analysis")
        
        # Show available data
        overview = data.get('overview', {})
        if overview:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Market Overview")
                st.metric("Total Opportunities", f"{overview.get('total_alerts', 0):,}")
                st.metric("Categories Analyzed", overview.get('categories_count', 0))
                
            with col2:
                st.subheader("💡 Key Insights")
                avg_savings = overview.get('avg_savings', 0)
                if avg_savings > 50:
                    st.success(f"High average savings: €{avg_savings:.2f}")
                elif avg_savings > 20:
                    st.info(f"Moderate average savings: €{avg_savings:.2f}")
                else:
                    st.warning(f"Low average savings: €{avg_savings:.2f}")
                
                total_savings = overview.get('total_savings', 0)
                if total_savings > 1000:
                    st.success(f"Strong profit potential: €{total_savings:,.2f}")
                else:
                    st.info(f"Profit potential: €{total_savings:,.2f}")
        
        st.info("🔍 Advanced competitive analysis features coming soon!")
        st.markdown("""
        **Planned Features:**
        - Competitor price tracking
        - Market share analysis
        - Price volatility indicators
        - Opportunity scoring system
        """)


def render_analytics(data_loader=None):
    """Render analytics dashboard with shared data loader.
    
    Args:
        data_loader: Shared MongoDB data loader instance
    """
    dashboard = AnalyticsDashboard(data_loader)
    dashboard.render()


# Export main function
__all__ = ['AnalyticsDashboard', 'render_analytics'] 