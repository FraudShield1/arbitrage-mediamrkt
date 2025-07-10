"""
Email notification service for arbitrage alerts.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import asyncio
from concurrent.futures import ThreadPoolExecutor
import structlog

from src.config.settings import settings

logger = structlog.get_logger(__name__)


class EmailNotifier:
    """Email notification service for arbitrage alerts."""
    
    def __init__(self):
        self.smtp_server = settings.email.smtp_host
        self.smtp_port = settings.email.smtp_port
        self.username = settings.email.smtp_user
        self.password = settings.email.smtp_password
        self.from_email = settings.email.from_email
        self.use_tls = True  # Default to True for security
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    async def send_arbitrage_alert(
        self,
        recipients: List[str],
        product_data: Dict[str, Any],
        alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send arbitrage opportunity alert via email.
        
        Args:
            recipients: List of email addresses
            product_data: Product information
            alert_data: Alert details with profit calculations
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = self._generate_alert_subject(product_data, alert_data)
            html_body = self._generate_alert_html(product_data, alert_data)
            text_body = self._generate_alert_text(product_data, alert_data)
            
            success = await self._send_email(
                recipients=recipients,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info("Arbitrage alert sent successfully", 
                          recipients=len(recipients),
                          product_title=product_data.get('title', 'Unknown')[:50])
            else:
                logger.error("Failed to send arbitrage alert",
                           recipients=len(recipients))
            
            return success
            
        except Exception as e:
            logger.error("Error sending arbitrage alert", error=str(e))
            return False
    
    async def send_system_notification(
        self,
        recipients: List[str],
        subject: str,
        message: str,
        severity: str = "info"
    ) -> bool:
        """
        Send system notification email.
        
        Args:
            recipients: List of email addresses
            subject: Email subject
            message: Notification message
            severity: Notification severity (info, warning, error)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            html_body = self._generate_system_notification_html(message, severity)
            text_body = self._generate_system_notification_text(message, severity)
            
            # Add severity prefix to subject
            severity_prefix = {
                "error": "🚨 ERROR",
                "warning": "⚠️ WARNING", 
                "info": "ℹ️ INFO"
            }.get(severity, "📢")
            
            full_subject = f"{severity_prefix} - {subject}"
            
            success = await self._send_email(
                recipients=recipients,
                subject=full_subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info("System notification sent successfully",
                          recipients=len(recipients),
                          severity=severity)
            else:
                logger.error("Failed to send system notification",
                           recipients=len(recipients),
                           severity=severity)
            
            return success
            
        except Exception as e:
            logger.error("Error sending system notification", error=str(e))
            return False
    
    async def send_daily_summary(
        self,
        recipients: List[str],
        summary_data: Dict[str, Any]
    ) -> bool:
        """
        Send daily summary report via email.
        
        Args:
            recipients: List of email addresses
            summary_data: Daily statistics and top opportunities
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = f"📊 Daily Arbitrage Summary - {datetime.now().strftime('%Y-%m-%d')}"
            html_body = self._generate_daily_summary_html(summary_data)
            text_body = self._generate_daily_summary_text(summary_data)
            
            success = await self._send_email(
                recipients=recipients,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            if success:
                logger.info("Daily summary sent successfully",
                          recipients=len(recipients),
                          alerts_count=summary_data.get('total_alerts', 0))
            else:
                logger.error("Failed to send daily summary",
                           recipients=len(recipients))
            
            return success
            
        except Exception as e:
            logger.error("Error sending daily summary", error=str(e))
            return False
    
    async def test_connection(self) -> bool:
        """
        Test email connection and configuration.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self.executor,
                self._test_smtp_connection
            )
            
            if success:
                logger.info("Email connection test successful")
            else:
                logger.error("Email connection test failed")
            
            return success
            
        except Exception as e:
            logger.error("Email connection test error", error=str(e))
            return False
    
    async def _send_email(
        self,
        recipients: List[str],
        subject: str,
        html_body: str,
        text_body: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send email using SMTP."""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                self._send_smtp_email,
                recipients,
                subject,
                html_body,
                text_body,
                attachments
            )
        except Exception as e:
            logger.error("Error in async email sending", error=str(e))
            return False
    
    def _send_smtp_email(
        self,
        recipients: List[str],
        subject: str,
        html_body: str,
        text_body: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Synchronous SMTP email sending."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(recipients)
            
            # Add text and HTML parts
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Create SMTP connection
            if self.use_tls and self.smtp_port == 587:
                # Use STARTTLS
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=ssl.create_default_context())
            elif self.smtp_port == 465:
                # Use SSL
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                # Plain connection
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Login and send
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error("SMTP email sending failed", error=str(e))
            return False
    
    def _test_smtp_connection(self) -> bool:
        """Test SMTP connection synchronously."""
        try:
            if self.use_tls and self.smtp_port == 587:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=ssl.create_default_context())
            elif self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            if self.username and self.password:
                server.login(self.username, self.password)
            
            server.quit()
            return True
            
        except Exception as e:
            logger.error("SMTP connection test failed", error=str(e))
            return False
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error("Failed to add attachment", filename=attachment.get('filename'), error=str(e))
    
    def _generate_alert_subject(self, product_data: Dict[str, Any], alert_data: Dict[str, Any]) -> str:
        """Generate subject line for arbitrage alert."""
        profit_potential = alert_data.get('profit_potential', 0)
        discount_percentage = alert_data.get('discount_percentage', 0)
        product_title = product_data.get('title', 'Product')[:50]
        
        severity_emoji = {
            'critical': '🔥',
            'high': '⚡',
            'medium': '💰'
        }.get(alert_data.get('severity', 'medium'), '💰')
        
        return f"{severity_emoji} {discount_percentage:.0f}% OFF - €{profit_potential:.2f} Profit - {product_title}"
    
    def _generate_alert_html(self, product_data: Dict[str, Any], alert_data: Dict[str, Any]) -> str:
        """Generate HTML email body for arbitrage alert."""
        severity_color = {
            'critical': '#dc3545',
            'high': '#fd7e14', 
            'medium': '#28a745'
        }.get(alert_data.get('severity', 'medium'), '#28a745')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ padding: 20px; }}
                .product-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .price-info {{ display: flex; justify-content: space-between; margin: 10px 0; }}
                .profit-highlight {{ background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; font-weight: bold; text-align: center; }}
                .button {{ display: inline-block; background-color: {severity_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .footer {{ text-align: center; padding: 15px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Arbitrage Opportunity Detected!</h1>
                    <p>Severity: {alert_data.get('severity', 'medium').upper()}</p>
                </div>
                
                <div class="content">
                    <div class="product-info">
                        <h3>{product_data.get('title', 'Unknown Product')}</h3>
                        <p><strong>Brand:</strong> {product_data.get('brand', 'Unknown')}</p>
                        <p><strong>Category:</strong> {product_data.get('category', 'Unknown')}</p>
                        <p><strong>EAN:</strong> {product_data.get('ean', 'Not available')}</p>
                        <p><strong>Stock:</strong> {product_data.get('stock_status', 'Unknown').replace('_', ' ').title()}</p>
                    </div>
                    
                    <div class="price-info">
                        <div>
                            <strong>MediaMarkt Price:</strong><br>
                            €{product_data.get('price', 0):.2f}
                            {f'<br><small>Original: €{product_data.get("original_price", 0):.2f}</small>' if product_data.get('original_price') else ''}
                        </div>
                        <div>
                            <strong>Amazon Average:</strong><br>
                            €{alert_data.get('average_price', 0):.2f}
                        </div>
                        <div>
                            <strong>Discount:</strong><br>
                            {alert_data.get('discount_percentage', 0):.1f}%
                        </div>
                    </div>
                    
                    <div class="profit-highlight">
                        💰 Estimated Profit: €{alert_data.get('profit_potential', 0):.2f}
                        ({alert_data.get('profit_potential', 0) / max(product_data.get('price', 1), 1) * 100:.1f}% ROI)
                    </div>
                    
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="{product_data.get('url', '#')}" class="button">View on MediaMarkt</a>
                        <a href="https://keepa.com/#!product/8-{alert_data.get('asin', '')}" class="button">View Keepa Data</a>
                    </div>
                    
                    <div style="margin-top: 20px; font-size: 12px; color: #6c757d;">
                        <p><strong>Confidence Score:</strong> {alert_data.get('confidence_score', 0):.0%}</p>
                        <p><strong>Detected:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Cross-Market Arbitrage Tool</p>
                    <p>This is an automated alert. Please verify all data before making purchasing decisions.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_alert_text(self, product_data: Dict[str, Any], alert_data: Dict[str, Any]) -> str:
        """Generate plain text email body for arbitrage alert."""
        return f"""
🎯 ARBITRAGE OPPORTUNITY DETECTED!

Product: {product_data.get('title', 'Unknown Product')}
Brand: {product_data.get('brand', 'Unknown')}
Category: {product_data.get('category', 'Unknown')}

PRICING:
MediaMarkt: €{product_data.get('price', 0):.2f}
Amazon Avg: €{alert_data.get('average_price', 0):.2f}
Discount: {alert_data.get('discount_percentage', 0):.1f}%

💰 ESTIMATED PROFIT: €{alert_data.get('profit_potential', 0):.2f}
ROI: {alert_data.get('profit_potential', 0) / max(product_data.get('price', 1), 1) * 100:.1f}%

Stock Status: {product_data.get('stock_status', 'Unknown').replace('_', ' ').title()}
Confidence: {alert_data.get('confidence_score', 0):.0%}
Severity: {alert_data.get('severity', 'medium').upper()}

Links:
MediaMarkt: {product_data.get('url', 'N/A')}
Keepa: https://keepa.com/#!product/8-{alert_data.get('asin', '')}

Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
Cross-Market Arbitrage Tool
This is an automated alert. Please verify all data before making purchasing decisions.
        """.strip()
    
    def _generate_system_notification_html(self, message: str, severity: str) -> str:
        """Generate HTML for system notifications."""
        severity_color = {
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        }.get(severity, '#17a2b8')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ text-align: center; padding: 15px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>System Notification</h2>
                </div>
                <div class="content">
                    <p>{message}</p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Severity:</strong> {severity.upper()}</p>
                </div>
                <div class="footer">
                    <p>Cross-Market Arbitrage Tool</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_system_notification_text(self, message: str, severity: str) -> str:
        """Generate plain text for system notifications."""
        return f"""
SYSTEM NOTIFICATION

{message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Severity: {severity.upper()}

---
Cross-Market Arbitrage Tool
        """.strip()
    
    def _generate_daily_summary_html(self, summary_data: Dict[str, Any]) -> str:
        """Generate HTML for daily summary report."""
        top_opportunities = summary_data.get('top_opportunities', [])
        
        opportunities_html = ""
        for i, opp in enumerate(top_opportunities[:5], 1):
            opportunities_html += f"""
            <tr>
                <td>{i}</td>
                <td>{opp.get('title', 'Unknown')[:40]}...</td>
                <td>€{opp.get('price', 0):.2f}</td>
                <td>{opp.get('discount_percentage', 0):.1f}%</td>
                <td>€{opp.get('profit_potential', 0):.2f}</td>
            </tr>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 700px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: #28a745; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }}
                .content {{ padding: 20px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .stat {{ text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #28a745; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                th {{ background-color: #f8f9fa; }}
                .footer {{ text-align: center; padding: 15px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Daily Arbitrage Summary</h1>
                    <p>{datetime.now().strftime('%Y-%m-%d')}</p>
                </div>
                
                <div class="content">
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-value">{summary_data.get('total_alerts', 0)}</div>
                            <div>Total Alerts</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">€{summary_data.get('total_profit_potential', 0):.2f}</div>
                            <div>Total Profit Potential</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{summary_data.get('products_scraped', 0):,}</div>
                            <div>Products Scraped</div>
                        </div>
                        <div class="stat">
                            <div class="stat-value">{summary_data.get('success_rate', 0):.1f}%</div>
                            <div>Success Rate</div>
                        </div>
                    </div>
                    
                    <h3>🏆 Top Opportunities</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Product</th>
                                <th>Price</th>
                                <th>Discount</th>
                                <th>Profit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {opportunities_html}
                        </tbody>
                    </table>
                </div>
                
                <div class="footer">
                    <p>Cross-Market Arbitrage Tool</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_daily_summary_text(self, summary_data: Dict[str, Any]) -> str:
        """Generate plain text for daily summary."""
        top_opportunities = summary_data.get('top_opportunities', [])
        
        opportunities_text = ""
        for i, opp in enumerate(top_opportunities[:5], 1):
            opportunities_text += f"{i}. {opp.get('title', 'Unknown')[:40]}... - €{opp.get('price', 0):.2f} ({opp.get('discount_percentage', 0):.1f}% off) - Profit: €{opp.get('profit_potential', 0):.2f}\n"
        
        return f"""
📊 DAILY ARBITRAGE SUMMARY - {datetime.now().strftime('%Y-%m-%d')}

STATISTICS:
Total Alerts: {summary_data.get('total_alerts', 0)}
Total Profit Potential: €{summary_data.get('total_profit_potential', 0):.2f}
Products Scraped: {summary_data.get('products_scraped', 0):,}
Success Rate: {summary_data.get('success_rate', 0):.1f}%

🏆 TOP OPPORTUNITIES:
{opportunities_text}

---
Cross-Market Arbitrage Tool
        """.strip()


# Singleton instance
email_notifier = EmailNotifier() 