"""
Company Mention Extractor

Extracts company references from SEC filing text using fuzzy matching
against known company database.
"""
import logging
import re
from typing import List, Tuple, Dict, Set, Optional
from functools import lru_cache
from fuzzywuzzy import fuzz, process

logger = logging.getLogger(__name__)


class CompanyMentionExtractor:
    """
    Extract company references from SEC filing text using fuzzy matching
    against known company database.

    Handles:
    - Exact company name matches
    - Ticker symbol matches ($AAPL, MSFT)
    - Fuzzy matching with high confidence threshold
    - Deduplication and confidence scoring
    """

    def __init__(self, all_companies: List[Dict]):
        """
        Initialize with company database.

        Args:
            all_companies: List of dicts with 'name', 'ticker', 'cik'
        """
        self.all_companies = all_companies

        # Build lookup indices for fast matching
        self.names_index = {(c.get('name') or c.get('title', 'Unknown')).lower(): c['cik'] for c in all_companies if c.get('name') or c.get('title')}
        self.tickers_index = {c['ticker'].lower(): c['cik'] for c in all_companies if c.get('ticker')}
        self.aliases_index = self._build_aliases()

        logger.info(f"CompanyMentionExtractor initialized with {len(all_companies)} companies")

    def _build_aliases(self) -> Dict[str, str]:
        """
        Build alternate company name aliases.
        E.g., "Apple Inc" -> "Apple", "TSMC" -> variants
        """
        aliases = {}

        for company in self.all_companies:
            name = (company.get('name') or company.get('title', 'Unknown')).lower()
            ticker = company.get('ticker', '').lower()
            cik = company['cik']

            # Add base name (remove Inc, Corp, LLC, Ltd, etc.)
            base_name = re.sub(
                r'\s+(?:Inc|Inc\.|Corporation|Corp|LLC|Ltd|Ltd\.|Company|Co\.|&|and)$',
                '',
                name
            ).strip()
            if base_name:
                aliases[base_name] = cik

            # Add ticker
            if ticker:
                aliases[ticker] = cik

        return aliases

    def extract_mentions(self, text: str, threshold: float = 0.82) -> List[Tuple[str, str, float]]:
        """
        Extract company mentions from text.

        Args:
            text: Filing text to search
            threshold: Fuzzy match confidence threshold (0.0-1.0)

        Returns:
            List of (cik, company_name, confidence_score) tuples
        """
        mentions = []
        seen_ciks = set()

        try:
            # 1. EXACT MATCHES (highest confidence = 0.99)
            exact_mentions = self._find_exact_matches(text)
            for cik, name, conf in exact_mentions:
                if cik not in seen_ciks:
                    mentions.append((cik, name, conf))
                    seen_ciks.add(cik)

            # 2. TICKER MATCHES (very high confidence = 0.98)
            ticker_mentions = self._find_ticker_matches(text)
            for cik, ticker, conf in ticker_mentions:
                if cik not in seen_ciks:
                    mentions.append((cik, ticker, conf))
                    seen_ciks.add(cik)

            # 3. FUZZY MATCHES (medium-high confidence = varies)
            fuzzy_mentions = self._find_fuzzy_matches(text, threshold)
            for cik, name, conf in fuzzy_mentions:
                if cik not in seen_ciks:
                    mentions.append((cik, name, conf))
                    seen_ciks.add(cik)

            logger.debug(f"Extracted {len(mentions)} company mentions from text")

        except Exception as e:
            logger.error(f"Error extracting mentions: {e}")

        return mentions

    def _find_exact_matches(self, text: str) -> List[Tuple[str, str, float]]:
        """Find exact company name matches (case-insensitive)"""
        matches = []
        text_lower = text.lower()

        for name_lower, cik in self.names_index.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(name_lower) + r'\b'
            if re.search(pattern, text_lower):
                matches.append((cik, name_lower.title(), 0.99))

        return matches

    def _find_ticker_matches(self, text: str) -> List[Tuple[str, str, float]]:
        """
        Find ticker symbol matches.
        Patterns:
        - $AAPL (dollar sign prefix)
        - AAPL (uppercase, word boundary)
        """
        matches = []

        # Pattern: $TICKER or standalone TICKER in caps
        ticker_pattern = r'\$([A-Z]{1,5})\b|(?:^|\s)([A-Z]{1,5})(?:\s|:|,|\.)'

        for match in re.finditer(ticker_pattern, text):
            ticker = (match.group(1) or match.group(2)).lower()

            if ticker in self.tickers_index:
                cik = self.tickers_index[ticker]
                matches.append((cik, ticker.upper(), 0.98))

        return matches

    def _find_fuzzy_matches(self, text: str, threshold: float) -> List[Tuple[str, str, float]]:
        """
        Find fuzzy company name matches using FuzzyWuzzy.
        OPTIMIZED VERSION: Reduces search space dramatically

        Args:
            text: Text to search
            threshold: Match confidence threshold (0-1 scale)

        Returns:
            List of fuzzy match results
        """
        matches = []
        start_time = __import__('time').time()

        # OPTIMIZATION 1: Extract unique capitalized phrases (dedup before fuzzy matching)
        company_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b'

        potential_names = set()
        name_counts = {}

        for match in re.finditer(company_pattern, text):
            potential_name = match.group(1).lower()

            # Skip very short words or common English words
            if len(potential_name) < 4 or potential_name in {
                'the', 'and', 'for', 'with', 'from', 'that', 'this', 'when',
                'where', 'which', 'what', 'about', 'during', 'after', 'before',
                'data', 'time', 'year', 'base', 'note', 'such', 'each', 'group',
                'way', 'part', 'area', 'term', 'make', 'take', 'will', 'would'
            }:
                continue

            potential_names.add(potential_name)
            name_counts[potential_name] = name_counts.get(potential_name, 0) + 1

        total_names = len(potential_names)
        logger.info(f"Fuzzy matching {total_names} unique phrases (from {sum(name_counts.values())} occurrences)")

        # OPTIMIZATION 2: Aggressive limiting - reduce to top 30 phrases only (not 50)
        # Most company mentions are in top phrases, rest are noise
        if total_names > 30:
            sorted_names = sorted(name_counts.items(), key=lambda x: x[1], reverse=True)
            potential_names = {name for name, count in sorted_names[:30]}
            logger.info(f"Limiting to top 30 phrases (from {total_names} total)")

        # OPTIMIZATION 3: Filter company database - only match against companies with 3+ char names
        # This cuts search space from ~9000 to ~6000 companies
        filtered_company_names = [
            name for name in self.names_index.keys()
            if len(name) > 3
        ]

        if not filtered_company_names:
            return matches

        # Process each unique phrase - limited set now
        for idx, potential_name in enumerate(potential_names, 1):
            # Skip if fuzzy matching would take too long (prevent timeout)
            elapsed = __import__('time').time() - start_time
            if elapsed > 10:  # 10 second timeout for entire fuzzy matching
                logger.warning(f"Fuzzy matching timeout after {elapsed:.1f}s - stopping early")
                break

            # Fuzzy match against filtered company names
            # Using token_set_ratio is slower but more accurate
            # For speed, we could use simple token_ratio or partial_ratio
            result = process.extractOne(
                potential_name,
                filtered_company_names,
                scorer=fuzz.token_set_ratio,
                score_cutoff=int(threshold * 100)
            )

            if result is None:
                continue

            best_match, score = result

            if best_match and score >= (threshold * 100):
                cik = self.names_index[best_match]
                confidence = score / 100.0
                matches.append((cik, best_match.title(), confidence))

        elapsed = __import__('time').time() - start_time
        logger.info(f"Fuzzy matching complete in {elapsed:.2f}s: Found {len(matches)} matches from {len(potential_names)} phrases")
        return matches


