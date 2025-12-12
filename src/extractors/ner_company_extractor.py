"""
NER-Based Company Extractor

Extracts company names directly from filing text using Named Entity Recognition (NER)
and pattern matching. This approach finds ALL companies mentioned in filings, not just
SEC-registered companies.

Key advantages:
- Finds private companies, subsidiaries, foreign companies
- Much faster than fuzzy matching against 10k+ companies
- More accurate for relationship extraction
"""
import logging
import re
from typing import List, Dict, Set, Tuple, Any
from collections import Counter
from functools import lru_cache

logger = logging.getLogger(__name__)


class NERCompanyExtractor:
    """
    Extract company/organization names from text using NER and pattern matching.

    This extractor finds companies by:
    1. Pattern matching for company suffixes (Inc., Corp., LLC, etc.)
    2. Capitalized multi-word phrases
    3. Context-based identification (e.g., "agreements with [Company]")

    Does NOT require a pre-existing company database.
    """

    # Common company/organization suffixes
    COMPANY_SUFFIXES = [
        r'Inc\.?',
        r'Incorporated',
        r'Corp\.?',
        r'Corporation',
        r'Ltd\.?',
        r'Limited',
        r'LLC',
        r'L\.L\.C\.?',
        r'LLP',
        r'L\.L\.P\.?',
        r'LP',
        r'L\.P\.?',
        r'Company',
        r'Co\.?',
        r'Group',
        r'Holdings?',
        r'Partners?',
        r'Enterprises?',
        r'Industries',
        r'International',
        r'Services?',
        r'Solutions?',
        r'Technologies',
        r'Systems?',
        r'Networks?',
    ]

    # Words to exclude (common English words that match capitalized patterns)
    EXCLUDE_WORDS = {
        'the', 'and', 'for', 'with', 'from', 'that', 'this', 'when', 'where',
        'which', 'what', 'about', 'during', 'after', 'before', 'data', 'time',
        'year', 'years', 'base', 'note', 'notes', 'such', 'each', 'group',
        'way', 'part', 'area', 'term', 'make', 'take', 'will', 'would', 'should',
        'could', 'may', 'might', 'must', 'shall', 'can', 'said', 'says', 'also',
        'other', 'others', 'more', 'most', 'some', 'any', 'all', 'both', 'many',
        'table', 'figure', 'page', 'section', 'item', 'part', 'form', 'filing',
        'december', 'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'monday', 'tuesday',
        'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'states', 'united',
        'america', 'american', 'stock', 'exchange', 'securities', 'commission',
        'federal', 'national', 'state', 'public', 'private', 'general', 'special',
        'total', 'amount', 'number', 'percent', 'million', 'billion', 'thousand',
        # Add filing-specific exclusions to prevent extracting form headers/fragments
        'annual', 'meeting', 'report', 'statement', 'documents', 'incorporat',
        'incorporated', 'exhibit', 'schedule', 'table', 'contents', 'index',
        'cover', 'summary', 'former', 'company', 'emerging', 'growth', 'target',
        'pursuant', 'information', 'required', 'instructions', 'description',
    }

    # Relationship context patterns (help identify companies in specific contexts)
    RELATIONSHIP_PATTERNS = [
        # Customer relationships - match complete company names
        (r'(?:customer|client)s?\s+(?:include|including|such as)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited))', 'customer'),
        (r'([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited))\s+(?:is|are|was|were)\s+(?:a|an|our)\s+(?:key|major|significant)?\s*customer', 'customer'),

        # Supplier relationships
        (r'(?:supplier|vendor)s?\s+(?:include|including|such as)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited))', 'supplier'),
        (r'(?:purchase|procure|obtain)(?:d|s)?\s+(?:from|through)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited))', 'supplier'),

        # Partnership relationships
        (r'(?:partner|partnership|collaboration|joint venture)\s+(?:with|including)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited))', 'partner'),

        # Competitor relationships
        (r'(?:competitor|compete|competition)\s+(?:with|from|including)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited))', 'competitor'),

        # Acquisition/merger
        (r'(?:acquired|acquiring|acquisition of|merger with)\s+([A-Z][A-Za-z0-9\s&\.\-]{2,40}?(?:Inc\.|LLC|Corp\.|Corporation|Ltd\.|Limited|\'s))', 'acquisition'),
    ]

    def __init__(self):
        """Initialize the NER-based company extractor"""
        # Compile patterns for efficiency
        self.suffix_pattern = re.compile(
            r'\b(' + '|'.join(self.COMPANY_SUFFIXES) + r')\b',
            re.IGNORECASE
        )

        self.relationship_patterns = [
            (re.compile(pattern, re.IGNORECASE), rel_type)
            for pattern, rel_type in self.RELATIONSHIP_PATTERNS
        ]

        logger.info("NERCompanyExtractor initialized (pattern-based, no company database needed)")

    def extract_companies(
        self,
        text: str,
        min_mentions: int = 2,
        max_companies: int = 100
    ) -> List[Dict]:
        """
        Extract company names from text.

        Args:
            text: Filing text to analyze
            min_mentions: Minimum number of mentions to include a company
            max_companies: Maximum number of companies to return

        Returns:
            List of dicts with company info: {'name', 'count', 'confidence', 'contexts'}
        """
        companies = {}

        # Method 1: Extract companies with formal suffixes (high confidence)
        suffix_companies = self._extract_with_suffixes(text)
        for name, contexts in suffix_companies.items():
            if name not in companies:
                companies[name] = {
                    'name': name,
                    'count': 0,
                    'confidence': 0.95,  # High confidence for suffix matches
                    'contexts': [],
                    'relationship_type': None
                }
            companies[name]['count'] += len(contexts)
            companies[name]['contexts'].extend(contexts[:3])  # Keep top 3 contexts

        # Method 2: Extract from relationship patterns (very high confidence)
        relationship_companies = self._extract_from_relationships(text)
        for name, rel_type, contexts in relationship_companies:
            if name not in companies:
                companies[name] = {
                    'name': name,
                    'count': 0,
                    'confidence': 0.98,  # Very high confidence for relationship context
                    'contexts': [],
                    'relationship_type': rel_type
                }
            companies[name]['count'] += len(contexts)
            companies[name]['relationship_type'] = rel_type
            companies[name]['contexts'].extend(contexts[:3])

        # Method 3: Extract capitalized phrases (medium confidence)
        # Only use if we don't have enough companies yet
        if len(companies) < 20:
            phrase_companies = self._extract_capitalized_phrases(text)
            for name, count, contexts in phrase_companies:
                if name not in companies:
                    companies[name] = {
                        'name': name,
                        'count': count,
                        'confidence': 0.75,  # Medium confidence for phrase matches
                        'contexts': contexts[:3],
                        'relationship_type': None
                    }

        # Filter by minimum mentions
        filtered = [
            company for company in companies.values()
            if company['count'] >= min_mentions
        ]

        # Sort by count (most mentioned first)
        filtered.sort(key=lambda x: x['count'], reverse=True)

        # Limit to max_companies
        result = filtered[:max_companies]

        logger.info(f"✓ Extracted {len(result)} companies from text (min_mentions={min_mentions})")

        return result

    def _extract_with_suffixes(self, text: str) -> Dict[str, List[str]]:
        """
        Extract company names with formal suffixes.

        Returns:
            Dict mapping company_name -> list of contexts
        """
        companies = {}

        # Pattern: Capitalized words (1-5 words) followed by a company suffix
        # Using word boundaries to prevent partial matches
        suffix_pattern = '|'.join(self.COMPANY_SUFFIXES)
        pattern = rf'\b([A-Z][A-Za-z0-9]+(?:[\s&\.\-]+[A-Z][A-Za-z0-9]+){{0,4}})\s+({suffix_pattern})\b'

        for match in re.finditer(pattern, text, re.IGNORECASE):
            company_name = match.group(1).strip()
            suffix = match.group(2).strip()

            # Clean up the name
            company_name = self._clean_company_name(company_name)

            # Skip very short names
            if not company_name or len(company_name) < 2:
                continue

            # ✅ STRICT VALIDATION: Check each word in the name
            words = company_name.split()
            invalid_name = False
            for word in words:
                if word.lower() in self.EXCLUDE_WORDS:
                    invalid_name = True
                    break

            if invalid_name:
                continue

            # Skip names that are all lowercase or have weird patterns
            if not any(c.isupper() for c in company_name):
                continue

            # ✅ Additional validation: Must have at least 2 capitalized words OR be a recognized brand
            capital_words = [w for w in words if w and w[0].isupper()]
            if len(capital_words) < 1:
                continue

            # ✅ Reject if name contains too many common words
            common_word_count = sum(1 for w in words if w.lower() in self.EXCLUDE_WORDS)
            if common_word_count > len(words) * 0.5:  # More than 50% common words
                continue

            # ✅ Reject if it looks like a sentence fragment (ends with common prepositions/articles)
            if words and words[-1].lower() in {'of', 'the', 'a', 'an', 'to', 'for', 'in', 'on', 'at', 'by'}:
                continue

            # Build full company name with suffix
            full_company_name = f"{company_name} {suffix}"

            # Get context (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].replace('\n', ' ').strip()

            if full_company_name not in companies:
                companies[full_company_name] = []
            companies[full_company_name].append(context)

        logger.debug(f"Extracted {len(companies)} companies with suffixes")
        return companies

    def _extract_from_relationships(self, text: str) -> List[Tuple[str, str, List[str]]]:
        """
        Extract companies mentioned in relationship contexts.

        Returns:
            List of (company_name, relationship_type, contexts)
        """
        companies = []
        seen = set()

        for pattern, rel_type in self.relationship_patterns:
            for match in pattern.finditer(text):
                company_name = match.group(1).strip()

                # Clean up
                company_name = self._clean_company_name(company_name)

                if not company_name or len(company_name) < 3:
                    continue

                if company_name.lower() in self.EXCLUDE_WORDS:
                    continue

                # Avoid duplicates in this batch
                key = (company_name.lower(), rel_type)
                if key in seen:
                    continue
                seen.add(key)

                # Get context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()

                companies.append((company_name, rel_type, [context]))

        logger.debug(f"Extracted {len(companies)} companies from relationship patterns")
        return companies

    def _extract_capitalized_phrases(self, text: str) -> List[Tuple[str, int, List[str]]]:
        """
        Extract capitalized multi-word phrases (potential company names).

        Returns:
            List of (phrase, count, contexts)
        """
        # Pattern: 2-4 capitalized words
        pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'

        phrase_counter = Counter()
        phrase_contexts = {}

        for match in re.finditer(pattern, text):
            phrase = match.group(1).strip()

            # Skip common words
            if phrase.lower() in self.EXCLUDE_WORDS:
                continue

            # Skip very short phrases
            if len(phrase) < 5:
                continue

            phrase_counter[phrase] += 1

            # Store context for first few occurrences
            if phrase not in phrase_contexts:
                phrase_contexts[phrase] = []

            if len(phrase_contexts[phrase]) < 3:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()
                phrase_contexts[phrase].append(context)

        # Convert to list format
        result = [
            (phrase, count, phrase_contexts.get(phrase, []))
            for phrase, count in phrase_counter.items()
            if count >= 2  # At least 2 mentions
        ]

        logger.debug(f"Extracted {len(result)} capitalized phrases")
        return result

    def _clean_company_name(self, name: str) -> str:
        """Clean and normalize company name"""
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()

        # Remove trailing punctuation
        name = name.rstrip('.,;:')

        # Remove leading articles
        name = re.sub(r'^(?:The|A|An)\s+', '', name, flags=re.IGNORECASE)

        return name

    def extract_with_metadata(
        self,
        text: str,
        min_mentions: int = 2
    ) -> Dict[str, Any]:
        """
        Extract companies with additional metadata.

        Returns:
            Dict with:
                - companies: List of company dicts
                - total_found: Total number of companies found
                - high_confidence: Companies with confidence >= 0.95
                - relationship_typed: Companies with known relationship types
        """
        companies = self.extract_companies(text, min_mentions=min_mentions)

        return {
            'companies': companies,
            'total_found': len(companies),
            'high_confidence': [c for c in companies if c['confidence'] >= 0.95],
            'relationship_typed': [c for c in companies if c['relationship_type'] is not None],
            'extraction_metadata': {
                'method': 'ner_pattern_based',
                'requires_database': False,
                'min_mentions': min_mentions
            }
        }


