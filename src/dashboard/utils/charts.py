"""Chart generation utilities for dashboard visualizations."""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta


class ChartGenerator:
    """Utility class for generating various charts and visualizations."""
    
    @staticmethod
    def create_profit_trend_chart(trend_data: List[Dict[str, Any]], title: str = "Profit Trend") -> go.Figure:
        """Create a profit trend line chart.
        
        Args:
            trend_data: List of trend data points with date and value
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not trend_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        df = pd.DataFrame(trend_data)
        
        # Ensure date column is datetime and handle properly to avoid warnings
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            # Convert to string format to avoid plotly datetime warnings
            df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
            x_data = df['date_str']
        else:
            x_data = df.index
        
        fig = go.Figure()
        
        # Main trend line
        fig.add_trace(go.Scatter(
            x=x_data,
            y=df['total_profit'] if 'total_profit' in df.columns else df['value'],
            mode='lines+markers',
            name='Total Profit',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=6),
            hovertemplate='<b>%{y:.2f}€</b><br>%{x}<extra></extra>'
        ))
        
        # Add average line
        if 'total_profit' in df.columns:
            avg_profit = df['total_profit'].mean()
            fig.add_hline(
                y=avg_profit,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Avg: €{avg_profit:.2f}"
            )
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Profit Potential (€)",
            template="plotly_white",
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_roi_distribution_chart(roi_data: List[float], title: str = "ROI Distribution") -> go.Figure:
        """Create an ROI distribution histogram.
        
        Args:
            roi_data: List of ROI percentages
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not roi_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No ROI data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=roi_data,
            nbinsx=20,
            name='ROI Distribution',
            marker_color='#2ecc71',
            opacity=0.7
        ))
        
        # Add vertical lines for key thresholds
        thresholds = [30, 50, 70]  # Critical thresholds for arbitrage
        colors = ['orange', 'red', 'darkred']
        
        for threshold, color in zip(thresholds, colors):
            fig.add_vline(
                x=threshold,
                line_dash="dash",
                line_color=color,
                annotation_text=f"{threshold}%"
            )
        
        fig.update_layout(
            title=title,
            xaxis_title="ROI Percentage (%)",
            yaxis_title="Count",
            template="plotly_white",
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_category_performance_chart(category_data: Dict[str, Any], title: str = "Category Performance") -> go.Figure:
        """Create a category performance bar chart.
        
        Args:
            category_data: Dictionary with category names as keys and metrics as values
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not category_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No category data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        categories = list(category_data.keys())
        
        # Create subplots for multiple metrics
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Products Count', 'Total Profit', 'Average ROI', 'Success Rate'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Products count
        products_count = [category_data[cat].get('products_count', 0) for cat in categories]
        fig.add_trace(
            go.Bar(x=categories, y=products_count, name='Products', marker_color='#3498db'),
            row=1, col=1
        )
        
        # Total profit
        total_profits = [category_data[cat].get('total_profit', 0) for cat in categories]
        fig.add_trace(
            go.Bar(x=categories, y=total_profits, name='Profit (€)', marker_color='#2ecc71'),
            row=1, col=2
        )
        
        # Average ROI
        avg_roi = [category_data[cat].get('average_roi', 0) for cat in categories]
        fig.add_trace(
            go.Bar(x=categories, y=avg_roi, name='ROI (%)', marker_color='#f39c12'),
            row=2, col=1
        )
        
        # Success rate
        success_rates = [category_data[cat].get('success_rate', 0) for cat in categories]
        fig.add_trace(
            go.Bar(x=categories, y=success_rates, name='Success (%)', marker_color='#e74c3c'),
            row=2, col=2
        )
        
        fig.update_layout(
            title_text=title,
            height=600,
            showlegend=False,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_price_comparison_chart(price_data: List[Dict[str, Any]], title: str = "Price Comparison") -> go.Figure:
        """Create a price comparison chart between MediaMarkt and Amazon.
        
        Args:
            price_data: List of products with MediaMarkt and Amazon prices
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not price_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No price data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        df = pd.DataFrame(price_data)
        
        fig = go.Figure()
        
        # Scatter plot of MediaMarkt vs Amazon prices
        fig.add_trace(go.Scatter(
            x=df['mediamarkt_price'],
            y=df['amazon_price'],
            mode='markers',
            marker=dict(
                size=8,
                color=df['profit_potential'] if 'profit_potential' in df.columns else 'blue',
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Profit Potential (€)")
            ),
            text=df['product_name'] if 'product_name' in df.columns else None,
            hovertemplate='<b>%{text}</b><br>' +
                         'MediaMarkt: €%{x:.2f}<br>' +
                         'Amazon: €%{y:.2f}<br>' +
                         '<extra></extra>'
        ))
        
        # Add diagonal line (equal prices)
        max_price = max(df['mediamarkt_price'].max(), df['amazon_price'].max())
        fig.add_trace(go.Scatter(
            x=[0, max_price],
            y=[0, max_price],
            mode='lines',
            line=dict(dash='dash', color='gray'),
            name='Equal Price Line',
            showlegend=False
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="MediaMarkt Price (€)",
            yaxis_title="Amazon Price (€)",
            template="plotly_white",
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_alert_timeline_chart(alert_data: List[Dict[str, Any]], title: str = "Alert Timeline") -> go.Figure:
        """Create an alert timeline chart showing alert frequency over time.
        
        Args:
            alert_data: List of alerts with timestamps
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not alert_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No alert data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        df = pd.DataFrame(alert_data)
        
        # Convert timestamps to datetime
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['date'] = df['created_at'].dt.date
        
        # Group by date and severity
        alert_counts = df.groupby(['date', 'severity']).size().reset_index(name='count')
        
        fig = go.Figure()
        
        # Different colors for different severities
        severity_colors = {
            'critical': '#e74c3c',
            'high': '#f39c12',
            'medium': '#f1c40f'
        }
        
        for severity in alert_counts['severity'].unique():
            severity_data = alert_counts[alert_counts['severity'] == severity]
            
            fig.add_trace(go.Scatter(
                x=severity_data['date'],
                y=severity_data['count'],
                mode='lines+markers',
                name=severity.title(),
                line=dict(color=severity_colors.get(severity, '#3498db')),
                stackgroup='one'
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Number of Alerts",
            template="plotly_white",
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_success_rate_gauge(success_rate: float, title: str = "Success Rate") -> go.Figure:
        """Create a gauge chart for success rate.
        
        Args:
            success_rate: Success rate percentage (0-100)
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=success_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': 75},  # Target success rate
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 75], 'color': "yellow"},
                    {'range': [75, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        
        return fig
    
    @staticmethod
    def create_top_opportunities_chart(opportunities: List[Dict[str, Any]], title: str = "Top Opportunities") -> go.Figure:
        """Create a horizontal bar chart of top arbitrage opportunities.
        
        Args:
            opportunities: List of opportunities with profit data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not opportunities:
            fig = go.Figure()
            fig.add_annotation(
                text="No opportunities available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # Sort by profit and take top 10
        sorted_opportunities = sorted(opportunities, key=lambda x: x.get('profit_potential', 0), reverse=True)[:10]
        
        product_names = [opp.get('product_name', 'Unknown')[:30] + '...' if len(opp.get('product_name', '')) > 30 
                        else opp.get('product_name', 'Unknown') for opp in sorted_opportunities]
        profits = [opp.get('profit_potential', 0) for opp in sorted_opportunities]
        roi_percentages = [opp.get('roi_percentage', 0) for opp in sorted_opportunities]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=product_names,
            x=profits,
            orientation='h',
            marker=dict(
                color=roi_percentages,
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="ROI (%)")
            ),
            text=[f"€{profit:.2f}" for profit in profits],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>' +
                         'Profit: €%{x:.2f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Profit Potential (€)",
            yaxis_title="Products",
            template="plotly_white",
            height=500,
            margin=dict(l=200)  # More space for product names
        )
        
        return fig
    
    @staticmethod
    def create_scraping_health_chart(scraping_data: List[Dict[str, Any]], title: str = "Scraping Performance") -> go.Figure:
        """Create a chart showing scraping session performance.
        
        Args:
            scraping_data: List of scraping session data
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not scraping_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No scraping data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        df = pd.DataFrame(scraping_data)
        
        if 'started_at' in df.columns:
            df['started_at'] = pd.to_datetime(df['started_at'])
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Products Scraped', 'Success Rate'),
            vertical_spacing=0.1
        )
        
        # Products scraped over time
        fig.add_trace(
            go.Scatter(
                x=df['started_at'] if 'started_at' in df.columns else df.index,
                y=df['products_scraped'] if 'products_scraped' in df.columns else [0] * len(df),
                mode='lines+markers',
                name='Products Scraped',
                line=dict(color='#3498db')
            ),
            row=1, col=1
        )
        
        # Success rate over time
        if 'success_rate' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['started_at'] if 'started_at' in df.columns else df.index,
                    y=df['success_rate'],
                    mode='lines+markers',
                    name='Success Rate (%)',
                    line=dict(color='#2ecc71')
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title_text=title,
            height=500,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_brand_popularity_pie(brand_data: Dict[str, int], title: str = "Brand Distribution") -> go.Figure:
        """Create a pie chart showing brand popularity.
        
        Args:
            brand_data: Dictionary with brand names and product counts
            title: Chart title
            
        Returns:
            Plotly figure object
        """
        if not brand_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No brand data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # Take top 8 brands and group rest as "Others"
        sorted_brands = sorted(brand_data.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_brands) > 8:
            top_brands = sorted_brands[:8]
            others_count = sum(count for _, count in sorted_brands[8:])
            if others_count > 0:
                top_brands.append(("Others", others_count))
        else:
            top_brands = sorted_brands
        
        labels, values = zip(*top_brands) if top_brands else ([], [])
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.3,
            hovertemplate='<b>%{label}</b><br>' +
                         'Products: %{value}<br>' +
                         'Percentage: %{percent}<br>' +
                         '<extra></extra>'
        )])
        
        fig.update_layout(
            title=title,
            height=400,
            template="plotly_white"
        )
        
        return fig 
    
    @staticmethod
    def create_profit_distribution_chart(distribution_data: Dict[str, Any], title: str = "Profit Distribution") -> go.Figure:
        """Create profit distribution histogram chart."""
        profit_ranges = distribution_data.get("ranges", [])
        counts = distribution_data.get("counts", [])
        
        fig = go.Figure(data=[go.Histogram(
            x=[f"€{r['min']}-{r['max']}" for r in profit_ranges],
            y=counts,
            nbinsx=len(profit_ranges),
            name="Distribution",
            marker_color="lightseagreen",
            opacity=0.7
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Profit Range",
            yaxis_title="Number of Opportunities",
            height=400,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_roi_by_category_chart(roi_data: List[Dict[str, Any]], title: str = "ROI by Category") -> go.Figure:
        """Create ROI by category bar chart."""
        categories = [item['category'] for item in roi_data]
        roi_values = [item['avg_roi'] for item in roi_data]
        
        fig = go.Figure(data=[go.Bar(
            x=categories,
            y=roi_values,
            marker_color="mediumturquoise",
            text=[f"{roi:.1f}%" for roi in roi_values],
            textposition='auto'
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Category",
            yaxis_title="Average ROI (%)",
            height=400,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_multi_metric_trend_chart(time_series_data: List[Dict[str, Any]], title: str = "Multi-Metric Trends") -> go.Figure:
        """Create multi-metric time series chart."""
        dates = [item['date'] for item in time_series_data]
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Opportunities', 'Profit Potential', 'Success Rate', 'Average ROI'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Opportunities
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[item['opportunities'] for item in time_series_data],
                mode='lines+markers',
                name='Opportunities',
                line=dict(color='royalblue')
            ),
            row=1, col=1
        )
        
        # Profit Potential
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[item['profit_potential'] for item in time_series_data],
                mode='lines+markers',
                name='Profit Potential',
                line=dict(color='lightseagreen')
            ),
            row=1, col=2
        )
        
        # Success Rate
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[item['success_rate'] for item in time_series_data],
                mode='lines+markers',
                name='Success Rate',
                line=dict(color='orange')
            ),
            row=2, col=1
        )
        
        # Average ROI
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[item['avg_roi'] for item in time_series_data],
                mode='lines+markers',
                name='Average ROI',
                line=dict(color='crimson')
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title=title,
            height=600,
            template="plotly_white",
            showlegend=False
        )
        
        return fig
    
    @staticmethod
    def create_hourly_pattern_chart(hourly_data: List[Dict[str, Any]], title: str = "Hourly Patterns") -> go.Figure:
        """Create hourly activity pattern chart."""
        hours = [item['hour'] for item in hourly_data]
        activities = [item['activity_count'] for item in hourly_data]
        
        fig = go.Figure(data=[go.Bar(
            x=hours,
            y=activities,
            marker_color="lightcoral",
            text=activities,
            textposition='auto'
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Hour of Day",
            yaxis_title="Activity Count",
            height=400,
            template="plotly_white",
            xaxis=dict(tickmode='linear', tick0=0, dtick=2)
        )
        
        return fig
    
    @staticmethod
    def create_weekly_pattern_chart(weekly_data: List[Dict[str, Any]], title: str = "Weekly Patterns") -> go.Figure:
        """Create weekly activity pattern chart."""
        days = [item['day'] for item in weekly_data]
        activities = [item['activity_count'] for item in weekly_data]
        
        fig = go.Figure(data=[go.Bar(
            x=days,
            y=activities,
            marker_color="mediumpurple",
            text=activities,
            textposition='auto'
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Day of Week",
            yaxis_title="Activity Count",
            height=400,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_category_distribution_chart(distribution_data: Dict[str, int], title: str = "Category Distribution") -> go.Figure:
        """Create category distribution pie chart."""
        categories = list(distribution_data.keys())
        values = list(distribution_data.values())
        
        fig = go.Figure(data=[go.Pie(
            labels=categories,
            values=values,
            hole=0.3,
            hovertemplate='<b>%{label}</b><br>' +
                         'Count: %{value}<br>' +
                         'Percentage: %{percent}<br>' +
                         '<extra></extra>'
        )])
        
        fig.update_layout(
            title=title,
            height=400,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_category_profit_chart(profit_data: List[Dict[str, Any]], title: str = "Profit by Category") -> go.Figure:
        """Create profit by category bar chart."""
        categories = [item['category'] for item in profit_data]
        profits = [item['total_profit'] for item in profit_data]
        
        fig = go.Figure(data=[go.Bar(
            x=categories,
            y=profits,
            marker_color="gold",
            text=[f"€{profit:,.0f}" for profit in profits],
            textposition='auto'
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Category",
            yaxis_title="Total Profit (€)",
            height=400,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_marketplace_performance_chart(marketplace_data: List[Dict[str, Any]], title: str = "Marketplace Performance") -> go.Figure:
        """Create marketplace performance comparison chart."""
        marketplaces = [item['marketplace'] for item in marketplace_data]
        opportunities = [item['opportunities'] for item in marketplace_data]
        avg_profits = [item['avg_profit'] for item in marketplace_data]
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Opportunities', 'Average Profit'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Opportunities
        fig.add_trace(
            go.Bar(
                x=marketplaces,
                y=opportunities,
                name='Opportunities',
                marker_color='royalblue',
                text=opportunities,
                textposition='auto'
            ),
            row=1, col=1
        )
        
        # Average Profit
        fig.add_trace(
            go.Bar(
                x=marketplaces,
                y=avg_profits,
                name='Avg Profit',
                marker_color='lightseagreen',
                text=[f"€{profit:.0f}" for profit in avg_profits],
                textposition='auto'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title=title,
            height=400,
            template="plotly_white",
            showlegend=False
        )
        
        return fig
    
    @staticmethod
    def create_regional_trends_chart(regional_data: List[Dict[str, Any]], title: str = "Regional Trends") -> go.Figure:
        """Create regional trends line chart."""
        dates = sorted(set(item['date'] for item in regional_data))
        regions = sorted(set(item['region'] for item in regional_data))
        
        fig = go.Figure()
        
        colors = ['royalblue', 'lightseagreen', 'orange', 'crimson', 'mediumpurple']
        
        for i, region in enumerate(regions):
            region_data = [item for item in regional_data if item['region'] == region]
            region_dates = [item['date'] for item in region_data]
            region_values = [item['value'] for item in region_data]
            
            fig.add_trace(go.Scatter(
                x=region_dates,
                y=region_values,
                mode='lines+markers',
                name=region,
                line=dict(color=colors[i % len(colors)])
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Value",
            height=400,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_price_gap_analysis_chart(price_gap_data: List[Dict[str, Any]], title: str = "Price Gap Analysis") -> go.Figure:
        """Create price gap analysis scatter chart."""
        mm_prices = [item['mediamarkt_price'] for item in price_gap_data]
        amazon_prices = [item['amazon_price'] for item in price_gap_data]
        products = [item['product_name'][:30] + '...' if len(item['product_name']) > 30 else item['product_name'] 
                   for item in price_gap_data]
        
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=mm_prices,
            y=amazon_prices,
            mode='markers',
            marker=dict(
                size=10,
                color='lightseagreen',
                opacity=0.7
            ),
            text=products,
            hovertemplate='<b>%{text}</b><br>' +
                         'MediaMarkt: €%{x:.2f}<br>' +
                         'Amazon: €%{y:.2f}<br>' +
                         '<extra></extra>',
            name="Products"
        ))
        
        # Add diagonal line for reference
        max_price = max(max(mm_prices, default=0), max(amazon_prices, default=0))
        fig.add_trace(go.Scatter(
            x=[0, max_price],
            y=[0, max_price],
            mode='lines',
            line=dict(dash='dash', color='gray'),
            name="Equal Price Line"
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="MediaMarkt Price (€)",
            yaxis_title="Amazon Price (€)",
            height=500,
            template="plotly_white"
        )
        
        return fig
    
    @staticmethod
    def create_market_saturation_chart(saturation_data: Dict[str, float], title: str = "Market Saturation") -> go.Figure:
        """Create market saturation gauge chart."""
        categories = list(saturation_data.keys())
        saturation_levels = list(saturation_data.values())
        
        fig = go.Figure(data=[go.Bar(
            x=categories,
            y=saturation_levels,
            marker_color=['red' if level > 80 else 'orange' if level > 60 else 'green' for level in saturation_levels],
            text=[f"{level:.1f}%" for level in saturation_levels],
            textposition='auto'
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Category",
            yaxis_title="Saturation Level (%)",
            height=400,
            template="plotly_white",
            yaxis=dict(range=[0, 100])
        )
        
        return fig
    
    @staticmethod
    def create_opportunity_score_chart(score_data: List[Dict[str, Any]], title: str = "Opportunity Score Distribution") -> go.Figure:
        """Create opportunity score distribution chart."""
        scores = [item['score'] for item in score_data]
        counts = [item['count'] for item in score_data]
        
        fig = go.Figure(data=[go.Bar(
            x=scores,
            y=counts,
            marker_color="mediumseagreen",
            text=counts,
            textposition='auto'
        )])
        
        fig.update_layout(
            title=title,
            xaxis_title="Opportunity Score",
            yaxis_title="Number of Opportunities",
            height=400,
            template="plotly_white"
        )
        
        return fig 