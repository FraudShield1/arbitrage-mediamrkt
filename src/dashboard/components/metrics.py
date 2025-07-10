"""Metrics dashboard component for displaying key system statistics."""

import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..utils.mongodb_loader import MongoDBDataLoader


class MetricsDashboard:
    """Dashboard component for displaying key metrics with delta indicators."""
    
    def __init__(self, data_loader: MongoDBDataLoader):
        """Initialize metrics dashboard.
        
        Args:
            data_loader: MongoDBDataLoader instance for fetching data
        """
        self.data_loader = data_loader
    
    def render(self) -> None:
        """Render the metrics dashboard component."""
        st.header("📊 System Metrics")
        
        # Load current stats
        stats = self._load_stats()
        if not stats:
            st.error("Unable to load system statistics")
            return
        
        # Load trend data for delta calculations
        trends = self._load_trends()
        
        # Create metric cards
        self._render_metric_cards(stats, trends)
        
        # System health indicator
        self._render_system_health(stats)
        
        # Quick action buttons
        self._render_quick_actions()
    
    def _load_stats(self) -> Optional[Dict[str, Any]]:
        """Load current system statistics."""
        try:
            return self.data_loader.get_system_stats()
        except Exception as e:
            st.error(f"Error loading statistics: {e}")
            return None
    
    def _load_trends(self) -> Optional[Dict[str, Any]]:
        """Load trend data for delta calculations."""
        try:
            return self.data_loader.get_trends()
        except Exception as e:
            # Trends are optional, log but don't show error
            return None
    
    def _render_metric_cards(self, stats: Dict[str, Any], trends: Optional[Dict[str, Any]]) -> None:
        """Render metric cards with delta indicators."""
        
        # Create 4 columns for main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            active_alerts = stats.get("active_alerts", 0)
            alert_delta = self._calculate_delta(trends, "active_alerts_delta") if trends else None
            self._render_metric_card(
                "🚨 Active Alerts",
                active_alerts,
                alert_delta,
                delta_color="normal" if alert_delta and alert_delta > 0 else "inverse"
            )
        
        with col2:
            total_products = stats.get("total_products", 0)
            products_delta = self._calculate_delta(trends, "products_delta") if trends else None
            self._render_metric_card(
                "📦 Total Products",
                f"{total_products:,}",
                products_delta,
                delta_color="normal"
            )
        
        with col3:
            profit_potential = stats.get("total_profit_potential", 0)
            profit_delta = self._calculate_delta(trends, "profit_delta") if trends else None
            self._render_metric_card(
                "💰 Profit Potential",
                f"€{profit_potential:,.2f}",
                profit_delta,
                delta_color="normal"
            )
        
        with col4:
            success_rate = stats.get("success_rate", 0)
            success_delta = self._calculate_delta(trends, "success_rate_delta") if trends else None
            self._render_metric_card(
                "✅ Success Rate",
                f"{success_rate:.1f}%",
                success_delta,
                delta_color="normal"
            )
        
        # Secondary metrics in a second row
        st.markdown("---")
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            avg_roi = stats.get("average_roi", 0)
            self._render_metric_card(
                "📈 Average ROI",
                f"{avg_roi:.1f}%",
                None
            )
        
        with col6:
            products_scraped_today = stats.get("products_scraped_today", 0)
            self._render_metric_card(
                "🔄 Scraped Today",
                f"{products_scraped_today:,}",
                None
            )
        
        with col7:
            critical_alerts = stats.get("critical_alerts", 0)
            self._render_metric_card(
                "🔴 Critical Alerts",
                critical_alerts,
                None,
                background_color="#ffebee" if critical_alerts > 0 else None
            )
        
        with col8:
            last_scrape = stats.get("last_scrape_time")
            if last_scrape:
                try:
                    # Parse ISO format timestamp
                    if last_scrape.endswith('Z'):
                        last_scrape_dt = datetime.fromisoformat(last_scrape.replace('Z', '+00:00'))
                    else:
                        last_scrape_dt = datetime.fromisoformat(last_scrape)
                    
                    # Calculate time difference
                    time_diff = datetime.utcnow() - last_scrape_dt.replace(tzinfo=None)
                    
                    if time_diff.total_seconds() < 3600:  # Less than 1 hour
                        minutes_ago = int(time_diff.total_seconds() / 60)
                        last_scrape_text = f"{minutes_ago}m ago"
                        color = "normal"
                    elif time_diff.total_seconds() < 86400:  # Less than 1 day
                        hours_ago = int(time_diff.total_seconds() / 3600)
                        last_scrape_text = f"{hours_ago}h ago"
                        color = "normal" if hours_ago < 6 else "inverse"
                    else:  # More than 1 day
                        days_ago = int(time_diff.total_seconds() / 86400)
                        last_scrape_text = f"{days_ago}d ago"
                        color = "inverse"
                except (ValueError, TypeError):
                    last_scrape_text = "Parse Error"
                    color = "inverse"
            else:
                last_scrape_text = "Never"
                color = "inverse"
            
            self._render_metric_card(
                "⏰ Last Scrape",
                last_scrape_text,
                None,
                delta_color=color
            )
    
    def _render_metric_card(
        self,
        title: str,
        value: Any,
        delta: Optional[float] = None,
        delta_color: str = "normal",
        background_color: Optional[str] = None
    ) -> None:
        """Render a single metric card."""
        
        # Custom CSS for metric cards
        card_style = f"""
        <div style="
            background-color: {background_color or '#f0f2f6'};
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
            margin-bottom: 1rem;
        ">
            <h4 style="margin: 0; color: #333; font-size: 0.9rem;">{title}</h4>
            <h2 style="margin: 0.2rem 0; color: #1f77b4; font-weight: bold;">{value}</h2>
        """
        
        if delta is not None:
            delta_symbol = "↗️" if delta > 0 else "↘️" if delta < 0 else "➡️"
            delta_color_code = "#4caf50" if (delta > 0 and delta_color == "normal") or (delta < 0 and delta_color == "inverse") else "#f44336"
            card_style += f"""
            <p style="margin: 0; color: {delta_color_code}; font-size: 0.8rem;">
                {delta_symbol} {abs(delta):.1f}% vs last period
            </p>
            """
        
        card_style += "</div>"
        st.markdown(card_style, unsafe_allow_html=True)
    
    def _calculate_delta(self, trends: Dict[str, Any], key: str) -> Optional[float]:
        """Calculate percentage delta from trends data."""
        if not trends or key not in trends:
            return None
        
        return trends[key]
    
    def _render_system_health(self, stats: Dict[str, Any]) -> None:
        """Render system health indicator."""
        st.markdown("---")
        st.subheader("🔋 System Health")
        
        # Calculate overall health score
        health_factors = {
            "API Response": self._get_api_health(),
            "Last Scrape": self._get_scrape_health(stats),
            "Database": self._get_database_health(),
            "Task Queue": self._get_queue_health(stats)
        }
        
        # Display health indicators
        health_cols = st.columns(len(health_factors))
        
        for i, (component, status) in enumerate(health_factors.items()):
            with health_cols[i]:
                status_color = {
                    "healthy": "🟢",
                    "warning": "🟡", 
                    "critical": "🔴"
                }.get(status, "⚪")
                
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <div style="font-size: 2rem;">{status_color}</div>
                    <div style="font-size: 0.8rem; color: #666;">{component}</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Overall health gauge
        healthy_count = sum(1 for status in health_factors.values() if status == "healthy")
        health_percentage = (healthy_count / len(health_factors)) * 100
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = health_percentage,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Overall Health"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    def _get_api_health(self) -> str:
        """Check API health status."""
        try:
            health = self.data_loader.health_check()
            return "healthy" if health.get("status") == "ok" else "critical"
        except:
            return "critical"
    
    def _get_scrape_health(self, stats: Dict[str, Any]) -> str:
        """Check scraping health based on last scrape time."""
        last_scrape = stats.get("last_scrape_time")
        if not last_scrape:
            return "critical"
        
        time_diff = datetime.now() - datetime.fromisoformat(last_scrape.replace('Z', '+00:00'))
        minutes_ago = time_diff.total_seconds() / 60
        
        if minutes_ago < 45:  # Expected every 30 minutes
            return "healthy"
        elif minutes_ago < 90:
            return "warning"
        else:
            return "critical"
    
    def _get_database_health(self) -> str:
        """Check database health (simplified)."""
        # In a real implementation, this would check database connectivity
        # For now, assume healthy if we can load stats
        try:
            stats = self.data_loader.get_stats()
            return "healthy" if stats else "critical"
        except:
            return "critical"
    
    def _get_queue_health(self, stats: Dict[str, Any]) -> str:
        """Check task queue health."""
        # Check if tasks are processing normally
        # This could be enhanced with actual Celery queue monitoring
        active_tasks = stats.get("active_background_tasks", 0)
        failed_tasks = stats.get("failed_tasks_last_hour", 0)
        
        if failed_tasks > 10:
            return "critical"
        elif failed_tasks > 5:
            return "warning"
        else:
            return "healthy"
    
    def _render_quick_actions(self) -> None:
        """Render quick action buttons."""
        st.markdown("---")
        st.subheader("⚡ Quick Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Force Refresh", help="Refresh all data"):
                self.data_loader.clear_cache()
                st.rerun()
        
        with col2:
            if st.button("🚨 View Critical Alerts", help="Go to critical alerts"):
                st.session_state.page = "Alerts"
                st.session_state.alert_filter = "critical"
                st.rerun()
        
        with col3:
            if st.button("📊 View Analytics", help="Go to analytics dashboard"):
                st.session_state.page = "Analytics"
                st.rerun()
        
        with col4:
            if st.button("⚙️ Settings", help="Go to settings"):
                st.session_state.page = "Settings"
                st.rerun() 