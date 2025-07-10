"""
Enhanced Telegram notification service with comprehensive alert types and advanced features.

This module extends the base Telegram notifier with:
- Multiple specialized alert types
- Smart timing and frequency management
- User preferences and personalization
- Advanced interactive components
- Rich media and visualizations
- Analytics and performance tracking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
from io import BytesIO
import aiohttp
from pydantic import BaseModel
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from collections import defaultdict
import math

from ...config.settings import get_settings
from ...config.database import get_database
from .telegram_notifier import TelegramNotifier, TelegramMessage, MessageFormat

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Enhanced alert priority levels."""
    INSTANT = "instant"      # Send immediately
    HIGH = "high"           # Send within 5 minutes
    MEDIUM = "medium"       # Send within 15 minutes
    LOW = "low"            # Send in next batch
    SCHEDULED = "scheduled"  # Send at optimal time


class AlertType(Enum):
    """Enhanced alert types."""
    MEGA_DEAL = "mega_deal"                    # 70%+ discount
    FLASH_SALE = "flash_sale"                  # Limited time high discount
    PRICE_DROP = "price_drop"                  # Significant price reduction
    STOCK_ALERT = "stock_alert"                # Low stock warning
    TRENDING = "trending"                      # Trending products
    CATEGORY_ALERT = "category_alert"          # Category-specific deals
    BRAND_ALERT = "brand_alert"                # Brand-specific deals
    PERSONALIZED = "personalized"             # User preference based
    MARKET_INSIGHT = "market_insight"          # Market analysis
    DAILY_DIGEST = "daily_digest"              # Daily summary
    WEEKLY_REPORT = "weekly_report"            # Weekly analytics
    SYSTEM_STATUS = "system_status"            # System health


@dataclass
class UserPreferences:
    """User notification preferences."""
    user_id: int
    chat_id: str
    min_profit_threshold: float = 30.0
    max_alerts_per_hour: int = 5
    preferred_categories: List[str] = None
    preferred_brands: List[str] = None
    price_range_min: float = 0.0
    price_range_max: float = 1000.0
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8     # 8 AM
    enabled_alert_types: List[str] = None
    timezone: str = "UTC"
    language: str = "en"


