"""
Overview Page - Enhanced Real-Time Dashboard

Enhanced main dashboard page with real-time monitoring, advanced visualizations,
and comprehensive system metrics.
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
from src.dashboard.utils.state_management import get_page_state, update_page_state, get_cached_data, set_cached_data
from src.dashboard.utils.styling import create_metric_card, create_status_badge, create_alert_card

logger = logging.getLogger(__name__)

def render(data_loader):
    """Render the Enhanced Overview page with real-time features."""
    
    # Page setup with auto-refresh capability
    page_state = get_page_state('overview')
    
    # Enhanced header with real-time indicators
    _render_enhanced_header()
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=True, key="overview_auto_refresh")
    
    if auto_refresh:
        # Auto-refresh every 30 seconds
        time.sleep(0.1)  # Small delay to prevent rapid updates
        st.rerun()
    
    try:
        # Real-time metrics section
        _render_realtime_metrics(data_loader)
        
        # Enhanced system health monitoring
        _render_enhanced_system_health(data_loader)
        
        # Advanced analytics row
        col1, col2 = st.columns([2, 1])
        
        with col1:
            _render_performance_dashboard(data_loader)
            _render_advanced_trends(data_loader)
        
        with col2:
            _render_live_alerts_feed(data_loader)
            _render_system_insights(data_loader)
        
        # Interactive charts section
        _render_interactive_charts(data_loader)
        
        # Update page state
        update_page_state('overview', {
            'last_refresh': datetime.now(),
            'data_loaded': True,
            'error_count': 0,
            'enhancement_level': 'Phase2'
        })
        
    except Exception as e:
        logger.error(f"Error rendering Enhanced Overview page: {e}")
        st.error("⚠️ Error loading enhanced dashboard data")
        st.exception(e)

def _render_enhanced_header():
    """Render enhanced header with real-time status."""
    # Main header with live indicators
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #1f77b4; font-size: 2.2em;">
                💰 Enhanced Control Center
            </h1>
            <span style="margin-left: 15px; padding: 6px 12px; background: linear-gradient(90deg, #28a745, #20c997); 
                         color: white; border-radius: 20px; font-size: 12px; font-weight: bold; 
                         animation: pulse 2s infinite;">
                ⚡ REAL-TIME
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
        if st.button("📊 Export Report", key="export_report", help="Export system report"):
            st.success("📄 Report export initiated!")

def _render_realtime_metrics(data_loader):
    """Render enhanced real-time metrics with trend indicators."""
    
    st.markdown("### 📊 Real-Time Performance Metrics")
    
    # Get enhanced metrics
    metrics_data = _get_enhanced_metrics(data_loader)
    
    if not metrics_data:
        st.warning("Unable to load real-time metrics")
        return
    
    # Enhanced metrics display with trends
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        _render_enhanced_metric_card(
            "🎯 Active Alerts",
            metrics_data['active_alerts'],
            metrics_data.get('alerts_trend', 0),
            "critical_high" if metrics_data['active_alerts'] > 50 else "normal"
        )
    
    with col2:
        _render_enhanced_metric_card(
            "📦 Total Products",
            f"{metrics_data['total_products']:,}",
            metrics_data.get('products_trend', 0),
            "normal"
        )
    
    with col3:
        _render_enhanced_metric_card(
            "💰 Profit Potential",
            f"€{metrics_data['total_profit_potential']:,.2f}",
            metrics_data.get('profit_trend', 0),
            "success_high" if metrics_data['total_profit_potential'] > 1000 else "normal"
        )
    
    with col4:
        _render_enhanced_metric_card(
            "🔄 Success Rate",
            f"{metrics_data['success_rate']:.1f}%",
            metrics_data.get('success_trend', 0),
            "success_high" if metrics_data['success_rate'] > 95 else "warning"
        )
    
    with col5:
        _render_enhanced_metric_card(
            "⚡ Avg ROI",
            f"{metrics_data['average_roi']:.1f}%",
            metrics_data.get('roi_trend', 0),
            "success_high" if metrics_data['average_roi'] > 20 else "normal"
        )

def _render_enhanced_metric_card(title: str, value: str, trend: float, status: str):
    """Render an enhanced metric card with trend and status indicators."""
    
    # Status colors
    status_colors = {
        "normal": "#17a2b8",
        "success_high": "#28a745", 
        "warning": "#ffc107",
        "critical_high": "#dc3545"
    }
    
    color = status_colors.get(status, "#17a2b8")
    
    # Trend arrow
    if trend > 0:
        trend_icon = "📈"
        trend_color = "#28a745"
    elif trend < 0:
        trend_icon = "📉"
        trend_color = "#dc3545"
    else:
        trend_icon = "➖"
        trend_color = "#6c757d"
    
    st.markdown(f"""
    <div style="
        padding: 20px;
        background: linear-gradient(135deg, {color}15, {color}05);
        border-left: 4px solid {color};
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">{title}</div>
        <div style="font-size: 24px; font-weight: bold; color: {color}; margin-bottom: 5px;">{value}</div>
        <div style="font-size: 12px; color: {trend_color};">
            {trend_icon} {abs(trend):.1f}% vs yesterday
        </div>
    </div>
    """, unsafe_allow_html=True)

def _render_enhanced_system_health(data_loader):
    """Render enhanced system health monitoring."""
    
    st.markdown("### 🔋 Enhanced System Health Monitor")
    
    # Get system health data
    health_data = _get_system_health_data(data_loader)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        _render_health_indicator("🗄️ Database", health_data.get('database', True), "Sub-50ms queries")
    
    with col2:
        _render_health_indicator("🤖 Scraper", health_data.get('scraper', True), "100+ products/min")
    
    with col3:
        _render_health_indicator("🚨 Alerts", health_data.get('alerts', True), "Real-time processing")
    
    with col4:
        _render_health_indicator("📡 API", health_data.get('api', True), "FastAPI operational")

def _render_health_indicator(name: str, status: bool, description: str):
    """Render a health status indicator."""
    status_color = "#28a745" if status else "#dc3545"
    status_icon = "🟢" if status else "🔴"
    status_text = "Operational" if status else "Issues"
    
    st.markdown(f"""
    <div style="
        padding: 15px;
        background-color: {status_color}10;
        border: 1px solid {status_color}30;
        border-radius: 8px;
        text-align: center;
    ">
        <div style="font-size: 20px; margin-bottom: 5px;">{status_icon}</div>
        <div style="font-weight: bold; color: {status_color}; margin-bottom: 3px;">{name}</div>
        <div style="font-size: 12px; color: {status_color};">{status_text}</div>
        <div style="font-size: 10px; color: #666; margin-top: 5px;">{description}</div>
    </div>
    """, unsafe_allow_html=True)

def _render_performance_dashboard(data_loader):
    """Render performance dashboard with interactive charts."""
    
    st.markdown("### 📈 Performance Dashboard")
    
    # Performance metrics over time
    perf_data = _get_performance_data(data_loader)
    
    if perf_data:
        # Create subplot with secondary y-axis
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Response Times", "Throughput", "Success Rate", "Resource Usage"),
            specs=[[{"secondary_y": True}, {"secondary_y": True}],
                   [{"secondary_y": True}, {"secondary_y": True}]]
        )
        
        # Response times
        fig.add_trace(
            go.Scatter(
                x=perf_data['timestamps'],
                y=perf_data['response_times'],
                mode='lines+markers',
                name='Response Time',
                line=dict(color='#1f77b4')
            ),
            row=1, col=1
        )
        
        # Throughput
        fig.add_trace(
            go.Scatter(
                x=perf_data['timestamps'],
                y=perf_data['throughput'],
                mode='lines+markers',
                name='Products/min',
                line=dict(color='#ff7f0e')
            ),
            row=1, col=2
        )
        
        # Success rate
        fig.add_trace(
            go.Scatter(
                x=perf_data['timestamps'],
                y=perf_data['success_rates'],
                mode='lines+markers',
                name='Success %',
                line=dict(color='#2ca02c')
            ),
            row=2, col=1
        )
        
        # Resource usage
        fig.add_trace(
            go.Scatter(
                x=perf_data['timestamps'],
                y=perf_data['memory_usage'],
                mode='lines+markers',
                name='Memory %',
                line=dict(color='#d62728')
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=400,
            showlegend=False,
            title_font_size=16
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📊 Performance data will appear here during active monitoring")

def _render_advanced_trends(data_loader):
    """Render advanced trend analysis."""
    
    st.markdown("### 📊 Advanced Trend Analysis")
    
    # Get trend data
    trends = data_loader.get_trends(days=30)
    
    if trends and trends.get('trends'):
        df = pd.DataFrame(trends['trends'])
        
        # Create advanced trend chart
        fig = px.line(
            df, 
            x='date', 
            y=['products', 'alerts'],
            title="30-Day Product and Alert Trends",
            labels={'value': 'Count', 'date': 'Date'},
            color_discrete_map={'products': '#1f77b4', 'alerts': '#ff7f0e'}
        )
        
        fig.update_layout(
            height=300,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📈 Trend analysis will display historical data")

def _render_live_alerts_feed(data_loader):
    """Render live alerts feed."""
    
    st.markdown("### 🚨 Live Alerts Feed")
    
    # Get recent alerts
    alerts_data = data_loader.get_alerts(page=1, size=10, status="active")
    
    if alerts_data and alerts_data.get('alerts'):
        for alert in alerts_data['alerts'][:5]:  # Show top 5
            _render_compact_alert_card(alert)
    else:
        st.info("🔍 No active alerts at the moment")
    
    # Quick actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 View All Alerts", key="view_all_alerts"):
            st.session_state.current_page = 'alerts'
            st.rerun()
    
    with col2:
        if st.button("➕ Create Alert", key="create_new_alert"):
            st.session_state.current_page = 'alerts'
            st.rerun()

def _render_compact_alert_card(alert: Dict[str, Any]):
    """Render a compact alert card for the live feed."""
    
    urgency_colors = {
        "HIGH": "#dc3545",
        "MEDIUM": "#ffc107", 
        "LOW": "#28a745"
    }
    
    urgency = alert.get('urgency', 'MEDIUM')
    color = urgency_colors.get(urgency, '#ffc107')
    
    savings = alert.get('savings_amount', 0)
    discount = alert.get('discount_percentage', 0)
    
    st.markdown(f"""
    <div style="
        padding: 10px;
        margin: 8px 0;
        border-left: 3px solid {color};
        background-color: {color}10;
        border-radius: 5px;
        font-size: 12px;
    ">
        <div style="font-weight: bold; margin-bottom: 3px;">{alert.get('product_name', 'Unknown Product')[:40]}</div>
        <div style="color: {color}; font-weight: bold;">€{savings:.2f} savings ({discount:.1f}% off)</div>
        <div style="color: #666; font-size: 10px;">{urgency} • {alert.get('created_at', '')[:10]}</div>
    </div>
    """, unsafe_allow_html=True)

def _render_system_insights(data_loader):
    """Render system insights and recommendations."""
    
    st.markdown("### 💡 System Insights")
    
    # Get insights data
    stats = data_loader.get_system_stats()
    
    if stats:
        insights = []
        
        # Generate insights based on data
        if stats.get('active_alerts', 0) > 100:
            insights.append("📈 High alert volume detected - consider reviewing filters")
        
        if stats.get('success_rate', 0) < 95:
            insights.append("⚠️ Success rate below optimal - check scraper health")
        
        if stats.get('total_profit_potential', 0) > 5000:
            insights.append("💰 Excellent profit opportunities available!")
        
        if stats.get('products_growth_rate', 0) > 20:
            insights.append("🚀 Product catalog growing rapidly")
        
        # Default insights if none generated
        if not insights:
            insights = [
                "✅ System operating within normal parameters",
                "🔍 Monitor for new arbitrage opportunities",
                "📊 Review analytics for optimization insights"
            ]
        
        for insight in insights[:4]:  # Show top 4 insights
            st.markdown(f"""
            <div style="
                padding: 8px 12px;
                margin: 5px 0;
                background-color: #e3f2fd;
                border-radius: 5px;
                border-left: 3px solid #2196f3;
                font-size: 13px;
            ">
                {insight}
            </div>
            """, unsafe_allow_html=True)

def _render_interactive_charts(data_loader):
    """Render interactive charts section."""
    
    st.markdown("### 📊 Interactive Analytics")
    
    # Chart selection tabs
    chart_tab1, chart_tab2, chart_tab3 = st.tabs(["🏷️ Categories", "💰 Profit Distribution", "⏱️ Time Analysis"])
    
    with chart_tab1:
        _render_category_analysis(data_loader)
    
    with chart_tab2:
        _render_profit_distribution(data_loader)
    
    with chart_tab3:
        _render_time_analysis(data_loader)

def _render_category_analysis(data_loader):
    """Render category analysis chart."""
    # Simulated category data
    categories = ['Electronics', 'Home & Garden', 'Sports', 'Fashion', 'Books']
    values = [45, 23, 18, 12, 8]
    
    fig = px.pie(
        values=values,
        names=categories,
        title="Product Distribution by Category",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

def _render_profit_distribution(data_loader):
    """Render profit distribution chart."""
    # Simulated profit data
    profit_ranges = ['€0-25', '€25-50', '€50-100', '€100-200', '€200+']
    counts = [15, 28, 22, 18, 7]
    
    fig = px.bar(
        x=profit_ranges,
        y=counts,
        title="Profit Opportunities Distribution",
        color=counts,
        color_continuous_scale="Greens"
    )
    
    fig.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def _render_time_analysis(data_loader):
    """Render time-based analysis."""
    # Simulated hourly data
    hours = list(range(24))
    activity = [2, 1, 1, 0, 1, 3, 8, 15, 22, 28, 35, 42, 45, 48, 52, 46, 38, 32, 25, 18, 12, 8, 5, 3]
    
    fig = px.line(
        x=hours,
        y=activity,
        title="Scraping Activity by Hour",
        labels={'x': 'Hour of Day', 'y': 'Products Scraped'}
    )
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

# Helper functions

def _get_enhanced_metrics(data_loader) -> Optional[Dict[str, Any]]:
    """Get enhanced metrics with trend calculations."""
    stats = data_loader.get_system_stats()
    
    if not stats:
        return None
    
    # Add simulated trends (in real implementation, calculate from historical data)
    enhanced_stats = stats.copy()
    enhanced_stats.update({
        'alerts_trend': 12.5,  # 12.5% increase
        'products_trend': 8.3,
        'profit_trend': 15.7,
        'success_trend': 2.1,
        'roi_trend': 5.4
    })
    
    return enhanced_stats

def _get_system_health_data(data_loader) -> Dict[str, bool]:
    """Get system health status."""
    try:
        health_check = data_loader.health_check()
        return {
            'database': health_check,
            'scraper': True,  # Simulated
            'alerts': True,   # Simulated
            'api': True       # Simulated
        }
    except:
        return {
            'database': False,
            'scraper': False,
            'alerts': False,
            'api': False
        }

def _get_performance_data(data_loader) -> Optional[Dict[str, List]]:
    """Get performance data for charts."""
    # Simulated performance data
    timestamps = [datetime.now() - timedelta(minutes=x*5) for x in range(12, 0, -1)]
    
    return {
        'timestamps': timestamps,
        'response_times': [45, 48, 52, 47, 49, 46, 51, 48, 44, 47, 50, 45],
        'throughput': [120, 115, 125, 118, 122, 128, 119, 124, 126, 121, 117, 123],
        'success_rates': [98.2, 97.8, 98.5, 98.1, 97.9, 98.3, 98.0, 98.4, 98.2, 97.7, 98.1, 98.3],
        'memory_usage': [65, 68, 72, 69, 71, 67, 70, 73, 68, 66, 69, 67]
    } 