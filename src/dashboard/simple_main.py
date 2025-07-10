# -*- coding: utf-8 -*-
"""
Simplified Arbitrage Dashboard - Basic Functionality Focus

A clean, working dashboard that prioritizes functionality over styling.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit
st.set_page_config(
    page_title="Arbitrage Monitor",
    page_icon="💰",
    layout="wide"
)

class SimpleArbitrageDashboard:
    """Simplified dashboard focusing on core functionality."""
    
    def __init__(self):
        self.db = None
        self.connect_database()
    
    def connect_database(self):
        """Connect to MongoDB."""
        try:
            mongodb_uri = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
            database_name = os.getenv('MONGODB_DATABASE', 'arbitrage_tool')
            
            if 'mongodb+srv://' in mongodb_uri:
                client = MongoClient(
                    mongodb_uri,
                    tls=True,
                    tlsAllowInvalidCertificates=True,
                    tlsAllowInvalidHostnames=True,
                    retryWrites=True,
                    w='majority',
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000
                )
            else:
                client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            
            self.db = client[database_name]
            # Test connection
            self.db.command("ping")
            st.success("Database connected successfully!")
            logger.info("MongoDB connected successfully")
            
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            logger.error(f"Database connection failed: {e}")
            self.db = None
    
    def get_stats(self):
        """Get basic system statistics."""
        if self.db is None:
            return None
        
        try:
            stats = {}
            
            # Products count and analysis
            products_collection = self.db.products
            stats['total_products'] = products_collection.count_documents({})
            
            # Count products with discounts
            stats['discounted_products'] = products_collection.count_documents({
                "has_discount": "True"
            })
            
            # Count by availability
            stats['in_stock_products'] = products_collection.count_documents({
                "availability": "in_stock"
            })
            
            # Alerts count and analysis
            alerts_collection = self.db.price_alerts
            stats['total_alerts'] = alerts_collection.count_documents({})
            stats['active_alerts'] = alerts_collection.count_documents({"status": "active"})
            
            # Calculate total profit potential
            total_profit = 0
            for alert in alerts_collection.find({"status": "active"}, {"profit_amount": 1}):
                try:
                    profit = float(alert.get('profit_amount', 0))
                    total_profit += profit
                except:
                    pass
            stats['total_profit_potential'] = total_profit
            
            # If no data, create sample
            if stats['total_products'] == 0 and stats['total_alerts'] == 0:
                stats = {
                    'total_products': 150,
                    'total_alerts': 25,
                    'active_alerts': 12,
                    'data_status': 'sample'
                }
            else:
                stats['data_status'] = 'real'
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return None
    
    def get_products(self, limit=20):
        """Get product list."""
        if self.db is None:
            return []
        
        try:
            products_collection = self.db.products
            products = list(products_collection.find({}).limit(limit))
            
            # Only create sample data if absolutely no products exist
            # Don't check if products is empty, check if we got real data from DB
            if len(products) == 0:
                sample_products = []
                for i in range(10):
                    sample_products.append({
                        'title': f'Sample Product {i+1}',
                        'price': 99.99 + i * 10,
                        'original_price': 109.99 + i * 10,
                        'discount_percentage': 10,
                        'category': 'Electronics',
                        'availability': 'in_stock',
                        'data_status': 'sample'
                    })
                return sample_products
            
            # Mark real products as real data
            for product in products:
                product['data_status'] = 'real'
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []
    
    def get_alerts(self, limit=20):
        """Get alerts list."""
        if self.db is None:
            return []
        
        try:
            alerts_collection = self.db.price_alerts
            alerts = list(alerts_collection.find({}).limit(limit))
            
            # Only create sample data if absolutely no alerts exist
            if len(alerts) == 0:
                sample_alerts = []
                for i in range(5):
                    sample_alerts.append({
                        'product_title': f'Alert Product {i+1}',
                        'profit_amount': 15.00 + i * 5,
                        'status': 'active' if i < 3 else 'inactive',
                        'severity': 'high' if i < 2 else 'medium',
                        'created_at': datetime.now() - timedelta(hours=i),
                        'data_status': 'sample'
                    })
                return sample_alerts
            
            # Mark real alerts as real data
            for alert in alerts:
                alert['data_status'] = 'real'
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def render_overview(self):
        """Render overview page."""
        st.header("Overview")
        
        # Get stats
        stats = self.get_stats()
        
        if stats:
            # Display metrics in rows
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Products", stats.get('total_products', 0))
            
            with col2:
                st.metric("Products with Discounts", stats.get('discounted_products', 0))
            
            with col3:
                st.metric("In Stock Products", stats.get('in_stock_products', 0))
            
            with col4:
                if stats.get('data_status') == 'sample':
                    st.info("Sample Data")
                else:
                    st.success("Live Data")
            
            # Second row of metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Alerts", stats.get('total_alerts', 0))
            
            with col2:
                st.metric("Active Alerts", stats.get('active_alerts', 0))
            
            with col3:
                profit_potential = stats.get('total_profit_potential', 0)
                st.metric("Profit Potential", f"€{profit_potential:.2f}")
            
            with col4:
                discount_rate = (stats.get('discounted_products', 0) / max(stats.get('total_products', 1), 1)) * 100
                st.metric("Discount Rate", f"{discount_rate:.1f}%")
            
            # Show latest data info
            st.subheader("System Status")
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"✅ Database Connected")
                st.info(f"📊 {stats.get('total_products', 0)} products in catalog")
                st.info(f"🚨 {stats.get('active_alerts', 0)} active opportunities")
            
            with col2:
                if stats.get('data_status') == 'real':
                    st.success("✅ Showing real data from MediaMarkt")
                else:
                    st.warning("⚠️ Showing sample data")
                
                if profit_potential > 0:
                    st.success(f"💰 €{profit_potential:.2f} total profit potential identified")
                
        else:
            st.error("Unable to load system statistics")
    
    def render_products(self):
        """Render products page."""
        st.header("Products")
        
        products = self.get_products()
        
        if products:
            # Show data status
            is_real_data = products[0].get('data_status') == 'real'
            if is_real_data:
                st.success("✅ Showing real data from MediaMarkt database")
            else:
                st.info("ℹ️ Showing sample data - no real products found")
            
            # Convert to DataFrame for display
            df_data = []
            for product in products:
                # Calculate profit if we have both prices
                price = 0
                original_price = 0
                
                try:
                    price = float(product.get('price', 0)) if product.get('price') else 0
                except:
                    price = 0
                
                try:
                    original_price = float(product.get('original_price', 0)) if product.get('original_price') else 0
                except:
                    original_price = 0
                
                profit = original_price - price if original_price > price else 0
                
                # Handle URL display
                url = product.get('url', 'No URL')
                url_display = url if url and url != 'No URL' else 'No URL Available'
                
                df_data.append({
                    'Product Name': product.get('title', 'Unknown Product'),
                    'Current Price': f"€{price:.2f}",
                    'Original Price': f"€{original_price:.2f}",
                    'Discount': f"{product.get('discount_percentage', '0')}%",
                    'Profit Potential': f"€{profit:.2f}",
                    'Brand': product.get('brand', 'Unknown') if product.get('brand') != 'None' else 'Unknown',
                    'Category': product.get('category', 'Unknown'),
                    'Status': product.get('availability', 'Unknown'),
                    'Source': product.get('source', 'MediaMarkt'),
                    'Has URL': 'Yes' if url and url != 'No URL' and not url.startswith('mock') else 'No'
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Show clickable links for products
            st.subheader("Product Links (First 10 items)")
            
            valid_url_count = 0
            for i, product in enumerate(products[:10]):
                url = product.get('url', '')
                title = product.get('title', 'Unknown Product')
                
                if url and url != 'No URL' and not url.startswith('mock'):
                    # Valid URL
                    valid_url_count += 1
                    st.markdown(f"**{title}**")
                    st.markdown(f"[🔗 View on MediaMarkt]({url})")
                    st.markdown(f"Price: €{product.get('price', 0)} | Original: €{product.get('original_price', 0)} | Discount: {product.get('discount_percentage', 0)}%")
                    st.markdown("---")
                else:
                    # No valid URL
                    st.markdown(f"**{title}**")
                    st.markdown("🚫 No valid URL available")
                    st.markdown(f"Price: €{product.get('price', 0)} | Original: €{product.get('original_price', 0)} | Discount: {product.get('discount_percentage', 0)}%")
                    st.markdown("---")
            
            # Show URL statistics
            total_products = len(products[:10])
            invalid_url_count = total_products - valid_url_count
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Products Shown", total_products)
            with col2:
                st.metric("Valid URLs", valid_url_count)
            with col3:
                st.metric("Missing/Invalid URLs", invalid_url_count)
            
        else:
            st.warning("No products found")
    
    def render_alerts(self):
        """Render alerts page."""
        st.header("Alerts")
        
        alerts = self.get_alerts()
        
        if alerts:
            # Show data status
            is_real_data = alerts[0].get('data_status') == 'real'
            if is_real_data:
                st.success("✅ Showing real alert data from database")
            else:
                st.info("ℹ️ Showing sample data - no real alerts found")
            
            # Convert to DataFrame for display
            df_data = []
            for alert in alerts:
                # Parse prices as floats for proper display
                mediamarkt_price = 0
                amazon_price = 0
                profit_amount = 0
                profit_margin = 0
                
                try:
                    mediamarkt_price = float(alert.get('mediamarkt_price', 0)) if alert.get('mediamarkt_price') else 0
                except:
                    pass
                
                try:
                    amazon_price = float(alert.get('amazon_price', 0)) if alert.get('amazon_price') else 0
                except:
                    pass
                
                try:
                    profit_amount = float(alert.get('profit_amount', 0)) if alert.get('profit_amount') else 0
                except:
                    pass
                
                try:
                    profit_margin = float(alert.get('profit_margin', 0)) if alert.get('profit_margin') else 0
                except:
                    pass
                
                # Parse created_at
                created_at = alert.get('created_at', datetime.now())
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        created_at = datetime.now()
                
                df_data.append({
                    'Product': alert.get('product_title', 'Unknown Product'),
                    'ASIN': alert.get('product_asin', 'Unknown'),
                    'MediaMarkt Price': f"€{mediamarkt_price:.2f}",
                    'Amazon Price': f"€{amazon_price:.2f}",
                    'Profit Amount': f"€{profit_amount:.2f}",
                    'Profit Margin': f"{profit_margin:.1f}%",
                    'Alert Type': alert.get('alert_type', 'Unknown'),
                    'Status': alert.get('status', 'Unknown'),
                    'Created': created_at.strftime('%Y-%m-%d %H:%M')
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Show summary stats
            st.subheader("Alert Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_profit = sum(float(alert.get('profit_amount', 0)) for alert in alerts if alert.get('profit_amount'))
                st.metric("Total Profit Potential", f"€{total_profit:.2f}")
            
            with col2:
                active_count = len([a for a in alerts if a.get('status') == 'active'])
                st.metric("Active Alerts", active_count)
            
            with col3:
                avg_margin = sum(float(alert.get('profit_margin', 0)) for alert in alerts if alert.get('profit_margin')) / len(alerts) if alerts else 0
                st.metric("Avg Profit Margin", f"{avg_margin:.1f}%")
            
        else:
            st.warning("No alerts found")
    
    def render_analytics(self):
        """Render analytics page."""
        st.header("Analytics")
        
        # Basic chart example
        if self.db is not None:
            try:
                # Get products and alerts for analysis
                products = self.get_products(100)
                alerts = self.get_alerts(50)
                
                if products:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Price Distribution")
                        prices = []
                        for product in products:
                            price = product.get('price')
                            if price and price != 'None':
                                try:
                                    prices.append(float(price))
                                except:
                                    pass
                        
                        if prices:
                            price_df = pd.DataFrame({'Price': prices[:50]})
                            st.bar_chart(price_df)
                        else:
                            st.info("No price data available")
                    
                    with col2:
                        st.subheader("Discount Distribution")
                        discounts = []
                        for product in products:
                            discount = product.get('discount_percentage')
                            if discount and discount != 'None':
                                try:
                                    discounts.append(float(discount))
                                except:
                                    pass
                        
                        if discounts:
                            discount_df = pd.DataFrame({'Discount %': discounts[:50]})
                            st.bar_chart(discount_df)
                        else:
                            st.info("No discount data available")
                    
                    # Category breakdown
                    st.subheader("Products by Category")
                    categories = {}
                    for product in products:
                        category = product.get('category', 'Unknown')
                        categories[category] = categories.get(category, 0) + 1
                    
                    if categories:
                        category_df = pd.DataFrame(list(categories.items()), columns=['Category', 'Count'])
                        st.bar_chart(category_df.set_index('Category'))
                
                if alerts:
                    st.subheader("Profit Opportunities")
                    profit_amounts = []
                    for alert in alerts:
                        profit = alert.get('profit_amount')
                        if profit:
                            try:
                                profit_amounts.append(float(profit))
                            except:
                                pass
                    
                    if profit_amounts:
                        profit_df = pd.DataFrame({'Profit Amount': profit_amounts})
                        st.line_chart(profit_df)
                        
                        # Show top opportunities
                        st.subheader("Top Profit Opportunities")
                        top_alerts = sorted(alerts, key=lambda x: float(x.get('profit_amount', 0)), reverse=True)[:5]
                        for alert in top_alerts:
                            st.write(f"**{alert.get('product_title', 'Unknown')}**: €{alert.get('profit_amount', 0)} profit ({alert.get('profit_margin', 0)}% margin)")
                    else:
                        st.info("No profit data available")
                
            except Exception as e:
                st.error(f"Error loading analytics: {e}")
                st.write("Error details:", str(e))
        else:
            st.error("Database not connected")
    
    def run(self):
        """Main dashboard runner."""
        st.title("Arbitrage Monitor")
        
        # Simple navigation
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Products", "Alerts", "Analytics"])
        
        with tab1:
            self.render_overview()
        
        with tab2:
            self.render_products()
        
        with tab3:
            self.render_alerts()
        
        with tab4:
            self.render_analytics()

# Run the dashboard
if __name__ == "__main__":
    dashboard = SimpleArbitrageDashboard()
    dashboard.run() 