class CompanyMentionExtractorWithAliases(CompanyMentionExtractor):
    """
    Enhanced version that also uses company aliases for matching.
    Useful for known alternative names.
    """

    def __init__(self, all_companies: List[Dict], custom_aliases: Optional[Dict[str, str]] = None):
        """
        Initialize with custom aliases.

        Args:
            all_companies: List of company dicts
            custom_aliases: Dict mapping alias -> cik
        """
        super().__init__(all_companies)

        if custom_aliases:
            self.aliases_index.update(custom_aliases)
            logger.info(f"Added {len(custom_aliases)} custom aliases")

    def _find_alias_matches(self, text: str) -> List[Tuple[str, str, float]]:
        """Find matches using aliases"""
        matches = []
        text_lower = text.lower()

        for alias_lower, cik in self.aliases_index.items():
            pattern = r'\b' + re.escape(alias_lower) + r'\b'
            if re.search(pattern, text_lower):
                matches.append((cik, alias_lower.title(), 0.95))

        return matches

    def extract_mentions(self, text: str, threshold: float = 0.82) -> List[Tuple[str, str, float]]:
        """Extract mentions using all methods including aliases"""
        mentions = []
        seen_ciks = set()

        try:
            # 1. Exact matches (0.99)
            for cik, name, conf in self._find_exact_matches(text):
                if cik not in seen_ciks:
                    mentions.append((cik, name, conf))
                    seen_ciks.add(cik)

            # 2. Ticker matches (0.98)
            for cik, name, conf in self._find_ticker_matches(text):
                if cik not in seen_ciks:
                    mentions.append((cik, name, conf))
                    seen_ciks.add(cik)

            # 3. Alias matches (0.95)
            for cik, name, conf in self._find_alias_matches(text):
                if cik not in seen_ciks:
                    mentions.append((cik, name, conf))
                    seen_ciks.add(cik)

            # 4. Fuzzy matches
            for cik, name, conf in self._find_fuzzy_matches(text, threshold):
                if cik not in seen_ciks:
                    mentions.append((cik, name, conf))
                    seen_ciks.add(cik)

        except Exception as e:
            logger.error(f"Error extracting mentions: {e}")

        return mentions

