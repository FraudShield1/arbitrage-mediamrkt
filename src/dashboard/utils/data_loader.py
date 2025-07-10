"""
Data Loading Utilities

Functions to fetch data from API endpoints, handle pagination, 
and cache responses for the Streamlit dashboard.
"""

import requests
import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """Data loader for fetching data from the arbitrage API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the data loader.
        
        Args:
            base_url: Base URL for the API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a GET request to the API.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            Response data or None if error
        """
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_system_stats(_self) -> Optional[Dict[str, Any]]:
        """
        Get system statistics.
        
        Returns:
            System stats dictionary or None if error
        """
        return _self._make_request("/stats")
    
    @st.cache_data(ttl=300)
    def get_trends(_self, days: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get system trends over time.
        
        Args:
            days: Number of days for trend analysis
            
        Returns:
            Trends data or None if error
        """
        return _self._make_request("/stats/trends", {"days": days})
    
    @st.cache_data(ttl=300)
    def get_category_stats(_self) -> Optional[Dict[str, Any]]:
        """
        Get category-wise statistics.
        
        Returns:
            Category stats or None if error
        """
        return _self._make_request("/stats/categories")
    
    @st.cache_data(ttl=300)
    def get_scraping_stats(_self) -> Optional[Dict[str, Any]]:
        """
        Get scraping session statistics.
        
        Returns:
            Scraping stats or None if error
        """
        return _self._make_request("/stats/scraping")
    
    @st.cache_data(ttl=60)  # Cache alerts for 1 minute (more dynamic)
    def get_alerts(_self, 
                   page: int = 1, 
                   size: int = 20,
                   status: Optional[str] = None,
                   severity: Optional[str] = None,
                   min_profit: Optional[float] = None,
                   category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get paginated alerts with filtering.
        
        Args:
            page: Page number
            size: Items per page
            status: Filter by status
            severity: Filter by severity
            min_profit: Minimum profit filter
            category: Filter by category
            
        Returns:
            Alerts data or None if error
        """
        params = {"page": page, "size": size}
        
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        if min_profit is not None:
            params["min_profit"] = min_profit
        if category:
            params["category"] = category
            
        return _self._make_request("/alerts", params)
    
    @st.cache_data(ttl=60)
    def get_alert_stats(_self, days: int = 7) -> Optional[Dict[str, Any]]:
        """
        Get alert statistics summary.
        
        Args:
            days: Number of days for statistics
            
        Returns:
            Alert stats or None if error
        """
        return _self._make_request("/alerts/stats/summary", {"days": days})
    
    @st.cache_data(ttl=60)
    def get_top_opportunities(_self, 
                             limit: int = 10,
                             min_profit: float = 50.0,
                             status: str = "pending") -> Optional[Dict[str, Any]]:
        """
        Get top arbitrage opportunities.
        
        Args:
            limit: Number of opportunities to return
            min_profit: Minimum profit threshold
            status: Alert status filter
            
        Returns:
            Top opportunities or None if error
        """
        params = {
            "limit": limit,
            "min_profit": min_profit,
            "status": status
        }
        return _self._make_request("/alerts/top-opportunities", params)
    
    @st.cache_data(ttl=300)
    def get_products(_self,
                    page: int = 1,
                    size: int = 20,
                    category: Optional[str] = None,
                    brand: Optional[str] = None,
                    min_price: Optional[float] = None,
                    max_price: Optional[float] = None,
                    min_discount: Optional[float] = None,
                    in_stock: Optional[bool] = None,
                    has_asin: Optional[bool] = None,
                    search: Optional[str] = None,
                    sort_by: str = "created_at",
                    sort_order: str = "desc") -> Optional[Dict[str, Any]]:
        """
        Get paginated products with filtering.
        
        Args:
            page: Page number
            size: Items per page
            category: Filter by category
            brand: Filter by brand
            min_price: Minimum price filter
            max_price: Maximum price filter
            min_discount: Minimum discount percentage
            in_stock: Filter by stock availability
            has_asin: Filter products with/without ASIN
            search: Search term
            sort_by: Sort field
            sort_order: Sort direction
            
        Returns:
            Products data or None if error
        """
        params = {
            "page": page,
            "size": size,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        if category:
            params["category"] = category
        if brand:
            params["brand"] = brand
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price
        if min_discount is not None:
            params["min_discount"] = min_discount
        if in_stock is not None:
            params["in_stock"] = in_stock
        if has_asin is not None:
            params["has_asin"] = has_asin
        if search:
            params["search"] = search
            
        return _self._make_request("/products", params)
    
    def get_product(_self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific product by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product data or None if error
        """
        return _self._make_request(f"/products/{product_id}")
    
    def get_product_matches(_self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Get ASIN matches for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product matches or None if error
        """
        return _self._make_request(f"/products/{product_id}/matches")
    
    def process_alert(_self, alert_id: int, status: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Process an alert (update status).
        
        Args:
            alert_id: Alert ID
            status: New status
            notes: Optional notes
            
        Returns:
            Updated alert data or None if error
        """
        try:
            url = f"{self.base_url}/alerts/{alert_id}/process"
            data = {"status": status}
            if notes:
                data["notes"] = notes
                
            response = self.session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Alert processing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def dismiss_alert(_self, alert_id: int, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Dismiss an alert.
        
        Args:
            alert_id: Alert ID
            notes: Optional dismissal notes
            
        Returns:
            Dismissal confirmation or None if error
        """
        try:
            url = f"{self.base_url}/alerts/{alert_id}/dismiss"
            params = {}
            if notes:
                params["notes"] = notes
                
            response = self.session.post(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Alert dismissal failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached data."""
        st.cache_data.clear()
    
    def health_check(self) -> bool:
        """
        Check if the API is healthy.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url.replace('/api/v1', '')}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    # Analytics methods
    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def get_analytics_data(self, start_date, end_date) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive analytics data for the specified time range.
        
        Args:
            start_date: Start date for analytics
            end_date: End date for analytics
            
        Returns:
            Analytics data dictionary or None if error
        """
        try:
            params = {
                "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
                "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date)
            }
            
            # Get overview metrics
            overview_metrics = self._make_request("/stats/analytics/overview", params)
            
            # Get profit analytics
            profit_analytics = self._make_request("/stats/analytics/profit", params)
            
            # Get trend analysis
            trend_analysis = self._make_request("/stats/analytics/trends", params)
            
            # Get category performance
            category_performance = self._make_request("/stats/analytics/categories", params)
            
            # Get geographic analysis
            geographic_analysis = self._make_request("/stats/analytics/geographic", params)
            
            # Get competitive analysis
            competitive_analysis = self._make_request("/stats/analytics/competitive", params)
            
            return {
                "overview_metrics": overview_metrics,
                "profit_analytics": profit_analytics,
                "trend_analysis": trend_analysis,
                "category_performance": category_performance,
                "geographic_analysis": geographic_analysis,
                "competitive_analysis": competitive_analysis
            }
        except Exception as e:
            logger.error(f"Analytics data loading failed: {e}")
            return None
    
    # Settings methods
    @st.cache_data(ttl=300)
    def get_settings(self) -> Optional[Dict[str, Any]]:
        """
        Get current system settings.
        
        Returns:
            Settings dictionary or None if error
        """
        try:
            return self._make_request("/settings")
        except Exception as e:
            logger.error(f"Settings loading failed: {e}")
            return None
    
    def update_settings(self, category: str, settings: Dict[str, Any]) -> bool:
        """
        Update settings for a specific category.
        
        Args:
            category: Settings category (e.g., 'scraping', 'matching')
            settings: New settings for the category
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/settings/{category}"
            response = self.session.put(url, json=settings, timeout=self.timeout)
            response.raise_for_status()
            
            # Clear settings cache
            self.get_settings.clear()
            
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Settings update failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def export_system_data(self) -> Optional[Dict[str, Any]]:
        """
        Export system data for backup.
        
        Returns:
            System data dictionary or None if error
        """
        try:
            return self._make_request("/export/system")
        except Exception as e:
            logger.error(f"System data export failed: {e}")
            return None
    
    def import_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Import settings from backup.
        
        Args:
            settings: Settings dictionary to import
            
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/import/settings"
            response = self.session.post(url, json=settings, timeout=self.timeout)
            response.raise_for_status()
            
            # Clear all caches
            st.cache_data.clear()
            
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Settings import failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def reset_settings_to_defaults(self) -> bool:
        """
        Reset all settings to default values.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            url = f"{self.base_url}/settings/reset"
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Clear all caches
            st.cache_data.clear()
            
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Settings reset failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False 