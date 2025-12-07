"""
Failure tracking system for monitoring failed tickers during processing.
Stores failure reasons and allows retry/delete operations.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class FailureReason(Enum):
    """Enumeration of possible failure reasons."""
    COMPANY_NOT_FOUND = "Company not found in database"
    CIK_LOOKUP_FAILED = "Failed to lookup CIK"
    NO_FILINGS = "No filings available for this company"
    FILING_FETCH_ERROR = "Failed to fetch filings from SEC"
    DATA_EXTRACTION_ERROR = "Failed to extract data from filings"
    INSUFFICIENT_DATA = "Insufficient data for analysis"
    AI_ANALYSIS_FAILED = "AI analysis generation failed"
    PROFILE_SAVE_ERROR = "Failed to save profile to database"
    TIMEOUT_ERROR = "Processing timeout"
    UNKNOWN_ERROR = "Unknown error occurred"
    CANCELLED = "Processing cancelled by user"


class FailureTracker:
    """Tracks failed tickers with detailed failure information."""

    def __init__(self):
        self.failures: Dict[str, Dict] = {}  # ticker -> {reason, timestamp, error_msg, details}
        self.retry_count: Dict[str, int] = {}  # ticker -> retry count

    def track_failure(self, ticker: str, reason: FailureReason,
                     error_msg: str = "", details: Dict = None, context: Dict = None):
        """
        Track a failed ticker with detailed information.

        Args:
            ticker: Ticker symbol
            reason: FailureReason enum
            error_msg: Detailed error message
            details: Additional context/details
            context: Processing context (lookback_years, filing_limit, etc)
        """
        self.failures[ticker] = {
            'ticker': ticker,
            'reason': reason.value,
            'reason_code': reason.name,
            'error_message': error_msg,
            'timestamp': datetime.now().isoformat(),
            'details': details or {},
            'context': context or {},
            'retry_attempts': self.retry_count.get(ticker, 0)
        }
        logger.warning(f"Failure tracked for {ticker}: {reason.value} - {error_msg}")

    def mark_retry(self, ticker: str):
        """Mark a ticker for retry."""
        self.retry_count[ticker] = self.retry_count.get(ticker, 0) + 1
        if ticker in self.failures:
            self.failures[ticker]['retry_attempts'] = self.retry_count[ticker]

    def get_failed_tickers(self) -> List[str]:
        """Get list of all failed tickers."""
        return list(self.failures.keys())

    def get_failure_info(self, ticker: str) -> Optional[Dict]:
        """Get detailed failure information for a ticker."""
        return self.failures.get(ticker)

    def get_failures_by_reason(self, reason: FailureReason) -> List[str]:
        """Get all tickers that failed for a specific reason."""
        return [ticker for ticker, info in self.failures.items()
                if info['reason_code'] == reason.name]

    def get_failure_summary(self) -> Dict:
        """Get summary of all failures."""
        summary = {
            'total_failures': len(self.failures),
            'failures_by_reason': {},
            'failures_by_retry_count': {}
        }

        for ticker, info in self.failures.items():
            reason_code = info['reason_code']
            retry_count = info['retry_attempts']

            # Count by reason
            if reason_code not in summary['failures_by_reason']:
                summary['failures_by_reason'][reason_code] = []
            summary['failures_by_reason'][reason_code].append(ticker)

            # Count by retry attempts
            if retry_count not in summary['failures_by_retry_count']:
                summary['failures_by_retry_count'][retry_count] = []
            summary['failures_by_retry_count'][retry_count].append(ticker)

        return summary

    def remove_failure(self, ticker: str) -> bool:
        """Remove a ticker from failure tracking (after successful retry)."""
        if ticker in self.failures:
            del self.failures[ticker]
            if ticker in self.retry_count:
                del self.retry_count[ticker]
            logger.info(f"Removed {ticker} from failure tracking")
            return True
        return False

    def clear_failures(self):
        """Clear all tracked failures."""
        self.failures.clear()
        self.retry_count.clear()
        logger.info("All failures cleared")

    def export_failures(self) -> str:
        """Export failures as JSON string."""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_failures': len(self.failures),
            'failures': self.failures,
            'retry_counts': self.retry_count
        }
        return json.dumps(export_data, indent=2)

    def get_formatted_failure_report(self) -> str:
        """Get human-readable failure report."""
        if not self.failures:
            return "No failures recorded."

        report = f"Failure Report ({len(self.failures)} failures)\n"
        report += "=" * 80 + "\n\n"

        # Group by reason
        summary = self.get_failure_summary()

        for reason_code, tickers in summary['failures_by_reason'].items():
            report += f"\n{reason_code}: {len(tickers)} failures\n"
            report += "-" * 80 + "\n"

            for ticker in sorted(tickers):
                info = self.failures[ticker]
                report += f"  • {ticker}\n"
                report += f"    Error: {info['error_message']}\n"
                if info['retry_attempts'] > 0:
                    report += f"    Retries: {info['retry_attempts']}\n"
                report += f"    Time: {info['timestamp']}\n\n"

        return report

