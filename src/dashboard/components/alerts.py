"""Alerts management component for displaying and managing price alerts."""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.mongodb_loader import MongoDBDataLoader


class AlertsTable:
    """Dashboard component for displaying and managing alerts."""
    
    def __init__(self, data_loader: MongoDBDataLoader):
        """Initialize alerts table.
        
        Args:
            data_loader: MongoDBDataLoader instance for fetching data
        """
        self.data_loader = data_loader
    
    def render(self) -> None:
        """Render the alerts table component."""
        st.header("🚨 Arbitrage Alerts")
        
        # Render filters
        filters = self._render_filters()
        
        # Load alerts with filters
        alerts = self._load_alerts(filters)
        if alerts is None:
            st.error("Unable to load alerts")
            return
        
        # Display summary stats
        self._render_alert_summary(alerts)
        
        # Render the main alerts table
        self._render_alerts_table(alerts)
    
    def _render_filters(self) -> Dict[str, Any]:
        """Render filter controls and return filter values."""
        st.subheader("🔍 Filters")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_filter = st.selectbox(
                "Status",
                options=["all", "active", "processed", "dismissed"],
                index=0
            )
        
        with col2:
            severity_filter = st.selectbox(
                "Severity",
                options=["all", "critical", "high", "medium"],
                index=0
            )
        
        with col3:
            min_profit = st.number_input(
                "Min Profit (€)",
                min_value=0.0,
                value=10.0,
                step=5.0
            )
        
        with col4:
            category_filter = st.selectbox(
                "Category",
                options=["all", "Electronics", "Home & Garden", "Sports", "Fashion", "Books"],
                index=0
            )
        
        return {
            "status": status_filter,
            "severity": severity_filter,
            "min_profit": min_profit,
            "category": category_filter,
        }
    
    def _load_alerts(self, filters: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Load alerts with applied filters."""
        try:
            # Convert filters for MongoDB query
            status_filter = filters["status"] if filters["status"] != "all" else None
            
            # Get alerts from MongoDB
            alerts_data = self.data_loader.get_alerts(
                page=1,
                size=100,  # Get more alerts for dashboard
                status=status_filter
            )
            
            if not alerts_data or "alerts" not in alerts_data:
                return []
            
            alerts = alerts_data["alerts"]
            
            # Apply additional filters
            filtered_alerts = []
            for alert in alerts:
                # Apply profit filter
                profit = alert.get("savings_amount", 0)
                if profit < filters["min_profit"]:
                    continue
                
                # Apply category filter
                if filters["category"] != "all":
                    category = alert.get("category", "")
                    if filters["category"].lower() not in category.lower():
                        continue
                
                # Apply severity filter (map urgency to severity)
                if filters["severity"] != "all":
                    urgency = alert.get("urgency", "MEDIUM").lower()
                    severity_map = {
                        "critical": "critical",
                        "high": "high", 
                        "medium": "medium",
                        "low": "medium"
                    }
                    mapped_severity = severity_map.get(urgency, "medium")
                    if mapped_severity != filters["severity"]:
                        continue
                
                # Add computed fields for dashboard compatibility
                alert["profit_potential"] = alert.get("savings_amount", 0)
                alert["roi_percentage"] = alert.get("discount_percentage", 0)
                alert["mediamarkt_price"] = alert.get("price", 0)
                alert["amazon_price"] = alert.get("original_price", 0)
                alert["severity"] = severity_map.get(alert.get("urgency", "MEDIUM").lower(), "medium")
                
                filtered_alerts.append(alert)
            
            return filtered_alerts
        
        except Exception as e:
            st.error(f"Error loading alerts: {e}")
            return None
    
    def _render_alert_summary(self, alerts: List[Dict[str, Any]]) -> None:
        """Render summary statistics for current alerts."""
        if not alerts:
            st.info("No alerts found matching the current filters.")
            return
        
        # Calculate summary stats
        total_alerts = len(alerts)
        total_profit = sum(alert.get("profit_potential", 0) for alert in alerts)
        avg_roi = sum(alert.get("roi_percentage", 0) for alert in alerts) / total_alerts if total_alerts > 0 else 0
        
        # Count by severity
        severity_counts = {}
        for alert in alerts:
            severity = alert.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Display summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Alerts", f"{total_alerts:,}")
        
        with col2:
            st.metric("Total Profit Potential", f"€{total_profit:,.2f}")
        
        with col3:
            st.metric("Average ROI", f"{avg_roi:.1f}%")
        
        with col4:
            critical_count = severity_counts.get("critical", 0)
            st.metric("Critical Alerts", critical_count, delta=critical_count if critical_count > 0 else None)
        
        # Severity distribution
        if severity_counts:
            st.write("**Severity Distribution:**")
            severity_cols = st.columns(len(severity_counts))
            
            for i, (severity, count) in enumerate(severity_counts.items()):
                with severity_cols[i]:
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠", 
                        "medium": "🟡"
                    }.get(severity, "⚪")
                    st.write(f"{severity_emoji} {severity.title()}: {count}")
    
    def _render_alerts_table(self, alerts: List[Dict[str, Any]]) -> None:
        """Render the main alerts table with actions."""
        if not alerts:
            return
        
        st.markdown("---")
        st.subheader("📋 Alert Details")
        
        # Convert to DataFrame for better display
        df_data = []
        for alert in alerts:
            df_data.append({
                "ID": alert["id"],
                "Product": alert.get("product_name", "Unknown")[:50] + ("..." if len(alert.get("product_name", "")) > 50 else ""),
                "MediaMarkt Price": f"€{alert.get('mediamarkt_price', 0):.2f}",
                "Amazon Price": f"€{alert.get('amazon_price', 0):.2f}",
                "Profit": f"€{alert.get('profit_potential', 0):.2f}",
                "ROI": f"{alert.get('roi_percentage', 0):.1f}%",
                "Severity": alert.get("severity", "unknown").title(),
                "Status": alert.get("status", "unknown").title(),
                "Created": self._format_datetime(alert.get("created_at")),
                "Actions": alert["id"]  # Will be used for action buttons
            })
        
        df = pd.DataFrame(df_data)
        
        # Display the table with custom styling
        self._render_styled_table(df, alerts)
        
        # Bulk actions
        self._render_bulk_actions(alerts)
    
    def _render_styled_table(self, df: pd.DataFrame, alerts: List[Dict[str, Any]]) -> None:
        """Render table with custom styling and action buttons."""
        
        # Custom CSS for table styling
        st.markdown("""
        <style>
        .alert-table {
            font-size: 0.9rem;
        }
        .severity-critical {
            background-color: #ffebee !important;
            border-left: 4px solid #f44336;
        }
        .severity-high {
            background-color: #fff3e0 !important;
            border-left: 4px solid #ff9800;
        }
        .severity-medium {
            background-color: #fffde7 !important;
            border-left: 4px solid #ffc107;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Use st.data_editor for interactive table
        edited_df = st.data_editor(
            df.drop(columns=["Actions"]),  # Remove actions column from data editor
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Product": st.column_config.TextColumn("Product", width="large"),
                "MediaMarkt Price": st.column_config.TextColumn("MM Price", width="small"),
                "Amazon Price": st.column_config.TextColumn("AMZ Price", width="small"),
                "Profit": st.column_config.TextColumn("Profit", width="small"),
                "ROI": st.column_config.TextColumn("ROI", width="small"),
                "Severity": st.column_config.SelectboxColumn(
                    "Severity",
                    options=["Critical", "High", "Medium"],
                    width="small"
                ),
                "Status": st.column_config.SelectboxColumn(
                    "Status", 
                    options=["Active", "Processed", "Dismissed"],
                    width="small"
                ),
                "Created": st.column_config.TextColumn("Created", width="medium")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        # Action buttons for each alert
        st.markdown("**Actions:**")
        
        # Create action buttons in columns
        num_alerts = len(alerts)
        if num_alerts > 0:
            # Show actions for first few alerts (limit for performance)
            display_alerts = alerts[:10] if num_alerts > 10 else alerts
            
            for i, alert in enumerate(display_alerts):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    # Alert summary
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡"
                    }.get(alert.get("severity"), "⚪")
                    
                    st.write(f"{severity_emoji} **{alert.get('product_name', 'Unknown')[:40]}** - €{alert.get('profit_potential', 0):.2f} profit")
                
                with col2:
                    if st.button("👁️ View", key=f"view_{alert['id']}", help="View alert details"):
                        self._show_alert_details(alert)
                
                with col3:
                    if st.button("✅ Process", key=f"process_{alert['id']}", help="Mark as processed"):
                        self._process_alert(alert['id'])
                
                with col4:
                    if st.button("❌ Dismiss", key=f"dismiss_{alert['id']}", help="Dismiss alert"):
                        self._dismiss_alert(alert['id'])
                
                with col5:
                    if st.button("🔗 Links", key=f"links_{alert['id']}", help="Show product links"):
                        self._show_product_links(alert)
        
        if num_alerts > 10:
            st.info(f"Showing actions for first 10 alerts. Total: {num_alerts} alerts.")
    
    def _render_bulk_actions(self, alerts: List[Dict[str, Any]]) -> None:
        """Render bulk action controls."""
        if not alerts:
            return
        
        st.markdown("---")
        st.subheader("⚡ Bulk Actions")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("✅ Process All Visible", help="Mark all visible alerts as processed"):
                if st.session_state.get("confirm_bulk_process"):
                    self._bulk_process_alerts([alert["id"] for alert in alerts])
                    st.session_state.confirm_bulk_process = False
                    st.rerun()
                else:
                    st.session_state.confirm_bulk_process = True
                    st.warning("Click again to confirm bulk processing")
        
        with col2:
            if st.button("❌ Dismiss All Critical", help="Dismiss all critical alerts"):
                critical_alerts = [alert["id"] for alert in alerts if alert.get("severity") == "critical"]
                if critical_alerts:
                    self._bulk_dismiss_alerts(critical_alerts)
        
        with col3:
            if st.button("📊 Export to CSV", help="Export current alerts to CSV"):
                self._export_alerts_csv(alerts)
        
        with col4:
            if st.button("🔄 Mark All as New", help="Reset all alerts to active status"):
                if st.session_state.get("confirm_bulk_reset"):
                    self._bulk_reset_alerts([alert["id"] for alert in alerts])
                    st.session_state.confirm_bulk_reset = False
                    st.rerun()
                else:
                    st.session_state.confirm_bulk_reset = True
                    st.warning("Click again to confirm bulk reset")
    
    def _show_alert_details(self, alert: Dict[str, Any]) -> None:
        """Show detailed alert information in a modal."""
        with st.expando(f"Alert Details - {alert['id']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Product Information:**")
                st.write(f"Name: {alert.get('product_name', 'Unknown')}")
                st.write(f"Brand: {alert.get('brand', 'Unknown')}")
                st.write(f"EAN: {alert.get('ean', 'Unknown')}")
                st.write(f"Category: {alert.get('category', 'Unknown')}")
                
                st.write("**Pricing:**")
                st.write(f"MediaMarkt Price: €{alert.get('mediamarkt_price', 0):.2f}")
                st.write(f"Amazon Price: €{alert.get('amazon_price', 0):.2f}")
                st.write(f"Profit Potential: €{alert.get('profit_potential', 0):.2f}")
                st.write(f"ROI: {alert.get('roi_percentage', 0):.1f}%")
            
            with col2:
                st.write("**Alert Information:**")
                st.write(f"Severity: {alert.get('severity', 'unknown').title()}")
                st.write(f"Status: {alert.get('status', 'unknown').title()}")
                st.write(f"Confidence: {alert.get('confidence_score', 0):.1f}%")
                st.write(f"Created: {self._format_datetime(alert.get('created_at'))}")
                
                st.write("**Competition Analysis:**")
                st.write(f"Amazon Sellers: {alert.get('amazon_seller_count', 'Unknown')}")
                st.write(f"FBA Available: {'Yes' if alert.get('fba_available') else 'No'}")
                st.write(f"Rating: {alert.get('amazon_rating', 'N/A')}")
    
    def _show_product_links(self, alert: Dict[str, Any]) -> None:
        """Show product links in an expandable section."""
        with st.expando(f"Product Links - {alert['id']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**MediaMarkt:**")
                if alert.get('mediamarkt_url'):
                    st.markdown(f"[View on MediaMarkt]({alert['mediamarkt_url']})")
                else:
                    st.write("URL not available")
            
            with col2:
                st.write("**Amazon:**")
                if alert.get('amazon_url'):
                    st.markdown(f"[View on Amazon]({alert['amazon_url']})")
                else:
                    st.write("URL not available")
    
    def _process_alert(self, alert_id: int) -> None:
        """Process a single alert."""
        try:
            result = self.data_loader.process_alert(alert_id, {"status": "processed"})
            if result:
                st.success(f"Alert {alert_id} marked as processed")
                st.rerun()
            else:
                st.error(f"Failed to process alert {alert_id}")
        except Exception as e:
            st.error(f"Error processing alert: {e}")
    
    def _dismiss_alert(self, alert_id: int) -> None:
        """Dismiss a single alert."""
        try:
            result = self.data_loader.dismiss_alert(alert_id)
            if result:
                st.success(f"Alert {alert_id} dismissed")
                st.rerun()
            else:
                st.error(f"Failed to dismiss alert {alert_id}")
        except Exception as e:
            st.error(f"Error dismissing alert: {e}")
    
    def _bulk_process_alerts(self, alert_ids: List[int]) -> None:
        """Process multiple alerts."""
        success_count = 0
        for alert_id in alert_ids:
            try:
                if self.data_loader.process_alert(alert_id, {"status": "processed"}):
                    success_count += 1
            except:
                continue
        
        st.success(f"Processed {success_count}/{len(alert_ids)} alerts")
        st.rerun()
    
    def _bulk_dismiss_alerts(self, alert_ids: List[int]) -> None:
        """Dismiss multiple alerts."""
        success_count = 0
        for alert_id in alert_ids:
            try:
                if self.data_loader.dismiss_alert(alert_id):
                    success_count += 1
            except:
                continue
        
        st.success(f"Dismissed {success_count}/{len(alert_ids)} alerts")
        st.rerun()
    
    def _bulk_reset_alerts(self, alert_ids: List[int]) -> None:
        """Reset multiple alerts to active status."""
        success_count = 0
        for alert_id in alert_ids:
            try:
                if self.data_loader.process_alert(alert_id, {"status": "active"}):
                    success_count += 1
            except:
                continue
        
        st.success(f"Reset {success_count}/{len(alert_ids)} alerts")
        st.rerun()
    
    def _export_alerts_csv(self, alerts: List[Dict[str, Any]]) -> None:
        """Export alerts to CSV."""
        if not alerts:
            st.warning("No alerts to export")
            return
        
        # Prepare data for CSV
        csv_data = []
        for alert in alerts:
            csv_data.append({
                "ID": alert["id"],
                "Product Name": alert.get("product_name", ""),
                "Brand": alert.get("brand", ""),
                "EAN": alert.get("ean", ""),
                "Category": alert.get("category", ""),
                "MediaMarkt Price": alert.get("mediamarkt_price", 0),
                "Amazon Price": alert.get("amazon_price", 0),
                "Profit Potential": alert.get("profit_potential", 0),
                "ROI Percentage": alert.get("roi_percentage", 0),
                "Severity": alert.get("severity", ""),
                "Status": alert.get("status", ""),
                "Confidence Score": alert.get("confidence_score", 0),
                "Created At": alert.get("created_at", ""),
                "MediaMarkt URL": alert.get("mediamarkt_url", ""),
                "Amazon URL": alert.get("amazon_url", "")
            })
        
        df = pd.DataFrame(csv_data)
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"arbitrage_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    def _format_datetime(self, dt_str: Optional[str]) -> str:
        """Format datetime string for display."""
        if not dt_str:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return dt_str 