class EnhancedTelegramNotifier(TelegramNotifier):
    """Enhanced Telegram notifier with advanced features."""
    
    def __init__(self, bot_token: Optional[str] = None):
        super().__init__(bot_token)
        self.alert_queue = defaultdict(list)
        self.user_preferences = {}
        self.alert_stats = defaultdict(int)
        self.last_alert_times = defaultdict(dict)
        
    async def initialize(self):
        """Initialize the enhanced notifier."""
        await self.load_user_preferences()
        await self.setup_alert_queue_processor()
        
    async def load_user_preferences(self):
        """Load user preferences from database."""
        try:
            db = await get_database()
            users = await db.user_preferences.find({}).to_list(None)
            
            for user in users:
                self.user_preferences[user['user_id']] = UserPreferences(
                    user_id=user['user_id'],
                    chat_id=user.get('chat_id', ''),
                    min_profit_threshold=user.get('min_profit_threshold', 30.0),
                    max_alerts_per_hour=user.get('max_alerts_per_hour', 5),
                    preferred_categories=user.get('preferred_categories', []),
                    preferred_brands=user.get('preferred_brands', []),
                    price_range_min=user.get('price_range_min', 0.0),
                    price_range_max=user.get('price_range_max', 1000.0),
                    quiet_hours_start=user.get('quiet_hours_start', 22),
                    quiet_hours_end=user.get('quiet_hours_end', 8),
                    enabled_alert_types=user.get('enabled_alert_types', []),
                    timezone=user.get('timezone', 'UTC'),
                    language=user.get('language', 'en')
                )
        except Exception as e:
            logger.error(f"Failed to load user preferences: {e}")

    async def send_mega_deal_alert(
        self,
        product_data: Dict[str, Any],
        discount_percentage: float,
        profit_potential: float,
        original_price: float,
        current_price: float,
        time_sensitive: bool = False,
        stock_level: Optional[str] = None,
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Send mega deal alert for exceptional opportunities."""
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
            
        # Create urgency indicators
        urgency_emoji = "🔥🔥🔥" if time_sensitive else "💥💥"
        stock_indicator = f"⚠️ {stock_level.replace('_', ' ').title()}" if stock_level else ""
        
        # Calculate savings
        savings = original_price - current_price
        
        # Create enhanced visualization
        chart = await self._create_mega_deal_chart(
            product_data['title'],
            original_price,
            current_price,
            discount_percentage,
            profit_potential
        )
        
        # Create interactive keyboard with enhanced options
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🛒 Buy Now on MediaMarkt", "url": product_data['url']},
                    {"text": "📊 Price History", "callback_data": f"history_{product_data['id']}"}
                ],
                [
                    {"text": "🔔 Set Price Alert", "callback_data": f"alert_{product_data['id']}"},
                    {"text": "📤 Share Deal", "callback_data": f"share_{product_data['id']}"}
                ],
                [
                    {"text": "❤️ Add to Wishlist", "callback_data": f"wishlist_{product_data['id']}"},
                    {"text": "🚫 Not Interested", "callback_data": f"ignore_{product_data['id']}"}
                ]
            ]
        }
        
        # Format mega deal message
        message_text = self._format_mega_deal_message(
            product_data=product_data,
            discount_percentage=discount_percentage,
            profit_potential=profit_potential,
            original_price=original_price,
            current_price=current_price,
            savings=savings,
            urgency_emoji=urgency_emoji,
            stock_indicator=stock_indicator,
            time_sensitive=time_sensitive
        )
        
        # Send to qualified users
        results = {}
        for chat_id in chat_ids:
            # Check user preferences
            if not await self._should_send_alert(chat_id, AlertType.MEGA_DEAL, profit_potential):
                continue
                
            try:
                # Send chart first
                chart_success = await self.send_photo(
                    chat_id=chat_id,
                    photo=chart,
                    caption=f"{urgency_emoji} MEGA DEAL DETECTED {urgency_emoji}",
                    parse_mode=MessageFormat.HTML
                )
                
                # Send detailed message
                message = TelegramMessage(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=MessageFormat.HTML,
                    reply_markup=keyboard,
                    disable_notification=False  # Mega deals should notify
                )
                
                message_success = await self.send_message(message)
                results[chat_id] = chart_success and message_success
                
                # Track alert
                await self._track_alert_sent(chat_id, AlertType.MEGA_DEAL)
                
            except Exception as e:
                logger.error(f"Failed to send mega deal alert to {chat_id}: {e}")
                results[chat_id] = False
                
        return results
    
    async def send_market_insight_alert(
        self,
        insights: Dict[str, Any],
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Send market analysis and insights."""
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
            
        # Create market analysis chart
        chart = await self._create_market_insight_chart(insights)
        
        # Create insights keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "📈 View Trending Categories", "callback_data": "trends_categories"},
                    {"text": "🏷️ Top Brands", "callback_data": "trends_brands"}
                ],
                [
                    {"text": "⏰ Best Shopping Times", "callback_data": "trends_timing"},
                    {"text": "💰 Price Predictions", "callback_data": "trends_predictions"}
                ],
                [
                    {"text": "📊 Full Report", "callback_data": "insights_full"},
                    {"text": "🔔 Alert Settings", "callback_data": "settings_alerts"}
                ]
            ]
        }
        
        # Format insights message
        message_text = self._format_market_insights(insights)
        
        results = {}
        for chat_id in chat_ids:
            if not await self._should_send_alert(chat_id, AlertType.MARKET_INSIGHT, 0):
                continue
                
            try:
                # Send chart
                chart_success = await self.send_photo(
                    chat_id=chat_id,
                    photo=chart,
                    caption="📊 Market Intelligence Report",
                    parse_mode=MessageFormat.HTML
                )
                
                # Send insights
                message = TelegramMessage(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=MessageFormat.HTML,
                    reply_markup=keyboard,
                    disable_notification=True  # Market insights are informational
                )
                
                message_success = await self.send_message(message)
                results[chat_id] = chart_success and message_success
                
                await self._track_alert_sent(chat_id, AlertType.MARKET_INSIGHT)
                
            except Exception as e:
                logger.error(f"Failed to send market insight to {chat_id}: {e}")
                results[chat_id] = False
                
        return results
    
    async def send_personalized_recommendations(
        self,
        user_id: int,
        recommendations: List[Dict[str, Any]],
        chat_id: Optional[str] = None
    ) -> bool:
        """Send personalized product recommendations."""
        
        if not chat_id and user_id in self.user_preferences:
            chat_id = self.user_preferences[user_id].chat_id
            
        if not chat_id:
            return False
            
        # Create recommendation carousel
        carousel_images = []
        for rec in recommendations[:5]:  # Limit to top 5
            chart = await self._create_recommendation_card(rec)
            carousel_images.append(chart)
            
        # Create navigation keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "⬅️ Previous", "callback_data": "rec_prev"},
                    {"text": f"1/{len(recommendations)}", "callback_data": "rec_info"},
                    {"text": "➡️ Next", "callback_data": "rec_next"}
                ],
                [
                    {"text": "🎯 Update Preferences", "callback_data": "prefs_update"},
                    {"text": "🔕 Stop Recommendations", "callback_data": "rec_stop"}
                ]
            ]
        }
        
        # Format personalized message
        prefs = self.user_preferences.get(user_id)
        message_text = self._format_personalized_recommendations(recommendations, prefs)
        
        try:
            # Send first recommendation with context
            if carousel_images:
                chart_success = await self.send_photo(
                    chat_id=chat_id,
                    photo=carousel_images[0],
                    caption="🎯 Personalized Recommendations",
                    parse_mode=MessageFormat.HTML
                )
            else:
                chart_success = True
                
            message = TelegramMessage(
                chat_id=chat_id,
                text=message_text,
                parse_mode=MessageFormat.HTML,
                reply_markup=keyboard,
                disable_notification=True
            )
            
            message_success = await self.send_message(message)
            
            await self._track_alert_sent(chat_id, AlertType.PERSONALIZED)
            
            return chart_success and message_success
            
        except Exception as e:
            logger.error(f"Failed to send personalized recommendations to {chat_id}: {e}")
            return False
    
    async def send_intelligent_daily_digest(
        self,
        date: datetime,
        analytics: Dict[str, Any],
        top_opportunities: List[Dict[str, Any]],
        user_specific_data: Dict[int, Dict[str, Any]],
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Send intelligent daily digest with analytics and insights."""
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
            
        results = {}
        
        for chat_id in chat_ids:
            # Get user-specific insights
            user_id = await self._get_user_id_from_chat(chat_id)
            user_data = user_specific_data.get(user_id, {})
            
            # Create personalized charts
            digest_chart = await self._create_daily_digest_chart(
                analytics, user_data, date
            )
            
            # Create action-oriented keyboard
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🔥 Today's Best Deals", "callback_data": "digest_deals"},
                        {"text": "📈 Price Trends", "callback_data": "digest_trends"}
                    ],
                    [
                        {"text": "🎯 My Watchlist", "callback_data": "digest_watchlist"},
                        {"text": "⚙️ Customize Digest", "callback_data": "digest_settings"}
                    ],
                    [
                        {"text": "📊 Weekly Report", "callback_data": "report_weekly"},
                        {"text": "💡 Smart Tips", "callback_data": "digest_tips"}
                    ]
                ]
            }
            
            # Format intelligent digest
            message_text = self._format_intelligent_digest(
                date, analytics, top_opportunities, user_data
            )
            
            try:
                # Send digest chart
                chart_success = await self.send_photo(
                    chat_id=chat_id,
                    photo=digest_chart,
                    caption=f"📊 Daily Intelligence Report - {date.strftime('%B %d, %Y')}",
                    parse_mode=MessageFormat.HTML
                )
                
                # Send detailed digest
                message = TelegramMessage(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=MessageFormat.HTML,
                    reply_markup=keyboard,
                    disable_notification=True
                )
                
                message_success = await self.send_message(message)
                results[chat_id] = chart_success and message_success
                
                await self._track_alert_sent(chat_id, AlertType.DAILY_DIGEST)
                
            except Exception as e:
                logger.error(f"Failed to send daily digest to {chat_id}: {e}")
                results[chat_id] = False
                
        return results
    
    async def send_flash_sale_alert(
        self,
        product_data: Dict[str, Any],
        time_remaining: timedelta,
        original_alert_count: int,
        current_stock: Optional[int] = None,
        chat_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Send urgent flash sale alert with countdown."""
        
        if not chat_ids:
            chat_ids = self.default_chat_ids
            
        # Calculate urgency level
        hours_left = time_remaining.total_seconds() / 3600
        urgency_level = "🚨🚨🚨" if hours_left < 2 else "⚡⚡" if hours_left < 6 else "⏰"
        
        # Create countdown visualization
        countdown_chart = await self._create_countdown_chart(
            product_data['title'],
            time_remaining,
            current_stock
        )
        
        # Create urgent action keyboard
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🚀 BUY NOW!", "url": product_data['url']},
                    {"text": "⏰ Set Reminder", "callback_data": f"remind_{product_data['id']}"}
                ],
                [
                    {"text": "📱 Share Alert", "callback_data": f"share_urgent_{product_data['id']}"},
                    {"text": "👥 Alert Friends", "callback_data": f"friends_{product_data['id']}"}
                ]
            ]
        }
        
        # Format flash sale message
        message_text = self._format_flash_sale_message(
            product_data, time_remaining, urgency_level, current_stock, original_alert_count
        )
        
        results = {}
        for chat_id in chat_ids:
            if not await self._should_send_alert(chat_id, AlertType.FLASH_SALE, 50.0):
                continue
                
            try:
                # Send countdown chart
                chart_success = await self.send_photo(
                    chat_id=chat_id,
                    photo=countdown_chart,
                    caption=f"{urgency_level} FLASH SALE ENDING SOON! {urgency_level}",
                    parse_mode=MessageFormat.HTML
                )
                
                # Send urgent message
                message = TelegramMessage(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=MessageFormat.HTML,
                    reply_markup=keyboard,
                    disable_notification=False  # Flash sales need immediate attention
                )
                
                message_success = await self.send_message(message)
                results[chat_id] = chart_success and message_success
                
                await self._track_alert_sent(chat_id, AlertType.FLASH_SALE)
                
            except Exception as e:
                logger.error(f"Failed to send flash sale alert to {chat_id}: {e}")
                results[chat_id] = False
                
        return results
    
    # Chart creation methods
    async def _create_mega_deal_chart(
        self,
        product_title: str,
        original_price: float,
        current_price: float,
        discount_percentage: float,
        profit_potential: float
    ) -> BytesIO:
        """Create enhanced mega deal visualization."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
        plt.style.use('dark_background')
        
        # Price comparison bar chart
        prices = [original_price, current_price]
        labels = ['Original Price', 'Current Price']
        colors = ['#ff6b6b', '#4ecdc4']
        
        bars = ax1.bar(labels, prices, color=colors, alpha=0.8)
        ax1.set_title('Price Comparison', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Price (€)')
        
        # Add value labels
        for bar, price in zip(bars, prices):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'€{price:.2f}', ha='center', va='bottom', fontweight='bold')
        
        # Discount gauge
        ax2.pie([discount_percentage, 100-discount_percentage], 
                colors=['#ff6b6b', '#2c3e50'], 
                startangle=90,
                counterclock=False)
        ax2.set_title(f'Discount: {discount_percentage:.1f}%', fontsize=14, fontweight='bold')
        
        # Profit potential meter
        profit_categories = ['Low', 'Medium', 'High', 'Mega']
        profit_values = [25, 25, 25, 25]
        profit_colors = ['#95a5a6', '#f39c12', '#e74c3c', '#2ecc71']
        
        current_category = min(3, int(profit_potential / 25))
        profit_colors[current_category] = '#ffff00'  # Highlight current level
        
        ax3.pie(profit_values, labels=profit_categories, colors=profit_colors, autopct='')
        ax3.set_title(f'Profit Potential: €{profit_potential:.2f}', fontsize=14, fontweight='bold')
        
        # Savings visualization
        savings = original_price - current_price
        ax4.barh(['Savings'], [savings], color='#2ecc71', alpha=0.8)
        ax4.set_title(f'You Save: €{savings:.2f}', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Amount (€)')
        
        plt.suptitle(f'MEGA DEAL: {product_title[:40]}...', 
                     fontsize=16, fontweight='bold', color='#ffff00')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='#2c3e50', edgecolor='none')
        buf.seek(0)
        plt.close()
        
        return buf
    
    async def _create_market_insight_chart(self, insights: Dict[str, Any]) -> BytesIO:
        """Create market analysis visualization."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Category performance
        categories = list(insights.get('category_performance', {}).keys())[:10]
        performance = list(insights.get('category_performance', {}).values())[:10]
        
        ax1.barh(categories, performance, color='skyblue', alpha=0.8)
        ax1.set_title('Top Performing Categories', fontweight='bold')
        ax1.set_xlabel('Average Discount %')
        
        # Price trend over time
        if 'price_trends' in insights:
            dates = insights['price_trends']['dates']
            avg_prices = insights['price_trends']['average_prices']
            
            ax2.plot(dates, avg_prices, color='orange', linewidth=2, marker='o')
            ax2.set_title('Market Price Trends', fontweight='bold')
            ax2.set_ylabel('Average Price (€)')
            ax2.tick_params(axis='x', rotation=45)
        
        # Opportunity distribution
        if 'opportunity_levels' in insights:
            levels = list(insights['opportunity_levels'].keys())
            counts = list(insights['opportunity_levels'].values())
            
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
            ax3.pie(counts, labels=levels, colors=colors, autopct='%1.1f%%')
            ax3.set_title('Opportunity Distribution', fontweight='bold')
        
        # Best shopping times
        if 'best_times' in insights:
            hours = list(range(24))
            activity = insights.get('hourly_activity', [0] * 24)
            
            ax4.bar(hours, activity, color='lightgreen', alpha=0.7)
            ax4.set_title('Best Shopping Hours', fontweight='bold')
            ax4.set_xlabel('Hour of Day')
            ax4.set_ylabel('Deal Activity')
        
        plt.suptitle('Market Intelligence Dashboard', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    async def _create_daily_digest_chart(
        self, 
        analytics: Dict[str, Any], 
        user_data: Dict[str, Any], 
        date: datetime
    ) -> BytesIO:
        """Create personalized daily digest visualization."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Daily summary stats
        stats = ['Deals Found', 'Avg Discount', 'Best Saving', 'Your Alerts']
        values = [
            analytics.get('deals_found', 0),
            analytics.get('average_discount', 0),
            analytics.get('best_saving', 0),
            user_data.get('alerts_received', 0)
        ]
        
        bars = ax1.bar(stats, values, color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12'])
        ax1.set_title(f'Daily Summary - {date.strftime("%B %d")}', fontweight='bold')
        
        # Add value labels
        for bar, value in zip(bars, values):
            height = bar.get_height()
            if 'Discount' in bar.get_x() or 'Saving' in bar.get_x():
                label = f'€{value:.0f}' if 'Saving' in bar.get_x() else f'{value:.1f}%'
            else:
                label = f'{int(value)}'
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    label, ha='center', va='bottom', fontweight='bold')
        
        # Weekly trend
        if 'weekly_trend' in analytics:
            days = analytics['weekly_trend']['days']
            deals = analytics['weekly_trend']['deals']
            
            ax2.plot(days, deals, color='purple', linewidth=3, marker='o', markersize=8)
            ax2.set_title('7-Day Deal Trend', fontweight='bold')
            ax2.set_ylabel('Deals Found')
            ax2.grid(True, alpha=0.3)
        
        # User preferences impact
        if user_data.get('preference_matches'):
            categories = list(user_data['preference_matches'].keys())
            matches = list(user_data['preference_matches'].values())
            
            ax3.pie(matches, labels=categories, autopct='%1.0f%%', startangle=90)
            ax3.set_title('Your Preference Matches', fontweight='bold')
        
        # Savings potential
        if 'savings_forecast' in analytics:
            months = analytics['savings_forecast']['months']
            potential = analytics['savings_forecast']['potential']
            
            ax4.bar(months, potential, color='gold', alpha=0.8)
            ax4.set_title('Monthly Savings Forecast', fontweight='bold')
            ax4.set_ylabel('Potential Savings (€)')
        
        plt.suptitle('Your Personalized Daily Intelligence', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    # Message formatting methods
    def _format_mega_deal_message(
        self,
        product_data: Dict[str, Any],
        discount_percentage: float,
        profit_potential: float,
        original_price: float,
        current_price: float,
        savings: float,
        urgency_emoji: str,
        stock_indicator: str,
        time_sensitive: bool
    ) -> str:
        """Format mega deal alert message."""
        
        def escape_html(text: str) -> str:
            if not text:
                return ""
            return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#x27;"))
        
        title = escape_html(product_data['title'])[:60] + ("..." if len(product_data['title']) > 60 else "")
        brand = escape_html(product_data.get('brand', 'Unknown'))
        
        message_parts = [
            f"{urgency_emoji} <b>MEGA DEAL ALERT!</b> {urgency_emoji}",
            "",
            f"🏆 <b>{title}</b>",
            f"🏷️ <b>Brand:</b> {brand}",
            "",
            f"💸 <b>Was:</b> <s>€{original_price:.2f}</s>",
            f"🔥 <b>Now:</b> <code>€{current_price:.2f}</code>",
            f"💰 <b>You Save:</b> <code>€{savings:.2f}</code>",
            f"📊 <b>Discount:</b> <code>{discount_percentage:.1f}%</code>",
            f"🚀 <b>Profit Potential:</b> <code>€{profit_potential:.2f}</code>",
            ""
        ]
        
        if stock_indicator:
            message_parts.append(f"{stock_indicator}")
            message_parts.append("")
        
        if time_sensitive:
            message_parts.extend([
                "⏰ <b>LIMITED TIME OFFER!</b>",
                "🏃‍♂️ <i>Act fast - this deal won't last long!</i>",
                ""
            ])
        
        # Add quality indicators
        if profit_potential > 100:
            message_parts.append("🌟 <b>PREMIUM OPPORTUNITY</b> - Exceptional profit potential!")
        elif profit_potential > 50:
            message_parts.append("⭐ <b>HIGH-VALUE DEAL</b> - Great profit opportunity!")
        else:
            message_parts.append("📈 <b>SOLID OPPORTUNITY</b> - Good profit potential!")
        
        message_parts.extend([
            "",
            f"🕐 <i>Alert sent at {datetime.now().strftime('%H:%M:%S')}</i>",
            "",
            "💡 <i>Tap buttons below to take action!</i>"
        ])
        
        return "\n".join(message_parts)
    
    def _format_market_insights(self, insights: Dict[str, Any]) -> str:
        """Format market insights message."""
        
        message_parts = [
            "📊 <b>MARKET INTELLIGENCE REPORT</b>",
            "",
            "🔍 <b>Today's Key Insights:</b>",
            ""
        ]
        
        # Top performing category
        if 'top_category' in insights:
            category = insights['top_category']['name']
            performance = insights['top_category']['avg_discount']
            message_parts.extend([
                f"🏆 <b>Top Category:</b> {category}",
                f"📈 <b>Average Discount:</b> {performance:.1f}%",
                ""
            ])
        
        # Price trends
        if 'price_direction' in insights:
            direction = insights['price_direction']
            emoji = "📉" if direction == "decreasing" else "📈" if direction == "increasing" else "➡️"
            message_parts.extend([
                f"{emoji} <b>Price Trend:</b> {direction.title()}",
                f"💭 <b>Forecast:</b> {insights.get('forecast', 'Stable market conditions')}"
            ])
        
        # Best shopping windows
        if 'best_shopping_times' in insights:
            times = insights['best_shopping_times']
            message_parts.extend([
                "",
                "⏰ <b>Optimal Shopping Windows:</b>",
                f"🌅 <b>Morning:</b> {times.get('morning', 'Low activity')}",
                f"🌆 <b>Evening:</b> {times.get('evening', 'Moderate activity')}",
                f"🌙 <b>Night:</b> {times.get('night', 'High activity')}"
            ])
        
        # Opportunity summary
        if 'opportunities' in insights:
            total = insights['opportunities']['total']
            high_value = insights['opportunities']['high_value']
            message_parts.extend([
                "",
                f"🎯 <b>Opportunities Today:</b> {total}",
                f"💎 <b>High-Value Deals:</b> {high_value}",
                f"📊 <b>Success Rate:</b> {insights.get('success_rate', 0):.1f}%"
            ])
        
        message_parts.extend([
            "",
            f"📅 <i>Analysis updated: {datetime.now().strftime('%H:%M')}</i>",
            "",
            "💡 <i>Use buttons below to explore insights!</i>"
        ])
        
        return "\n".join(message_parts)
    
    def _format_flash_sale_message(
        self,
        product_data: Dict[str, Any],
        time_remaining: timedelta,
        urgency_level: str,
        current_stock: Optional[int],
        original_alert_count: int
    ) -> str:
        """Format flash sale alert message."""
        
        def escape_html(text: str) -> str:
            if not text:
                return ""
            return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;"))
        
        # Calculate time components
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        
        title = escape_html(product_data['title'])[:50] + ("..." if len(product_data['title']) > 50 else "")
        
        message_parts = [
            f"{urgency_level} <b>FLASH SALE ENDING!</b> {urgency_level}",
            "",
            f"⚡ <b>{title}</b>",
            "",
            f"⏰ <b>Time Left:</b> <code>{hours}h {minutes}m</code>",
            f"💰 <b>Current Price:</b> <code>€{product_data['price']:.2f}</code>"
        ]
        
        if current_stock:
            if current_stock < 10:
                message_parts.append(f"🔥 <b>Only {current_stock} left!</b>")
            else:
                message_parts.append(f"📦 <b>Stock:</b> {current_stock} available")
        
        message_parts.extend([
            "",
            f"👥 <b>{original_alert_count}</b> people already alerted!",
            "",
            "🚨 <b>DON'T MISS OUT!</b>",
            "This deal expires soon and may not return.",
            "",
            f"⚡ <i>Urgent alert sent at {datetime.now().strftime('%H:%M:%S')}</i>"
        ])
        
        return "\n".join(message_parts)
    
    # Helper methods
    async def _should_send_alert(
        self, 
        chat_id: str, 
        alert_type: AlertType, 
        profit_potential: float
    ) -> bool:
        """Check if alert should be sent to user based on preferences."""
        
        try:
            user_id = await self._get_user_id_from_chat(chat_id)
            if not user_id:
                return True  # Default to sending if no user data
            
            prefs = self.user_preferences.get(user_id)
            if not prefs:
                return True
            
            # Check profit threshold
            if profit_potential < prefs.min_profit_threshold:
                return False
            
            # Check alert type preferences
            if prefs.enabled_alert_types and alert_type.value not in prefs.enabled_alert_types:
                return False
            
            # Check rate limiting
            current_hour = datetime.now().hour
            alerts_this_hour = self.last_alert_times.get(chat_id, {}).get(current_hour, 0)
            if alerts_this_hour >= prefs.max_alerts_per_hour:
                return False
            
            # Check quiet hours
            if prefs.quiet_hours_start <= current_hour or current_hour <= prefs.quiet_hours_end:
                if alert_type not in [AlertType.MEGA_DEAL, AlertType.FLASH_SALE]:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking alert preferences: {e}")
            return True  # Default to sending on error
    
    async def _track_alert_sent(self, chat_id: str, alert_type: AlertType):
        """Track that an alert was sent."""
        current_hour = datetime.now().hour
        if chat_id not in self.last_alert_times:
            self.last_alert_times[chat_id] = {}
        
        self.last_alert_times[chat_id][current_hour] = \
            self.last_alert_times[chat_id].get(current_hour, 0) + 1
        
        self.alert_stats[alert_type.value] += 1
    
    async def _get_user_id_from_chat(self, chat_id: str) -> Optional[int]:
        """Get user ID from chat ID."""
        try:
            db = await get_database()
            user = await db.user_preferences.find_one({"chat_id": chat_id})
            return user.get('user_id') if user else None
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alert statistics."""
        return {
            "total_alerts_sent": sum(self.alert_stats.values()),
            "alerts_by_type": dict(self.alert_stats),
            "active_users": len(self.user_preferences),
            "alerts_in_queue": sum(len(alerts) for alerts in self.alert_queue.values()),
            "last_24h_alerts": self._get_24h_alert_count(),
            "average_alerts_per_user": self._calculate_avg_alerts_per_user()
        }
    
    def _get_24h_alert_count(self) -> int:
        """Get alert count for last 24 hours."""
        current_hour = datetime.now().hour
        total = 0
        for chat_alerts in self.last_alert_times.values():
            for hour, count in chat_alerts.items():
                if abs(hour - current_hour) <= 24:
                    total += count
        return total
    
    def _calculate_avg_alerts_per_user(self) -> float:
        """Calculate average alerts per user."""
        if not self.user_preferences:
            return 0.0
        return sum(self.alert_stats.values()) / len(self.user_preferences)


# Convenience functions for easy integration
async def send_enhanced_mega_deal(
    product_data: Dict[str, Any],
    discount_percentage: float,
    profit_potential: float,
    **kwargs
) -> bool:
    """Quick function to send mega deal alert."""
    async with EnhancedTelegramNotifier() as notifier:
        await notifier.initialize()
        results = await notifier.send_mega_deal_alert(
            product_data=product_data,
            discount_percentage=discount_percentage,
            profit_potential=profit_potential,
            **kwargs
        )
        return any(results.values())


async def send_enhanced_market_insights(insights: Dict[str, Any]) -> bool:
    """Quick function to send market insights."""
    async with EnhancedTelegramNotifier() as notifier:
        await notifier.initialize()
        results = await notifier.send_market_insight_alert(insights)
        return any(results.values())


async def send_enhanced_daily_digest(
    date: datetime,
    analytics: Dict[str, Any],
    top_opportunities: List[Dict[str, Any]],
    user_specific_data: Dict[int, Dict[str, Any]]
) -> bool:
    """Quick function to send enhanced daily digest."""
    async with EnhancedTelegramNotifier() as notifier:
        await notifier.initialize()
        results = await notifier.send_intelligent_daily_digest(
            date, analytics, top_opportunities, user_specific_data
        )
        return any(results.values()) 