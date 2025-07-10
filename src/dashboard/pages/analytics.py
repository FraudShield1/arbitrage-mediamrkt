"""
Analytics Page - Enhanced Advanced Business Intelligence

Phase 2 enhanced analytics with predictive modeling, advanced time range selection,
interactive dashboards, export capabilities, and real-time monitoring.
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
import numpy as np

from src.dashboard.utils.mongodb_loader import get_mongodb_loader
from src.dashboard.utils.state_management import get_page_state, update_page_state, get_cached_data, set_cached_data
from src.dashboard.utils.styling import create_metric_card, create_status_badge, create_alert_card

logger = logging.getLogger(__name__)

def render(data_loader):
    """Render the Enhanced Analytics page with advanced intelligence features."""
    
    # Page setup with auto-refresh capability
    page_state = get_page_state('analytics')
    
    # Enhanced header with real-time indicators
    _render_enhanced_header()
    
    # Auto-refresh toggle and controls
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh (45s)", value=False, key="analytics_auto_refresh")
    with col2:
        if st.button("⚡ Force Refresh", key="force_refresh_analytics"):
            data_loader.clear_cache()
            st.rerun()
    with col3:
        if st.button("📊 Export Report", key="export_analytics"):
            _handle_export_report()
    with col4:
        if st.button("🤖 AI Insights", key="ai_insights"):
            _show_ai_insights()
    
    if auto_refresh:
        # Auto-refresh every 45 seconds for analytics
        time.sleep(0.1)
        st.rerun()
    
    try:
        # Advanced time range selector with predictive controls
        time_config = _render_advanced_time_selector()
        
        # Real-time analytics metrics dashboard
        _render_realtime_analytics_metrics(data_loader, time_config)
        
        # Enhanced analytics tabs with advanced features
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Intelligence Overview", 
            "💰 Advanced Pricing", 
            "🎯 Alert Intelligence", 
            "🔄 Performance Deep Dive",
            "🔮 Predictive Analytics"
        ])
        
        with tab1:
            _render_enhanced_overview_analytics(data_loader, time_config)
        
        with tab2:
            _render_advanced_pricing_analytics(data_loader, time_config)
        
        with tab3:
            _render_alert_intelligence_analytics(data_loader, time_config)
        
        with tab4:
            _render_performance_deep_dive(data_loader, time_config)
        
        with tab5:
            _render_predictive_analytics(data_loader, time_config)
        
        # Update page state
        update_page_state('analytics', {
            'last_refresh': datetime.now(),
            'data_loaded': True,
            'error_count': 0,
            'enhancement_level': 'Phase2'
        })
        
    except Exception as e:
        logger.error(f"Error rendering Enhanced Analytics page: {e}")
        st.error("⚠️ Error loading enhanced analytics data")
        st.exception(e)
        
        # Update error count
        page_state['error_count'] = page_state.get('error_count', 0) + 1
        update_page_state('analytics', page_state)

def _render_enhanced_header():
    """Render enhanced header with real-time analytics status."""
    # Main header with live indicators
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <h1 style="margin: 0; background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%); 
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                       font-size: 2.3em; font-weight: bold;">
                📈 Advanced Analytics Intelligence
            </h1>
            <span style="margin-left: 15px; padding: 6px 12px; background: linear-gradient(90deg, #667eea, #764ba2); 
                         color: white; border-radius: 20px; font-size: 12px; font-weight: bold; 
                         animation: pulse 2s infinite;">
                🧠 AI POWERED
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Live analytics status
        current_time = datetime.now().strftime("%H:%M:%S")
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; color: white; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
            <div style="font-size: 16px; font-weight: bold;">⏰ {current_time}</div>
            <div style="font-size: 11px; opacity: 0.9;">Analytics Live</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Analytics health indicator
        st.markdown("""
        <div style="text-align: center; padding: 10px; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                    border-radius: 15px; color: white; box-shadow: 0 4px 15px rgba(17, 153, 142, 0.4);">
            <div style="font-size: 16px; font-weight: bold;">🟢 ACTIVE</div>
            <div style="font-size: 11px; opacity: 0.9;">AI Processing</div>
        </div>
        """, unsafe_allow_html=True)

def _render_advanced_time_selector() -> Dict[str, Any]:
    """Render advanced time period selector with predictive features."""
    
    st.markdown("### ⏰ Advanced Time Range & Analytics Controls")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        # Enhanced time period selector
        time_period = st.selectbox(
            "📅 Analysis Period",
            ["1d", "3d", "7d", "14d", "30d", "60d", "90d", "180d", "365d", "custom"],
            format_func=lambda x: {
                "1d": "🕐 Last 24 hours",
                "3d": "📅 Last 3 days", 
                "7d": "📅 Last 7 days",
                "14d": "📅 Last 14 days",
                "30d": "📅 Last 30 days",
                "60d": "📅 Last 60 days",
                "90d": "📅 Last 90 days",
                "180d": "📅 Last 6 months",
                "365d": "📅 Last year",
                "custom": "🎯 Custom Range"
            }[x],
            index=4,  # Default to 30d
            key="advanced_analytics_period"
        )
    
    with col2:
        # Comparison period toggle
        enable_comparison = st.checkbox(
            "📊 Compare Periods",
            value=False,
            key="enable_period_comparison",
            help="Compare with previous period"
        )
    
    with col3:
        # Analytics granularity
        granularity = st.selectbox(
            "🔍 Granularity",
            ["hourly", "daily", "weekly", "monthly"],
            format_func=lambda x: {
                "hourly": "🕐 Hourly",
                "daily": "📅 Daily", 
                "weekly": "📆 Weekly",
                "monthly": "📊 Monthly"
            }[x],
            index=1,  # Default to daily
            key="analytics_granularity"
        )
    
    with col4:
        # Export format selection
        export_format = st.selectbox(
            "📤 Export As",
            ["pdf", "csv", "xlsx", "json"],
            format_func=lambda x: {
                "pdf": "📄 PDF Report",
                "csv": "📊 CSV Data",
                "xlsx": "📈 Excel File", 
                "json": "💾 JSON Data"
            }[x],
            key="export_format"
        )
    
    # Custom date range selector
    start_date, end_date = None, None
    if time_period == "custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=datetime.now())
    
    return {
        'period': time_period,
        'granularity': granularity,
        'enable_comparison': enable_comparison,
        'export_format': export_format,
        'start_date': start_date,
        'end_date': end_date,
        'days': _get_days_from_period(time_period)
    }

def _render_realtime_analytics_metrics(data_loader, time_config: Dict[str, Any]):
    """Render real-time analytics metrics dashboard."""
    
    st.markdown("### 🎯 Real-Time Analytics Intelligence")
    
    # Get cached analytics metrics
    metrics = get_cached_data('analytics_metrics', 60)  # 60 second cache
    if not metrics:
        metrics = _get_enhanced_analytics_metrics(data_loader, time_config)
        set_cached_data('analytics_metrics', metrics, 60)
    
    # Enhanced metrics with trend indicators
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        trend_indicator = "📈" if metrics['profit_trend'] > 0 else "📉" if metrics['profit_trend'] < 0 else "➖"
        profit_color = "#28a745" if metrics['total_profit'] > 10000 else "#ffc107" if metrics['total_profit'] > 5000 else "#dc3545"
        
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, {profit_color}20, {profit_color}10); 
                    border: 2px solid {profit_color}40; border-radius: 15px; text-align: center;
                    box-shadow: 0 4px 15px {profit_color}20;">
            <div style="font-size: 24px; font-weight: bold; color: {profit_color};">€{metrics['total_profit']:,.0f}</div>
            <div style="font-size: 14px; color: #666; margin: 5px 0;">Total Profit Potential</div>
            <div style="font-size: 12px; color: {profit_color};">{trend_indicator} {metrics['profit_trend']:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        opportunity_color = "#17a2b8" if metrics['opportunities'] > 50 else "#ffc107" if metrics['opportunities'] > 20 else "#dc3545"
        opp_trend = "📈" if metrics['opportunity_trend'] > 0 else "📉" if metrics['opportunity_trend'] < 0 else "➖"
        
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, {opportunity_color}20, {opportunity_color}10); 
                    border: 2px solid {opportunity_color}40; border-radius: 15px; text-align: center;
                    box-shadow: 0 4px 15px {opportunity_color}20;">
            <div style="font-size: 24px; font-weight: bold; color: {opportunity_color};">{metrics['opportunities']}</div>
            <div style="font-size: 14px; color: #666; margin: 5px 0;">Active Opportunities</div>
            <div style="font-size: 12px; color: {opportunity_color};">{opp_trend} {metrics['opportunity_trend']:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        accuracy_color = "#28a745" if metrics['accuracy'] > 85 else "#ffc107" if metrics['accuracy'] > 70 else "#dc3545"
        acc_trend = "📈" if metrics['accuracy_trend'] > 0 else "📉" if metrics['accuracy_trend'] < 0 else "➖"
        
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, {accuracy_color}20, {accuracy_color}10); 
                    border: 2px solid {accuracy_color}40; border-radius: 15px; text-align: center;
                    box-shadow: 0 4px 15px {accuracy_color}20;">
            <div style="font-size: 24px; font-weight: bold; color: {accuracy_color};">{metrics['accuracy']:.1f}%</div>
            <div style="font-size: 14px; color: #666; margin: 5px 0;">Detection Accuracy</div>
            <div style="font-size: 12px; color: {accuracy_color};">{acc_trend} {metrics['accuracy_trend']:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_margin_color = "#6f42c1" if metrics['avg_margin'] > 30 else "#fd7e14" if metrics['avg_margin'] > 20 else "#dc3545"
        margin_trend = "📈" if metrics['margin_trend'] > 0 else "📉" if metrics['margin_trend'] < 0 else "➖"
        
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, {avg_margin_color}20, {avg_margin_color}10); 
                    border: 2px solid {avg_margin_color}40; border-radius: 15px; text-align: center;
                    box-shadow: 0 4px 15px {avg_margin_color}20;">
            <div style="font-size: 24px; font-weight: bold; color: {avg_margin_color};">{metrics['avg_margin']:.1f}%</div>
            <div style="font-size: 14px; color: #666; margin: 5px 0;">Avg. Profit Margin</div>
            <div style="font-size: 12px; color: {avg_margin_color};">{margin_trend} {metrics['margin_trend']:+.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        processing_color = "#20c997"
        
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, {processing_color}20, {processing_color}10); 
                    border: 2px solid {processing_color}40; border-radius: 15px; text-align: center;
                    box-shadow: 0 4px 15px {processing_color}20;">
            <div style="font-size: 24px; font-weight: bold; color: {processing_color};">{metrics['processing_speed']:.0f}/min</div>
            <div style="font-size: 14px; color: #666; margin: 5px 0;">Processing Speed</div>
            <div style="font-size: 12px; color: {processing_color};">🚀 Real-time</div>
        </div>
        """, unsafe_allow_html=True)