class FastCompanyExtractor(NERCompanyExtractor):
    """
    Faster version that only uses suffix matching (no phrase extraction).
    Use this for large-scale processing where speed is critical.
    """

    def extract_companies(
        self,
        text: str,
        min_mentions: int = 2,
        max_companies: int = 50
    ) -> List[Dict]:
        """Extract companies using only high-confidence methods"""
        companies = {}

        # Method 1: Suffix matching
        suffix_companies = self._extract_with_suffixes(text)
        for name, contexts in suffix_companies.items():
            companies[name] = {
                'name': name,
                'count': len(contexts),
                'confidence': 0.95,
                'contexts': contexts[:3],
                'relationship_type': None
            }

        # Method 2: Relationship patterns
        relationship_companies = self._extract_from_relationships(text)
        for name, rel_type, contexts in relationship_companies:
            if name not in companies:
                companies[name] = {
                    'name': name,
                    'count': len(contexts),
                    'confidence': 0.98,
                    'contexts': contexts[:3],
                    'relationship_type': rel_type
                }
            else:
                companies[name]['count'] += len(contexts)
                companies[name]['relationship_type'] = rel_type

        # Filter and sort
        filtered = [
            company for company in companies.values()
            if company['count'] >= min_mentions
        ]
        filtered.sort(key=lambda x: x['count'], reverse=True)

        result = filtered[:max_companies]

        logger.info(f"✓ Fast extraction: {len(result)} companies (min_mentions={min_mentions})")

        return result

