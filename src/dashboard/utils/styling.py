"""
Styling Utilities for Professional Dashboard

Custom CSS, themes, and UI styling for the arbitrage dashboard.
"""

import streamlit as st
from typing import Dict, Any
import json
from pathlib import Path

def apply_custom_styling():
    """Apply custom CSS styling to the dashboard."""
    
    st.markdown("""
    <style>
    /* Global Styles */
    .main {
        padding-top: 1rem;
    }
    
    /* Header Styling */
    .dashboard-header {
        background: linear-gradient(90deg, #1f77b4, #17a2b8);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        color: white;
    }
    
    /* Status Indicators */
    .status-indicator {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: 10px;
    }
    
    .status-live {
        background-color: #28a745;
        color: white;
    }
    
    .status-warning {
        background-color: #ffc107;
        color: #212529;
    }
    
    .status-error {
        background-color: #dc3545;
        color: white;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        color: #6c757d;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-delta-positive {
        color: #28a745;
        font-size: 0.8rem;
    }
    
    .metric-delta-negative {
        color: #dc3545;
        font-size: 0.8rem;
    }
    
    /* Navigation Styles */
    .nav-item {
        padding: 0.5rem 1rem;
        margin-bottom: 0.25rem;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .nav-item:hover {
        background-color: #f8f9fa;
        transform: translateX(4px);
    }
    
    .nav-item.active {
        background-color: #1f77b4;
        color: white;
    }
    
    /* Alert Styles */
    .alert-card {
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 1rem;
        border-left: 4px solid;
    }
    
    .alert-high {
        background-color: #fff5f5;
        border-left-color: #dc3545;
    }
    
    .alert-medium {
        background-color: #fff8e1;
        border-left-color: #ffc107;
    }
    
    .alert-low {
        background-color: #f0f8ff;
        border-left-color: #17a2b8;
    }
    
    /* Product Cards */
    .product-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    
    .product-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }
    
    .product-title {
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .product-price {
        font-size: 1.25rem;
        font-weight: bold;
        color: #e74c3c;
    }
    
    .product-discount {
        background-color: #e74c3c;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    
    /* Table Styles */
    .dataframe {
        border: none !important;
    }
    
    .dataframe th {
        background-color: #f8f9fa !important;
        color: #495057 !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        font-size: 0.8rem !important;
        letter-spacing: 1px !important;
        padding: 1rem 0.5rem !important;
    }
    
    .dataframe td {
        padding: 0.75rem 0.5rem !important;
        border-bottom: 1px solid #dee2e6 !important;
    }
    
    .dataframe tr:hover {
        background-color: #f8f9fa !important;
    }
    
    /* Footer Styles */
    .dashboard-footer {
        margin-top: 3rem;
        padding: 1rem;
        text-align: center;
        color: #6c757d;
        font-size: 0.85rem;
        border-top: 1px solid #dee2e6;
    }
    
    /* Loading Spinner */
    .loading-spinner {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 2rem;
    }
    
    /* Chart Container */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Form Styles */
    .form-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    .form-section h3 {
        color: #495057;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #dee2e6;
    }
    
    /* Button Styles */
    .stButton > button {
        background: linear-gradient(90deg, #1f77b4, #17a2b8);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Sidebar Styles */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Hide Streamlit Menu */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    </style>
    """, unsafe_allow_html=True)

def load_theme_config() -> Dict[str, Any]:
    """
    Load theme configuration from config file.
    
    Returns:
        Theme configuration dictionary
    """
    try:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "theme.json"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    
    # Default theme configuration
    return {
        "primary_color": "#1f77b4",
        "secondary_color": "#17a2b8",
        "success_color": "#28a745",
        "warning_color": "#ffc107",
        "danger_color": "#dc3545",
        "info_color": "#17a2b8",
        "light_color": "#f8f9fa",
        "dark_color": "#343a40",
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "border_radius": "8px",
        "box_shadow": "0 2px 4px rgba(0,0,0,0.1)"
    }

def create_metric_card(title: str, value: str, delta: str = None, delta_type: str = "positive") -> str:
    """
    Create HTML for a metric card.
    
    Args:
        title: Metric title
        value: Metric value
        delta: Change value
        delta_type: Type of change (positive/negative)
        
    Returns:
        HTML string for metric card
    """
    delta_class = f"metric-delta-{delta_type}" if delta else ""
    delta_html = f'<div class="{delta_class}">{delta}</div>' if delta else ""
    
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
        {delta_html}
    </div>
    """

def create_status_badge(status: str, text: str) -> str:
    """
    Create HTML for a status badge.
    
    Args:
        status: Status type (live/warning/error)
        text: Badge text
        
    Returns:
        HTML string for status badge
    """
    return f'<span class="status-indicator status-{status}">{text}</span>'

def create_alert_card(title: str, content: str, alert_type: str = "medium") -> str:
    """
    Create HTML for an alert card.
    
    Args:
        title: Alert title
        content: Alert content
        alert_type: Alert severity (high/medium/low)
        
    Returns:
        HTML string for alert card
    """
    return f"""
    <div class="alert-card alert-{alert_type}">
        <h4>{title}</h4>
        <p>{content}</p>
    </div>
    """ 