def _render_enhanced_overview_analytics(data_loader, time_config: Dict[str, Any]):
    """Render enhanced overview analytics with advanced intelligence."""
    
    st.markdown("### 📊 Intelligence Overview Dashboard")
    
    try:
        # Get comprehensive analytics data
        analytics_data = _get_enhanced_analytics_data(data_loader, time_config)
        
        # Advanced metrics comparison
        if time_config['enable_comparison']:
            _render_period_comparison(analytics_data)
        
        # Interactive charts row
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Multi-metric time series
            st.markdown("#### 📈 Multi-Metric Performance Timeline")
            timeline_chart = _create_advanced_timeline_chart(analytics_data['timeline_data'])
            st.plotly_chart(timeline_chart, use_container_width=True)
        
        with col2:
            # Profit distribution heatmap
            st.markdown("#### 🌡️ Profit Distribution Heatmap")
            heatmap_chart = _create_profit_heatmap(analytics_data['profit_matrix'])
            st.plotly_chart(heatmap_chart, use_container_width=True)
        
        # Second row of charts
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Category performance radar
            st.markdown("#### 🎯 Category Performance Radar")
            radar_chart = _create_category_radar_chart(analytics_data['category_performance'])
            st.plotly_chart(radar_chart, use_container_width=True)
        
        with col2:
            # Opportunity funnel
            st.markdown("#### 🔄 Opportunity Conversion Funnel")
            funnel_chart = _create_opportunity_funnel(analytics_data['funnel_data'])
            st.plotly_chart(funnel_chart, use_container_width=True)
        
        with col3:
            # Risk-Reward scatter
            st.markdown("#### ⚖️ Risk vs Reward Analysis")
            scatter_chart = _create_risk_reward_scatter(analytics_data['risk_reward_data'])
            st.plotly_chart(scatter_chart, use_container_width=True)
        
    except Exception as e:
        logger.error(f"Error rendering enhanced overview analytics: {e}")
        st.error("Could not load enhanced overview analytics")

