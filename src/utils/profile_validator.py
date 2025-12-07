"""
Profile Validation and Inconsistency Detection System.
Identifies incomplete, out-of-order, inconsistent, or improper profiles.
"""
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ProfileValidator:
    """Validates and identifies issues with company profiles."""

    @staticmethod
    def validate_profile(profile: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """
        Validate a profile for completeness and consistency.

        Returns:
            (is_valid, status_message, list_of_issues)
        """
        issues = []

        if not profile:
            return False, "Profile is empty or None", ["Profile is null"]

        # Check for critical missing fields
        required_top_level = ['cik', 'company_info', 'filing_metadata', 'generated_at']
        for field in required_top_level:
            if field not in profile or profile[field] is None:
                issues.append(f"INCOMPLETE: Missing required field: {field}")

        # Check company_info structure
        if 'company_info' in profile and profile['company_info']:
            company_info = profile['company_info']
            if not isinstance(company_info, dict):
                issues.append(f"INCONSISTENT: company_info is not a dictionary, got {type(company_info)}")
            else:
                # Check for essential company fields
                for field in ['ticker', 'name', 'cik']:
                    if field not in company_info or not company_info[field]:
                        issues.append(f"INCOMPLETE: Missing company_info.{field}")

        # Check filing_metadata structure
        if 'filing_metadata' in profile and profile['filing_metadata']:
            meta = profile['filing_metadata']
            if not isinstance(meta, dict):
                issues.append(f"INCONSISTENT: filing_metadata is not a dictionary")
            else:
                # Check for date fields
                for field in ['oldest_filing', 'most_recent_filing']:
                    if field not in meta or meta[field] is None:
                        issues.append(f"INCOMPLETE: Missing filing_metadata.{field}")

                # Check filing count
                if 'total_filings' not in meta or meta['total_filings'] is None:
                    issues.append(f"INCOMPLETE: Missing filing_metadata.total_filings")

                # Check date consistency
                try:
                    oldest = meta.get('oldest_filing')
                    most_recent = meta.get('most_recent_filing')
                    if oldest and most_recent:
                        oldest_dt = datetime.fromisoformat(str(oldest))
                        recent_dt = datetime.fromisoformat(str(most_recent))
                        if oldest_dt > recent_dt:
                            issues.append(f"OUT_OF_ORDER: oldest_filing ({oldest}) is after most_recent_filing ({most_recent})")
                except (ValueError, TypeError, AttributeError):
                    pass  # Date parsing failed but that's already tracked above

        # Check financial_metrics - this is critical
        if 'financial_metrics' not in profile or profile['financial_metrics'] is None:
            issues.append(f"INCOMPLETE: Missing required field: financial_metrics")
        elif not isinstance(profile['financial_metrics'], dict):
            issues.append(f"INCOMPLETE: financial_metrics is not a dictionary")
        elif len(profile['financial_metrics']) == 0:
            issues.append(f"INCOMPLETE: financial_metrics dictionary is empty - no financial data extracted")
        else:
            # Check for key financial data
            metrics = profile['financial_metrics']

            # Check revenue data
            if 'revenue_data' not in metrics or not metrics.get('revenue_data'):
                issues.append(f"INCOMPLETE: Missing revenue_data in financial_metrics")

            # Check profitability metrics
            if 'profitability_metrics' not in metrics or not metrics.get('profitability_metrics'):
                issues.append(f"INCOMPLETE: Missing profitability_metrics in financial_metrics")

        # Check AI analysis quality (if present)
        if 'ai_analysis' in profile and profile['ai_analysis']:
            ai = profile['ai_analysis']
            if isinstance(ai, dict):
                # Check summary
                summary = ai.get('summary', '')
                if not summary or (isinstance(summary, str) and len(summary.strip()) < 20):
                    issues.append(f"IMPROPER: AI analysis summary is empty or too short (< 20 chars)")

                # Check key insights
                insights = ai.get('key_insights', [])
                if not insights or not isinstance(insights, list) or len(insights) == 0:
                    issues.append(f"IMPROPER: AI analysis has no key insights")
        elif 'ai_analysis' in profile:
            # AI analysis field exists but is empty/null
            issues.append(f"IMPROPER: AI analysis is empty or null")

        # Check generated_at timestamp
        if 'generated_at' in profile and profile['generated_at']:
            try:
                datetime.fromisoformat(str(profile['generated_at']))
            except (ValueError, TypeError):
                issues.append(f"INCONSISTENT: generated_at is not a valid ISO datetime string")

        # Determine final status
        if not issues:
            return True, "✓ Profile is VALID and complete", []

        # Categorize issues for status message
        incomplete_count = len([i for i in issues if 'INCOMPLETE' in i])
        improper_count = len([i for i in issues if 'IMPROPER' in i])
        other_count = len([i for i in issues if 'INCOMPLETE' not in i and 'IMPROPER' not in i])

        status_parts = []
        if incomplete_count > 0:
            status_parts.append(f"Incomplete: {incomplete_count}")
        if improper_count > 0:
            status_parts.append(f"Improper: {improper_count}")
        if other_count > 0:
            status_parts.append(f"Other: {other_count}")

        status = "❌ " + " | ".join(status_parts) if status_parts else "❌ Issues found"
        return False, status, issues

    @staticmethod
    def get_issue_category(issue: str) -> str:
        """Categorize an issue type."""
        if 'INCOMPLETE' in issue:
            return 'INCOMPLETE'
        elif 'OUT_OF_ORDER' in issue:
            return 'OUT_OF_ORDER'
        elif 'INCONSISTENT' in issue:
            return 'INCONSISTENT'
        else:
            return 'IMPROPER'

    @staticmethod
    def categorize_issues(issues: List[str]) -> Dict[str, List[str]]:
        """Categorize all issues by type."""
        categorized = {
            'INCOMPLETE': [],
            'OUT_OF_ORDER': [],
            'INCONSISTENT': [],
            'IMPROPER': []
        }

        for issue in issues:
            category = ProfileValidator.get_issue_category(issue)
            categorized[category].append(issue)

        return categorized

    @staticmethod
    def should_retry(profile: Dict[str, Any]) -> bool:
        """Determine if a profile should be retried."""
        is_valid, _, issues = ProfileValidator.validate_profile(profile)
        return not is_valid and len(issues) > 0

    @staticmethod
    def get_retry_reason(profile: Dict[str, Any]) -> str:
        """Get human-readable reason why profile should be retried."""
        is_valid, status, issues = ProfileValidator.validate_profile(profile)

        if is_valid:
            return "Profile is valid - no retry needed"

        categorized = ProfileValidator.categorize_issues(issues)

        reasons = []
        if categorized['INCOMPLETE']:
            reasons.append(f"Incomplete ({len(categorized['INCOMPLETE'])} issues)")
        if categorized['OUT_OF_ORDER']:
            reasons.append(f"Out-of-order ({len(categorized['OUT_OF_ORDER'])} issues)")
        if categorized['INCONSISTENT']:
            reasons.append(f"Inconsistent ({len(categorized['INCONSISTENT'])} issues)")
        if categorized['IMPROPER']:
            reasons.append(f"Improper ({len(categorized['IMPROPER'])} issues)")

        return " | ".join(reasons) if reasons else "Unknown issues"


class ProfileQualityAnalyzer:
    """Analyzes profile quality and completeness."""

    @staticmethod
    def analyze_profile_quality(profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze overall quality of a profile.

        Returns quality metrics dict with:
        - overall_score (0-100)
        - completeness_pct
        - data_integrity_score
        - issue_count
        - categories
        """
        is_valid, status, issues = ProfileValidator.validate_profile(profile)
        categorized = ProfileValidator.categorize_issues(issues)

        # Calculate scores
        issue_count = len(issues)
        max_issues = 10  # After this many, quality score approaches 0
        completeness_pct = max(0, 100 - (issue_count / max_issues * 100))

        # Data integrity based on presence of key data
        integrity_checks = 0
        integrity_passed = 0

        # Check financial data
        if 'financial_metrics' in profile and profile['financial_metrics']:
            integrity_checks += 1
            if isinstance(profile['financial_metrics'], dict) and len(profile['financial_metrics']) > 0:
                integrity_passed += 1

        # Check AI analysis
        if 'ai_analysis' in profile and profile['ai_analysis']:
            integrity_checks += 1
            if isinstance(profile['ai_analysis'], dict):
                summary = profile['ai_analysis'].get('summary', '')
                if summary and len(str(summary).strip()) > 20:
                    integrity_passed += 1

        # Check trends
        if 'trend_analysis' in profile and profile['trend_analysis']:
            integrity_checks += 1
            if isinstance(profile['trend_analysis'], (dict, list)) and len(profile['trend_analysis']) > 0:
                integrity_passed += 1

        # Check filing metadata
        if 'filing_metadata' in profile and profile['filing_metadata']:
            integrity_checks += 1
            if isinstance(profile['filing_metadata'], dict) and profile['filing_metadata'].get('total_filings', 0) > 0:
                integrity_passed += 1

        integrity_score = (integrity_passed / max(1, integrity_checks)) * 100 if integrity_checks > 0 else 0

        # Overall score (weighted average)
        overall_score = (completeness_pct * 0.6 + integrity_score * 0.4)

        return {
            'overall_score': round(overall_score, 1),
            'completeness_pct': round(completeness_pct, 1),
            'data_integrity_score': round(integrity_score, 1),
            'is_valid': is_valid,
            'issue_count': issue_count,
            'categories': categorized,
            'status': status
        }

    @staticmethod
    def get_quality_label(score: float) -> str:
        """Get human-readable quality label for a score."""
        if score >= 95:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"



