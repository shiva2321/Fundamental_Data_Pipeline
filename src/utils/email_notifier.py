"""
Email notification system for pipeline status updates.
Sends detailed email reports when processing completes, fails, or encounters errors.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from typing import List, Dict, Optional
import io

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles email notifications for pipeline events."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.email_settings = config.get('email_notifications', {})
        self.enabled = self.email_settings.get('enabled', False)
        self.smtp_server = self.email_settings.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = self.email_settings.get('smtp_port', 587)
        self.sender_email = self.email_settings.get('sender_email', '')
        self.sender_password = self.email_settings.get('sender_password', '')
        self.recipient_email = self.email_settings.get('recipient_email', '')
        
        # Alert preferences
        self.alert_on_complete = self.email_settings.get('alert_on_complete', True)
        self.alert_on_error = self.email_settings.get('alert_on_error', True)
        self.alert_on_ticker_failed = self.email_settings.get('alert_on_ticker_failed', True)
    
    def send_completion_report(self, results: Dict[str, any]):
        """Send email when processing completes."""
        if not self.enabled or not self.alert_on_complete:
            return
        
        subject = f"✓ Profile Generation Complete - {results['total']} Tickers Processed"
        body = self._create_completion_email(results)
        self._send_email(subject, body)
    
    def send_error_report(self, error_info: Dict[str, any]):
        """Send email when critical error occurs."""
        if not self.enabled or not self.alert_on_error:
            return
        
        subject = f"✗ Pipeline Error - {error_info.get('error_type', 'Unknown Error')}"
        body = self._create_error_email(error_info)
        self._send_email(subject, body)
    
    def send_ticker_failure_report(self, ticker: str, error: str, context: Dict):
        """Send email when a ticker fails processing."""
        if not self.enabled or not self.alert_on_ticker_failed:
            return
        
        subject = f"⚠ Ticker Failed - {ticker}"
        body = self._create_ticker_failure_email(ticker, error, context)
        self._send_email(subject, body)
    
    def _create_completion_email(self, results: Dict) -> str:
        """Create HTML email body for completion notification."""
        total = results.get('total', 0)
        successful = results.get('successful', 0)
        failed = results.get('failed', 0)
        duration = results.get('duration', 'N/A')
        tickers = results.get('tickers', [])
        failed_tickers = results.get('failed_tickers', [])
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ background-color: white; border-radius: 8px; padding: 30px; max-width: 800px; margin: 0 auto; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: #198754; color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .status-box {{ background-color: #f8f9fa; border-left: 4px solid #198754; padding: 15px; margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                .metric-label {{ font-size: 12px; color: #6c757d; text-transform: uppercase; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #198754; }}
                .ticker-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 10px 0; }}
                .ticker-badge {{ display: inline-block; background-color: #198754; color: white; padding: 5px 10px; margin: 3px; border-radius: 3px; font-size: 12px; }}
                .failed-badge {{ background-color: #dc3545; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Profile Generation Complete</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Fundamental Data Pipeline</p>
                </div>
                
                <div class="status-box">
                    <div class="metric">
                        <div class="metric-label">Total Processed</div>
                        <div class="metric-value">{total}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Successful</div>
                        <div class="metric-value" style="color: #198754;">{successful}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Failed</div>
                        <div class="metric-value" style="color: #dc3545;">{failed}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Duration</div>
                        <div class="metric-value" style="font-size: 20px; color: #0d6efd;">{duration}</div>
                    </div>
                </div>
                
                <h3>Processing Summary</h3>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td>Started At</td>
                        <td>{results.get('start_time', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Completed At</td>
                        <td>{results.get('end_time', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Success Rate</td>
                        <td>{(successful/total*100) if total > 0 else 0:.1f}%</td>
                    </tr>
                    <tr>
                        <td>Database</td>
                        <td>{results.get('database', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td>Collection</td>
                        <td>{results.get('collection', 'N/A')}</td>
                    </tr>
                </table>
                
                <h3>Successfully Processed Tickers</h3>
                <div class="ticker-list">
                    {' '.join([f'<span class="ticker-badge">{t}</span>' for t in tickers[:50]])}
                    {f'<p style="margin-top: 10px; color: #6c757d;">... and {len(tickers) - 50} more</p>' if len(tickers) > 50 else ''}
                </div>
        """
        
        if failed_tickers:
            html += f"""
                <h3 style="color: #dc3545;">Failed Tickers</h3>
                <div class="ticker-list">
                    {' '.join([f'<span class="ticker-badge failed-badge">{t}</span>' for t in failed_tickers])}
                </div>
            """
        
        html += f"""
                <div class="footer">
                    <p><strong>Fundamental Data Pipeline</strong> - Automated SEC Filing Analysis</p>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_error_email(self, error_info: Dict) -> str:
        """Create HTML email body for error notification."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ background-color: white; border-radius: 8px; padding: 30px; max-width: 800px; margin: 0 auto; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
                .error-box {{ background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .code {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; overflow-x: auto; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✗ Pipeline Error Occurred</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Immediate attention required</p>
                </div>
                
                <div class="error-box">
                    <h3 style="margin-top: 0; color: #dc3545;">Error Type: {error_info.get('error_type', 'Unknown')}</h3>
                    <p><strong>Message:</strong> {error_info.get('message', 'No message provided')}</p>
                </div>
                
                <h3>Error Details</h3>
                <div class="code">
{error_info.get('traceback', 'No traceback available')}
                </div>
                
                <h3>Context</h3>
                <ul>
                    <li><strong>Time:</strong> {error_info.get('timestamp', 'N/A')}</li>
                    <li><strong>Ticker:</strong> {error_info.get('ticker', 'N/A')}</li>
                    <li><strong>Operation:</strong> {error_info.get('operation', 'N/A')}</li>
                </ul>
                
                <div class="footer">
                    <p>Please check the application logs for more details.</p>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_ticker_failure_email(self, ticker: str, error: str, context: Dict) -> str:
        """Create HTML email body for ticker failure notification."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ background-color: white; border-radius: 8px; padding: 30px; max-width: 800px; margin: 0 auto; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ background-color: #ffc107; color: #000; padding: 20px; border-radius: 8px 8px 0 0; margin: -30px -30px 20px -30px; }}
                .warning-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠ Ticker Processing Failed</h1>
                    <p style="margin: 5px 0 0 0;">Ticker: <strong>{ticker}</strong></p>
                </div>
                
                <div class="warning-box">
                    <p><strong>Error:</strong> {error}</p>
                </div>
                
                <h3>Processing Context</h3>
                <ul>
                    <li><strong>Time:</strong> {context.get('timestamp', 'N/A')}</li>
                    <li><strong>Attempt:</strong> {context.get('attempt', 1)} of {context.get('max_attempts', 1)}</li>
                    <li><strong>Lookback Years:</strong> {context.get('lookback_years', 'N/A')}</li>
                    <li><strong>Filing Limit:</strong> {context.get('filing_limit', 'N/A')}</li>
                </ul>
                
                <p>The system will continue processing remaining tickers.</p>
                
                <div class="footer">
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _send_email(self, subject: str, html_body: str):
        """Send email with HTML content."""
        if not self.enabled:
            logger.debug("Email notifications disabled in config")
            return

        if not self.sender_email or not self.recipient_email:
            logger.warning("Email not configured properly. Missing sender or recipient email address.")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            
            # Attach HTML content
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email with better error handling
            logger.debug(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                logger.debug("Starting TLS...")
                server.starttls()

                if self.sender_password:
                    logger.debug(f"Logging in as {self.sender_email}")
                    server.login(self.sender_email, self.sender_password)

                logger.debug(f"Sending email to {self.recipient_email}")
                server.send_message(msg)
            
            logger.info(f"✓ Email notification sent successfully: {subject}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"✗ SMTP Authentication failed. Please check your email credentials: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"✗ SMTP error occurred while sending email: {e}")
        except Exception as e:
            logger.error(f"✗ Failed to send email notification: {e}", exc_info=True)

    def test_connection(self) -> tuple:
        """Test email configuration."""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                if self.sender_password:
                    server.login(self.sender_email, self.sender_password)
            return True, "Connection successful"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Email connection test failed: {error_msg}")
            return False, error_msg