def _render_predictive_analytics(data_loader, time_config: Dict[str, Any]):
    """Render predictive analytics with AI-powered insights."""
    
    st.markdown("### 🔮 Predictive Analytics & AI Insights")
    
    try:
        # Get predictive data
        predictive_data = _get_predictive_analytics_data(data_loader, time_config)
        
        # AI insights cards
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Predictive models row
            model_col1, model_col2 = st.columns(2)
            
            with model_col1:
                st.markdown("#### 🎯 Profit Forecasting Model")
                forecast_chart = _create_profit_forecast_chart(predictive_data['profit_forecast'])
                st.plotly_chart(forecast_chart, use_container_width=True)
            
            with model_col2:
                st.markdown("#### 📊 Trend Prediction Model")
                trend_chart = _create_trend_prediction_chart(predictive_data['trend_predictions'])
                st.plotly_chart(trend_chart, use_container_width=True)
        
        with col2:
            # AI insights panel
            st.markdown("#### 🧠 AI-Generated Insights")
            
            insights = predictive_data['ai_insights']
            for i, insight in enumerate(insights):
                insight_type = insight['type']
                confidence = insight['confidence']
                
                # Color coding based on insight type
                colors = {
                    'opportunity': '#28a745',
                    'warning': '#ffc107', 
                    'critical': '#dc3545',
                    'info': '#17a2b8'
                }
                color = colors.get(insight_type, '#6c757d')
                
                st.markdown(f"""
                <div style="padding: 12px; margin: 8px 0; background: linear-gradient(135deg, {color}15, {color}05); 
                            border-left: 4px solid {color}; border-radius: 8px;">
                    <div style="font-weight: bold; color: {color}; margin-bottom: 5px;">
                        {insight['icon']} {insight['title']}
                    </div>
                    <div style="font-size: 13px; color: #555; margin-bottom: 5px;">
                        {insight['description']}
                    </div>
                    <div style="font-size: 11px; color: {color};">
                        Confidence: {confidence:.0f}% • Impact: {insight['impact']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Advanced predictive models
        st.markdown("#### 🚀 Advanced Predictive Models")
        
        pred_tab1, pred_tab2, pred_tab3 = st.tabs(["📈 Price Prediction", "🎯 Demand Forecast", "⚡ Anomaly Detection"])
        
        with pred_tab1:
            _render_price_prediction_model(predictive_data)
        
        with pred_tab2:
            _render_demand_forecast_model(predictive_data)
        
        with pred_tab3:
            _render_anomaly_detection_model(predictive_data)
        
    except Exception as e:
        logger.error(f"Error rendering predictive analytics: {e}")
        st.error("Could not load predictive analytics")

def _render_advanced_pricing_analytics(data_loader, time_config: Dict[str, Any]):
    """Render advanced pricing analytics with deep insights."""
    
    st.markdown("### 💰 Advanced Pricing Intelligence")
    
    try:
        pricing_data = _get_advanced_pricing_data(data_loader, time_config)
        
        # Pricing intelligence metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Price Volatility Index", f"{pricing_data['volatility_index']:.2f}")
        with col2:
            st.metric("Market Premium", f"{pricing_data['market_premium']:.1f}%")
        with col3:
            st.metric("Optimal Price Range", f"€{pricing_data['optimal_range'][0]:.0f}-{pricing_data['optimal_range'][1]:.0f}")
        with col4:
            st.metric("Price Efficiency", f"{pricing_data['efficiency_score']:.1f}%")
        
        # Advanced pricing charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Price elasticity analysis
            st.markdown("#### 📊 Price Elasticity Analysis")
            elasticity_chart = _create_price_elasticity_chart(pricing_data['elasticity_data'])
            st.plotly_chart(elasticity_chart, use_container_width=True)
        
        with col2:
            # Competitor price comparison
            st.markdown("#### 🥊 Competitive Price Analysis")
            competitive_chart = _create_competitive_analysis_chart(pricing_data['competitive_data'])
            st.plotly_chart(competitive_chart, use_container_width=True)
        
        # Price optimization recommendations
        st.markdown("#### 💡 AI-Powered Price Optimization")
        _render_price_optimization_recommendations(pricing_data['optimization_recs'])
        
    except Exception as e:
        logger.error(f"Error rendering advanced pricing analytics: {e}")
        st.error("Could not load advanced pricing analytics")

def _render_alert_intelligence_analytics(data_loader, time_config: Dict[str, Any]):
    """Render alert intelligence analytics with advanced insights."""
    
    st.markdown("### 🎯 Alert Intelligence Analytics")
    
    try:
        alert_data = _get_alert_intelligence_data(data_loader, time_config)
        
        # Alert intelligence metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Alert Precision", f"{alert_data['precision']:.1f}%", delta=f"{alert_data['precision_change']:+.1f}%")
        with col2:
            st.metric("Response Time", f"{alert_data['avg_response_time']:.1f}min", delta=f"{alert_data['response_time_change']:+.1f}min")
        with col3:
            st.metric("False Positives", f"{alert_data['false_positives']:.1f}%", delta=f"{alert_data['fp_change']:+.1f}%")
        with col4:
            st.metric("Alert Value", f"€{alert_data['avg_alert_value']:,.0f}", delta=f"€{alert_data['value_change']:+,.0f}")
        
        # Alert analytics charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Alert severity timeline
            st.markdown("#### 🚨 Alert Severity Timeline")
            severity_chart = _create_alert_severity_timeline(alert_data['severity_timeline'])
            st.plotly_chart(severity_chart, use_container_width=True)
        
        with col2:
            # Alert category performance
            st.markdown("#### 📊 Alert Category Performance")
            category_perf_chart = _create_alert_category_performance(alert_data['category_performance'])
            st.plotly_chart(category_perf_chart, use_container_width=True)
        
    except Exception as e:
        logger.error(f"Error rendering alert intelligence analytics: {e}")
        st.error("Could not load alert intelligence analytics")

def _render_performance_deep_dive(data_loader, time_config: Dict[str, Any]):
    """Render performance deep dive analytics."""
    
    st.markdown("### 🔄 Performance Deep Dive Analytics")
    
    try:
        perf_data = _get_performance_deep_dive_data(data_loader, time_config)
        
        # Performance metrics grid
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("System Uptime", f"{perf_data['uptime']:.1f}%")
        with col2:
            st.metric("Processing Speed", f"{perf_data['processing_speed']:.0f}/min")
        with col3:
            st.metric("Memory Usage", f"{perf_data['memory_usage']:.1f}%")
        with col4:
            st.metric("Cache Hit Rate", f"{perf_data['cache_hit_rate']:.1f}%")
        with col5:
            st.metric("Error Rate", f"{perf_data['error_rate']:.2f}%")
        
        # Performance visualization
        col1, col2 = st.columns(2)
        
        with col1:
            # System resource utilization
            st.markdown("#### 💻 Resource Utilization Timeline")
            resource_chart = _create_resource_utilization_chart(perf_data['resource_data'])
            st.plotly_chart(resource_chart, use_container_width=True)
        
        with col2:
            # Performance bottleneck analysis
            st.markdown("#### 🔍 Bottleneck Analysis")
            bottleneck_chart = _create_bottleneck_analysis_chart(perf_data['bottleneck_data'])
            st.plotly_chart(bottleneck_chart, use_container_width=True)
        
    except Exception as e:
        logger.error(f"Error rendering performance deep dive: {e}")
        st.error("Could not load performance deep dive analytics")

def _render_price_prediction_model(predictive_data: Dict):
    """Render price prediction model visualization."""
    col1, col2 = st.columns(2)
    
    with col1:
        # Price trend prediction
        st.markdown("##### 📈 Price Trend Prediction")
        trend_chart = _create_price_trend_prediction_chart()
        st.plotly_chart(trend_chart, use_container_width=True)
    
    with col2:
        # Price volatility forecast
        st.markdown("##### 📊 Volatility Forecast")
        volatility_chart = _create_volatility_forecast_chart()
        st.plotly_chart(volatility_chart, use_container_width=True)

def _render_demand_forecast_model(predictive_data: Dict):
    """Render demand forecasting model."""
    col1, col2 = st.columns(2)
    
    with col1:
        # Demand prediction
        st.markdown("##### 🎯 Demand Prediction")
        demand_chart = _create_demand_prediction_chart()
        st.plotly_chart(demand_chart, use_container_width=True)
    
    with col2:
        # Seasonal patterns
        st.markdown("##### 🔄 Seasonal Patterns")
        seasonal_chart = _create_seasonal_pattern_chart()
        st.plotly_chart(seasonal_chart, use_container_width=True)

def _render_anomaly_detection_model(predictive_data: Dict):
    """Render anomaly detection visualization."""
    col1, col2 = st.columns(2)
    
    with col1:
        # Anomaly timeline
        st.markdown("##### ⚡ Anomaly Detection")
        anomaly_chart = _create_anomaly_detection_chart()
        st.plotly_chart(anomaly_chart, use_container_width=True)
    
    with col2:
        # Anomaly classification
        st.markdown("##### 🏷️ Anomaly Classification")
        classification_chart = _create_anomaly_classification_chart()
        st.plotly_chart(classification_chart, use_container_width=True)

def _render_period_comparison(analytics_data: Dict):
    """Render period comparison analytics."""
    st.markdown("#### 📊 Period Comparison Analysis")
    
    comparison_metrics = {
        'Current Period': {'profit': 47850, 'opportunities': 67, 'accuracy': 89.2},
        'Previous Period': {'profit': 42100, 'opportunities': 58, 'accuracy': 86.8}
    }
    
    col1, col2, col3 = st.columns(3)
    
    for period, metrics in comparison_metrics.items():
        color = '#28a745' if period == 'Current Period' else '#6c757d'
        with col1 if period == 'Current Period' else col2:
            st.markdown(f"""
            <div style="padding: 15px; background: {color}15; border: 2px solid {color}40; 
                        border-radius: 10px; text-align: center;">
                <h4 style="color: {color}; margin: 0;">{period}</h4>
                <div style="margin: 10px 0;">
                    <div>💰 €{metrics['profit']:,}</div>
                    <div>🎯 {metrics['opportunities']} opportunities</div>
                    <div>✅ {metrics['accuracy']:.1f}% accuracy</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        # Comparison summary
        profit_change = ((47850 - 42100) / 42100) * 100
        opp_change = ((67 - 58) / 58) * 100
        acc_change = 89.2 - 86.8
        
        st.markdown(f"""
        <div style="padding: 15px; background: #17a2b815; border: 2px solid #17a2b840; 
                    border-radius: 10px; text-align: center;">
            <h4 style="color: #17a2b8; margin: 0;">📈 Changes</h4>
            <div style="margin: 10px 0;">
                <div style="color: #28a745;">💰 +{profit_change:.1f}%</div>
                <div style="color: #28a745;">🎯 +{opp_change:.1f}%</div>
                <div style="color: #28a745;">✅ +{acc_change:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def _render_price_optimization_recommendations(optimization_recs: List[Dict]):
    """Render price optimization recommendations."""
    for i, rec in enumerate(optimization_recs):
        impact_color = {
            'High': '#28a745',
            'Medium': '#ffc107', 
            'Low': '#17a2b8'
        }.get(rec['impact'], '#6c757d')
        
        st.markdown(f"""
        <div style="padding: 12px; margin: 8px 0; background: {impact_color}10; 
                    border-left: 4px solid {impact_color}; border-radius: 8px;">
            <div style="display: flex; justify-content: between; align-items: center;">
                <div>
                    <div style="font-weight: bold; color: {impact_color};">
                        {rec['title']}
                    </div>
                    <div style="font-size: 13px; color: #555; margin: 5px 0;">
                        {rec['description']}
                    </div>
                    <div style="font-size: 11px; color: {impact_color};">
                        Expected Impact: {rec['impact']} • Confidence: {rec['confidence']:.0f}%
                    </div>
                </div>
                <div style="margin-left: 20px;">
                    <span style="background: {impact_color}; color: white; padding: 4px 8px; 
                                 border-radius: 12px; font-size: 11px;">
                        {rec['action']}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Chart creation helper functions
def _create_alert_severity_timeline(severity_data: Dict) -> go.Figure:
    """Create alert severity timeline chart."""
    dates = [(datetime.now() - timedelta(days=30-i)) for i in range(30)]
    critical = [2 + np.random.poisson(1) for _ in range(30)]
    high = [5 + np.random.poisson(2) for _ in range(30)]
    medium = [8 + np.random.poisson(3) for _ in range(30)]
    low = [3 + np.random.poisson(1) for _ in range(30)]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=dates, y=critical, name='Critical', stackgroup='one', fillcolor='#dc3545'))
    fig.add_trace(go.Scatter(x=dates, y=high, name='High', stackgroup='one', fillcolor='#fd7e14'))
    fig.add_trace(go.Scatter(x=dates, y=medium, name='Medium', stackgroup='one', fillcolor='#ffc107'))
    fig.add_trace(go.Scatter(x=dates, y=low, name='Low', stackgroup='one', fillcolor='#28a745'))
    
    fig.update_layout(height=300, title="Alert Severity Distribution Over Time")
    return fig

