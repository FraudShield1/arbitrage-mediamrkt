"""Products browser component for exploring MediaMarkt product catalog."""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..utils.mongodb_loader import MongoDBDataLoader


class ProductsBrowser:
    """Dashboard component for browsing and searching products."""
    
    def __init__(self, data_loader: MongoDBDataLoader):
        """Initialize products browser.
        
        Args:
            data_loader: MongoDBDataLoader instance for fetching data
        """
        self.data_loader = data_loader
    
    def render(self) -> None:
        """Render the products browser component."""
        st.header("📦 Products Browser")
        
        # Render search and filters
        search_params = self._render_search_filters()
        
        # Load products with filters
        products = self._load_products(search_params)
        if products is None:
            st.error("Unable to load products")
            return
        
        # Display summary stats
        self._render_product_summary(products)
        
        # Render the main products table
        self._render_products_table(products)
    
    def _render_search_filters(self) -> Dict[str, Any]:
        """Render search and filter controls."""
        st.subheader("🔍 Search & Filters")
        
        # Main search
        search_term = st.text_input(
            "Search Products",
            placeholder="Enter product name, brand, or EAN...",
            help="Search across product names, brands, and EAN codes"
        )
        
        # Filter controls in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            category_filter = st.selectbox(
                "Category",
                options=["all", "Electronics", "Home & Garden", "Sports", "Fashion", "Books", "Gaming"],
                index=0
            )
        
        with col2:
            brand_filter = st.selectbox(
                "Brand",
                options=["all", "Samsung", "Apple", "Sony", "Philips", "LG", "HP", "Other"],
                index=0
            )
        
        with col3:
            stock_filter = st.selectbox(
                "Stock Status",
                options=["all", "in_stock", "out_of_stock"],
                index=0
            )
        
        with col4:
            has_discount = st.selectbox(
                "Discounted Only",
                options=["all", "yes", "no"],
                index=0
            )
        
        # Price range filters
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            min_price = st.number_input(
                "Min Price (€)",
                min_value=0.0,
                value=0.0,
                step=10.0
            )
        
        with col6:
            max_price = st.number_input(
                "Max Price (€)",
                min_value=0.0,
                value=1000.0,
                step=50.0
            )
        
        with col7:
            min_discount = st.slider(
                "Min Discount %",
                min_value=0,
                max_value=90,
                value=0,
                step=5
            )
        
        with col8:
            has_asin = st.selectbox(
                "Has Amazon Match",
                options=["all", "yes", "no"],
                index=0
            )
        
        # Sort and display options
        col9, col10, col11, col12 = st.columns(4)
        
        with col9:
            sort_by = st.selectbox(
                "Sort By",
                options=["created_at", "current_price", "discount_percentage", "product_name"],
                index=0
            )
        
        with col10:
            sort_order = st.selectbox(
                "Order",
                options=["desc", "asc"],
                index=0
            )
        
        with col11:
            size = st.selectbox(
                "Results per Page",
                options=[25, 50, 100, 200],
                index=1
            )
        
        with col12:
            refresh_clicked = st.button("🔄 Refresh", key="products_refresh")
        
        if refresh_clicked:
            self.data_loader.clear_cache()
        
        return {
            "search": search_term,
            "category": category_filter,
            "brand": brand_filter,
            "stock_status": stock_filter,
            "has_discount": has_discount,
            "min_price": min_price,
            "max_price": max_price,
            "min_discount": min_discount,
            "has_asin": has_asin,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "size": size
        }
    
    def _load_products(self, search_params: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Load products with applied search and filters."""
        try:
            # Convert search params for API call
            api_params = {}
            
            if search_params["search"]:
                api_params["search"] = search_params["search"]
            
            if search_params["category"] != "all":
                api_params["category"] = search_params["category"]
            
            if search_params["brand"] != "all":
                api_params["brand"] = search_params["brand"]
            
            if search_params["stock_status"] != "all":
                api_params["stock_status"] = search_params["stock_status"]
            
            if search_params["has_discount"] == "yes":
                api_params["has_discount"] = True
            elif search_params["has_discount"] == "no":
                api_params["has_discount"] = False
            
            if search_params["min_price"] > 0:
                api_params["min_price"] = search_params["min_price"]
            
            if search_params["max_price"] < 10000:  # Reasonable upper limit
                api_params["max_price"] = search_params["max_price"]
            
            if search_params["min_discount"] > 0:
                api_params["min_discount"] = search_params["min_discount"]
            
            if search_params["has_asin"] == "yes":
                api_params["has_asin"] = True
            elif search_params["has_asin"] == "no":
                api_params["has_asin"] = False
            
            # Sorting and pagination
            api_params["sort_by"] = search_params["sort_by"]
            api_params["sort_order"] = search_params["sort_order"]
            api_params["size"] = search_params["size"]
            
            return self.data_loader.get_products(**api_params)
        
        except Exception as e:
            st.error(f"Error loading products: {e}")
            return None
    
    def _render_product_summary(self, products: List[Dict[str, Any]]) -> None:
        """Render summary statistics for current product list."""
        if not products:
            st.info("No products found matching the current search criteria.")
            return
        
        # Calculate summary stats
        total_products = len(products)
        discounted_products = sum(1 for p in products if p.get("discount_percentage", 0) > 0)
        avg_price = sum(p.get("current_price", 0) for p in products) / total_products if total_products > 0 else 0
        avg_discount = sum(p.get("discount_percentage", 0) for p in products if p.get("discount_percentage", 0) > 0)
        avg_discount = avg_discount / discounted_products if discounted_products > 0 else 0
        
        # Products with Amazon matches
        with_asin = sum(1 for p in products if p.get("asin"))
        
        # Display summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Products", f"{total_products:,}")
        
        with col2:
            st.metric("Average Price", f"€{avg_price:.2f}")
        
        with col3:
            discount_rate = (discounted_products / total_products * 100) if total_products > 0 else 0
            st.metric("Discounted", f"{discounted_products:,}", delta=f"{discount_rate:.1f}%")
        
        with col4:
            match_rate = (with_asin / total_products * 100) if total_products > 0 else 0
            st.metric("Amazon Matches", f"{with_asin:,}", delta=f"{match_rate:.1f}%")
        
        # Additional stats
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            if avg_discount > 0:
                st.metric("Avg Discount", f"{avg_discount:.1f}%")
            else:
                st.metric("Avg Discount", "0%")
        
        with col6:
            in_stock = sum(1 for p in products if p.get("stock_status") == "in_stock")
            st.metric("In Stock", f"{in_stock:,}")
        
        with col7:
            # Top category
            categories = {}
            for p in products:
                cat = p.get("category", "Unknown")
                categories[cat] = categories.get(cat, 0) + 1
            
            if categories:
                top_category = max(categories, key=categories.get)
                st.metric("Top Category", top_category[:15])
        
        with col8:
            # Recently added (within 24h)
            recent_count = sum(1 for p in products if self._is_recent(p.get("created_at")))
            st.metric("Recently Added", recent_count)
    
    def _render_products_table(self, products: List[Dict[str, Any]]) -> None:
        """Render the main products table."""
        if not products:
            return
        
        st.markdown("---")
        st.subheader("📋 Product Details")
        
        # Convert to DataFrame for better display
        df_data = []
        for product in products:
            discount_pct = product.get("discount_percentage", 0)
            original_price = product.get("original_price", 0)
            current_price = product.get("current_price", 0)
            
            # Calculate original price if not provided but discount exists
            if discount_pct > 0 and original_price == 0:
                original_price = current_price / (1 - discount_pct / 100)
            
            df_data.append({
                "ID": product["id"],
                "Product": product.get("product_name", "Unknown")[:60] + ("..." if len(product.get("product_name", "")) > 60 else ""),
                "Brand": product.get("brand", "Unknown")[:20],
                "Category": product.get("category", "Unknown")[:15],
                "Current Price": f"€{current_price:.2f}",
                "Original Price": f"€{original_price:.2f}" if original_price > 0 else "-",
                "Discount": f"{discount_pct:.1f}%" if discount_pct > 0 else "-",
                "Stock": "✅" if product.get("stock_status") == "in_stock" else "❌",
                "Amazon Match": "✅" if product.get("asin") else "❌",
                "EAN": product.get("ean", "Unknown")[:13],
                "Updated": self._format_datetime(product.get("updated_at"))
            })
        
        df = pd.DataFrame(df_data)
        
        # Display the table with custom configuration
        edited_df = st.data_editor(
            df,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Product": st.column_config.TextColumn("Product", width="large"),
                "Brand": st.column_config.TextColumn("Brand", width="small"),
                "Category": st.column_config.TextColumn("Category", width="small"),
                "Current Price": st.column_config.TextColumn("Current €", width="small"),
                "Original Price": st.column_config.TextColumn("Original €", width="small"),
                "Discount": st.column_config.TextColumn("Discount", width="small"),
                "Stock": st.column_config.TextColumn("Stock", width="small"),
                "Amazon Match": st.column_config.TextColumn("ASIN", width="small"),
                "EAN": st.column_config.TextColumn("EAN", width="medium"),
                "Updated": st.column_config.TextColumn("Updated", width="medium")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        # Product details and actions
        self._render_product_actions(products)
        
        # Export functionality
        self._render_export_options(products)
    
    def _render_product_actions(self, products: List[Dict[str, Any]]) -> None:
        """Render product action buttons."""
        st.markdown("---")
        st.subheader("🔧 Product Actions")
        
        # Quick actions
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔍 Analyze Discounts", help="Show discount analysis"):
                self._show_discount_analysis(products)
        
        with col2:
            if st.button("📊 Category Stats", help="Show category breakdown"):
                self._show_category_stats(products)
        
        with col3:
            if st.button("🏷️ Brand Analysis", help="Show brand distribution"):
                self._show_brand_analysis(products)
        
        with col4:
            if st.button("🔗 View Amazon Matches", help="Show matched products"):
                matched_products = [p for p in products if p.get("asin")]
                if matched_products:
                    self._show_matched_products(matched_products)
                else:
                    st.info("No Amazon matches found in current results")
        
        # Individual product actions for top results
        st.markdown("**Top Products:**")
        display_products = products[:5] if len(products) > 5 else products
        
        for i, product in enumerate(display_products):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                discount_info = f" (-{product.get('discount_percentage', 0):.1f}%)" if product.get('discount_percentage', 0) > 0 else ""
                st.write(f"**{product.get('product_name', 'Unknown')[:50]}** - €{product.get('current_price', 0):.2f}{discount_info}")
            
            with col2:
                if st.button("👁️ Details", key=f"details_{product['id']}", help="View product details"):
                    self._show_product_details(product)
            
            with col3:
                if st.button("🔗 MediaMarkt", key=f"mm_link_{product['id']}", help="Open MediaMarkt page"):
                    if product.get('url'):
                        st.markdown(f"[Open MediaMarkt]({product['url']})")
                    else:
                        st.warning("No URL available")
            
            with col4:
                if product.get('asin'):
                    if st.button("📊 Amazon", key=f"amz_link_{product['id']}", help="View Amazon data"):
                        self._show_amazon_data(product)
                else:
                    st.text("No ASIN")
    
    def _render_export_options(self, products: List[Dict[str, Any]]) -> None:
        """Render export functionality."""
        st.markdown("---")
        st.subheader("📤 Export Options")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Export All to CSV"):
                self._export_products_csv(products, "all")
        
        with col2:
            if st.button("💰 Export Discounted Only"):
                discounted = [p for p in products if p.get("discount_percentage", 0) > 0]
                if discounted:
                    self._export_products_csv(discounted, "discounted")
                else:
                    st.warning("No discounted products found")
        
        with col3:
            if st.button("🔗 Export Matched Only"):
                matched = [p for p in products if p.get("asin")]
                if matched:
                    self._export_products_csv(matched, "matched")
                else:
                    st.warning("No matched products found")
        
        with col4:
            if st.button("📦 Export In-Stock Only"):
                in_stock = [p for p in products if p.get("stock_status") == "in_stock"]
                if in_stock:
                    self._export_products_csv(in_stock, "in_stock")
                else:
                    st.warning("No in-stock products found")
    
    def _show_discount_analysis(self, products: List[Dict[str, Any]]) -> None:
        """Show discount analysis in an expandable section."""
        with st.expander("💰 Discount Analysis", expanded=True):
            discounted = [p for p in products if p.get("discount_percentage", 0) > 0]
            
            if not discounted:
                st.info("No discounted products in current results")
                return
            
            # Discount distribution
            discounts = [p.get("discount_percentage", 0) for p in discounted]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Discount Statistics:**")
                st.write(f"Products with discount: {len(discounted)}")
                st.write(f"Average discount: {sum(discounts)/len(discounts):.1f}%")
                st.write(f"Highest discount: {max(discounts):.1f}%")
                st.write(f"Lowest discount: {min(discounts):.1f}%")
            
            with col2:
                # Discount ranges
                ranges = {"0-10%": 0, "10-25%": 0, "25-50%": 0, "50%+": 0}
                for discount in discounts:
                    if discount < 10:
                        ranges["0-10%"] += 1
                    elif discount < 25:
                        ranges["10-25%"] += 1
                    elif discount < 50:
                        ranges["25-50%"] += 1
                    else:
                        ranges["50%+"] += 1
                
                st.write("**Discount Distribution:**")
                for range_name, count in ranges.items():
                    if count > 0:
                        st.write(f"{range_name}: {count} products")
    
    def _show_category_stats(self, products: List[Dict[str, Any]]) -> None:
        """Show category statistics."""
        with st.expander("📊 Category Statistics", expanded=True):
            categories = {}
            for product in products:
                cat = product.get("category", "Unknown")
                categories[cat] = categories.get(cat, 0) + 1
            
            if categories:
                st.write("**Products by Category:**")
                sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
                
                for category, count in sorted_categories:
                    percentage = (count / len(products)) * 100
                    st.write(f"• {category}: {count} products ({percentage:.1f}%)")
            else:
                st.info("No category data available")
    
    def _show_brand_analysis(self, products: List[Dict[str, Any]]) -> None:
        """Show brand analysis."""
        with st.expander("🏷️ Brand Analysis", expanded=True):
            brands = {}
            for product in products:
                brand = product.get("brand", "Unknown")
                brands[brand] = brands.get(brand, 0) + 1
            
            if brands:
                st.write("**Products by Brand (Top 10):**")
                sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]
                
                for brand, count in sorted_brands:
                    percentage = (count / len(products)) * 100
                    st.write(f"• {brand}: {count} products ({percentage:.1f}%)")
            else:
                st.info("No brand data available")
    
    def _show_matched_products(self, matched_products: List[Dict[str, Any]]) -> None:
        """Show products with Amazon matches."""
        with st.expander("🔗 Amazon Matched Products", expanded=True):
            st.write(f"**Found {len(matched_products)} products with Amazon matches:**")
            
            for product in matched_products[:10]:  # Show first 10
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{product.get('product_name', 'Unknown')[:40]}**")
                    st.write(f"EAN: {product.get('ean', 'Unknown')}")
                
                with col2:
                    st.write(f"Price: €{product.get('current_price', 0):.2f}")
                    if product.get('discount_percentage', 0) > 0:
                        st.write(f"Discount: {product.get('discount_percentage', 0):.1f}%")
                
                with col3:
                    st.write(f"ASIN: {product.get('asin', 'Unknown')}")
                    st.write(f"Confidence: {product.get('match_confidence', 0):.1f}%")
            
            if len(matched_products) > 10:
                st.info(f"Showing first 10 of {len(matched_products)} matched products")
    
    def _show_product_details(self, product: Dict[str, Any]) -> None:
        """Show detailed product information."""
        with st.expander(f"Product Details - {product['id']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Basic Information:**")
                st.write(f"Name: {product.get('product_name', 'Unknown')}")
                st.write(f"Brand: {product.get('brand', 'Unknown')}")
                st.write(f"Category: {product.get('category', 'Unknown')}")
                st.write(f"EAN: {product.get('ean', 'Unknown')}")
                
                st.write("**Pricing:**")
                st.write(f"Current Price: €{product.get('current_price', 0):.2f}")
                if product.get('original_price', 0) > 0:
                    st.write(f"Original Price: €{product.get('original_price', 0):.2f}")
                if product.get('discount_percentage', 0) > 0:
                    st.write(f"Discount: {product.get('discount_percentage', 0):.1f}%")
            
            with col2:
                st.write("**Status:**")
                st.write(f"Stock: {'In Stock' if product.get('stock_status') == 'in_stock' else 'Out of Stock'}")
                st.write(f"Updated: {self._format_datetime(product.get('updated_at'))}")
                
                if product.get('asin'):
                    st.write("**Amazon Match:**")
                    st.write(f"ASIN: {product.get('asin')}")
                    st.write(f"Confidence: {product.get('match_confidence', 0):.1f}%")
                
                if product.get('url'):
                    st.write("**Links:**")
                    st.markdown(f"[View on MediaMarkt]({product['url']})")
    
    def _show_amazon_data(self, product: Dict[str, Any]) -> None:
        """Show Amazon-related data for a product."""
        with st.expander(f"Amazon Data - {product.get('asin', 'Unknown')}", expanded=True):
            st.write("**Amazon Information:**")
            st.write(f"ASIN: {product.get('asin', 'Unknown')}")
            st.write(f"Match Confidence: {product.get('match_confidence', 0):.1f}%")
            
            # This would be expanded with actual Amazon data from Keepa API
            st.info("Amazon price history and competition data would be displayed here")
    
    def _export_products_csv(self, products: List[Dict[str, Any]], export_type: str) -> None:
        """Export products to CSV."""
        if not products:
            st.warning("No products to export")
            return
        
        # Prepare data for CSV
        csv_data = []
        for product in products:
            csv_data.append({
                "ID": product["id"],
                "Product Name": product.get("product_name", ""),
                "Brand": product.get("brand", ""),
                "Category": product.get("category", ""),
                "EAN": product.get("ean", ""),
                "Current Price": product.get("current_price", 0),
                "Original Price": product.get("original_price", 0),
                "Discount Percentage": product.get("discount_percentage", 0),
                "Stock Status": product.get("stock_status", ""),
                "ASIN": product.get("asin", ""),
                "Match Confidence": product.get("match_confidence", 0),
                "URL": product.get("url", ""),
                "Created At": product.get("created_at", ""),
                "Updated At": product.get("updated_at", "")
            })
        
        df = pd.DataFrame(csv_data)
        csv = df.to_csv(index=False)
        
        filename = f"mediamarkt_products_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        st.download_button(
            label=f"📥 Download {export_type.title()} Products CSV",
            data=csv,
            file_name=filename,
            mime="text/csv"
        )
    
    def _is_recent(self, date_str: Optional[str]) -> bool:
        """Check if a date is within the last 24 hours."""
        if not date_str:
            return False
        
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (datetime.now().replace(tzinfo=date.tzinfo) - date).total_seconds() < 86400
        except:
            return False
    
    def _format_datetime(self, dt_str: Optional[str]) -> str:
        """Format datetime string for display."""
        if not dt_str:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return dt_str 