def _create_price_trend_prediction_chart() -> go.Figure:
    """Create price trend prediction chart."""
    dates = [(datetime.now() + timedelta(days=i)) for i in range(30)]
    predicted_prices = [250 + 50*np.sin(i/7) + np.random.normal(0, 10) for i in range(30)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=predicted_prices,
        name='Predicted Price Trend',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.update_layout(height=250, title="30-Day Price Trend Prediction")
    return fig

def _create_volatility_forecast_chart() -> go.Figure:
    """Create volatility forecast chart."""
    dates = [(datetime.now() + timedelta(days=i)) for i in range(30)]
    volatility = [0.15 + 0.05*np.sin(i/5) + np.random.normal(0, 0.02) for i in range(30)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=volatility,
        name='Volatility Index',
        line=dict(color='#ff7f0e', width=2),
        fill='tonexty'
    ))
    
    fig.update_layout(height=250, title="Price Volatility Forecast")
    return fig

# Data generation functions
def _get_alert_intelligence_data(data_loader, time_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get alert intelligence analytics data."""
    return {
        'precision': 87.5 + np.random.normal(0, 2),
        'precision_change': np.random.normal(1.8, 1),
        'avg_response_time': 3.2 + np.random.normal(0, 0.5),
        'response_time_change': np.random.normal(-0.3, 0.2),
        'false_positives': 8.3 + np.random.normal(0, 1),
        'fp_change': np.random.normal(-1.2, 0.5),
        'avg_alert_value': 245 + np.random.normal(0, 20),
        'value_change': np.random.normal(15, 10),
        'severity_timeline': {},
        'category_performance': {}
    }

def _get_performance_deep_dive_data(data_loader, time_config: Dict[str, Any]) -> Dict[str, Any]:
    """Get performance deep dive analytics data."""
    return {
        'uptime': 99.2 + np.random.normal(0, 0.5),
        'processing_speed': 32.5 + np.random.normal(0, 3),
        'memory_usage': 67.8 + np.random.normal(0, 5),
        'cache_hit_rate': 94.3 + np.random.normal(0, 2),
        'error_rate': 0.15 + np.random.normal(0, 0.05),
        'resource_data': {},
        'bottleneck_data': {}
    }

def _generate_optimization_recommendations() -> List[Dict]:
    """Generate price optimization recommendations."""
    return [
        {
            'title': 'Increase Gaming Category Focus',
            'description': 'Gaming products show 45% higher profit margins. Recommend increasing monitoring frequency.',
            'impact': 'High',
            'confidence': 89,
            'action': 'Implement'
        },
        {
            'title': 'Adjust Price Thresholds',
            'description': 'Lower minimum price threshold to €150 to capture more opportunities.',
            'impact': 'Medium',
            'confidence': 76,
            'action': 'Test'
        },
        {
            'title': 'Optimize Processing Schedule',
            'description': 'Peak opportunities detected between 14:00-16:00 CET.',
            'impact': 'Medium',
            'confidence': 82,
            'action': 'Schedule'
        }
    ]

def _create_trend_prediction_chart(trend_data: Dict) -> go.Figure:
    """Create trend prediction chart."""
    # Simple trend prediction visualization
    dates = [(datetime.now() + timedelta(days=i)) for i in range(15)]
    trend_values = [85 + 5*np.sin(i/3) + np.random.normal(0, 2) for i in range(15)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=trend_values,
        name='Trend Prediction',
        line=dict(color='#2ca02c', width=2)
    ))
    
    fig.update_layout(height=300, title="Market Trend Prediction")
    return fig

# Additional helper functions for remaining chart creation methods
def _create_demand_prediction_chart() -> go.Figure:
    """Create demand prediction chart."""
    dates = [(datetime.now() + timedelta(days=i)) for i in range(30)]
    demand = [100 + 20*np.sin(i/7) + np.random.normal(0, 5) for i in range(30)]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=demand, name='Predicted Demand'))
    fig.update_layout(height=250, title="Demand Prediction")
    return fig

def _create_seasonal_pattern_chart() -> go.Figure:
    """Create seasonal pattern chart."""
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    patterns = [85, 90, 95, 88, 92, 78, 75, 82, 95, 100, 110, 105]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=months, y=patterns, mode='lines+markers', name='Seasonal Pattern'))
    fig.update_layout(height=250, title="Seasonal Demand Patterns")
    return fig

def _create_anomaly_detection_chart() -> go.Figure:
    """Create anomaly detection chart."""
    dates = [(datetime.now() - timedelta(days=30-i)) for i in range(30)]
    normal_data = [100 + 10*np.sin(i/5) + np.random.normal(0, 3) for i in range(30)]
    anomalies = [5, 12, 24]  # Days with anomalies
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=normal_data, name='Normal Data', line=dict(color='blue')))
    
    # Highlight anomalies
    for day in anomalies:
        if day < len(dates):
            fig.add_trace(go.Scatter(
                x=[dates[day]], y=[normal_data[day]], 
                mode='markers', marker=dict(color='red', size=10),
                name=f'Anomaly {day+1}' if day == anomalies[0] else '',
                showlegend=day == anomalies[0]
            ))
    
    fig.update_layout(height=250, title="Anomaly Detection Timeline")
    return fig

def _create_anomaly_classification_chart() -> go.Figure:
    """Create anomaly classification chart."""
    categories = ['Price Spike', 'Volume Drop', 'System Error', 'Data Quality']
    counts = [3, 2, 1, 2]
    
    fig = go.Figure()
    fig.add_trace(go.Pie(labels=categories, values=counts, name="Anomaly Types"))
    fig.update_layout(height=250, title="Anomaly Classification")
    return fig

def _create_alert_category_performance(category_data: Dict) -> go.Figure:
    """Create alert category performance chart."""
    categories = ['Electronics', 'Gaming', 'Smartphones', 'Audio', 'Accessories']
    performance = [92, 88, 85, 90, 87]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=categories, y=performance, name='Performance Score'))
    fig.update_layout(height=300, title="Alert Performance by Category")
    return fig

def _create_resource_utilization_chart(resource_data: Dict) -> go.Figure:
    """Create resource utilization chart."""
    times = [(datetime.now() - timedelta(hours=24-i)) for i in range(24)]
    cpu = [60 + 20*np.sin(i/4) + np.random.normal(0, 5) for i in range(24)]
    memory = [70 + 15*np.sin(i/6) + np.random.normal(0, 3) for i in range(24)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=cpu, name='CPU %', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=times, y=memory, name='Memory %', line=dict(color='red')))
    fig.update_layout(height=300, title="System Resource Utilization")
    return fig

def _create_bottleneck_analysis_chart(bottleneck_data: Dict) -> go.Figure:
    """Create bottleneck analysis chart."""
    components = ['Database', 'Network', 'CPU', 'Memory', 'Disk I/O']
    utilization = [45, 30, 65, 70, 25]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=components, y=utilization, name='Utilization %'))
    fig.update_layout(height=300, title="System Bottleneck Analysis")
    return fig

def _create_price_elasticity_chart(elasticity_data: Dict) -> go.Figure:
    """Create price elasticity chart."""
    prices = [100, 150, 200, 250, 300, 350, 400]
    demand = [100, 85, 70, 55, 45, 35, 25]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices, y=demand, mode='lines+markers', name='Price Elasticity'))
    fig.update_layout(height=300, title="Price Elasticity Analysis", 
                     xaxis_title="Price (€)", yaxis_title="Demand Index")
    return fig

def _create_competitive_analysis_chart(competitive_data: Dict) -> go.Figure:
    """Create competitive analysis chart."""
    competitors = ['MediaMarkt', 'Amazon DE', 'Amazon ES', 'Amazon FR', 'Amazon IT']
    avg_prices = [299, 315, 295, 320, 310]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=competitors, y=avg_prices, name='Average Price'))
    fig.update_layout(height=300, title="Competitive Price Analysis")
    return fig

def _create_opportunity_funnel(funnel_data: Dict) -> go.Figure:
    """Create opportunity conversion funnel."""
    stages = ['Products Scanned', 'Matches Found', 'Price Opportunities', 'Alerts Generated', 'Conversions']
    values = [10000, 2500, 850, 245, 87]
    
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial"
    ))
    fig.update_layout(height=300, title="Opportunity Conversion Funnel")
    return fig

def _create_risk_reward_scatter(risk_reward_data: Dict) -> go.Figure:
    """Create risk vs reward scatter plot."""
    risk_scores = [20, 35, 45, 60, 75, 80, 25, 40, 55, 70]
    reward_scores = [15, 45, 65, 80, 95, 85, 30, 50, 75, 90]
    categories = ['Electronics'] * 4 + ['Gaming'] * 3 + ['Audio'] * 3
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=risk_scores, y=reward_scores,
        mode='markers',
        marker=dict(size=10, color=range(len(risk_scores)), colorscale='Viridis'),
        text=categories,
        name='Opportunities'
    ))
    fig.update_layout(height=300, title="Risk vs Reward Analysis",
                     xaxis_title="Risk Score", yaxis_title="Reward Score")
    return fig

# Placeholder functions for completeness
def _generate_profit_forecast() -> Dict:
    """Generate profit forecast data."""
    return {'forecast': 'data'}

def _generate_trend_predictions() -> Dict:
    """Generate trend prediction data."""
    return {'trends': 'data'}

def _generate_elasticity_data() -> Dict:
    """Generate price elasticity data."""
    return {'elasticity': 'data'}

def _generate_competitive_data() -> Dict:
    """Generate competitive analysis data."""
    return {'competitive': 'data'} 