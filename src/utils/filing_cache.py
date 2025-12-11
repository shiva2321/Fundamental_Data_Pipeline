"""
Filing Cache System

Caches SEC filings to disk to avoid refetching during testing and development.
Maximum cache size: 2GB with automatic cleanup of oldest entries.
"""
import os
import json
import pickle
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class FilingCache:
    """
    Manages a disk-based cache for SEC filings.

    Features:
    - 2GB maximum size with LRU eviction
    - Per-ticker organization
    - Metadata tracking (form types, dates, file sizes)
    - Easy clearing (individual ticker or all)
    """

    def __init__(self, cache_dir: Optional[str] = None, max_size_gb: float = 2.0):
        """
        Initialize the filing cache.

        Args:
            cache_dir: Directory for cache storage (default: ./cache/filings)
            max_size_gb: Maximum cache size in GB (default: 2.0)
        """
        self.cache_dir = Path(cache_dir or './cache/filings')
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.metadata_file = self.cache_dir / 'cache_metadata.json'

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load or initialize metadata
        self.metadata = self._load_metadata()

        # Check and enforce size limit
        self._enforce_size_limit()

    def _load_metadata(self) -> Dict:
        """Load cache metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load cache metadata: {e}")

        return {
            'tickers': {},  # ticker -> {cik, last_accessed, filings: [{form, date, size}]}
            'total_size': 0,
            'created_at': datetime.now().isoformat()
        }

    def _save_metadata(self):
        """Save cache metadata to disk"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save cache metadata: {e}")

    def _get_cache_key(self, cik: str) -> str:
        """Generate cache key for a ticker's filings - one cache per CIK"""
        # Store ALL filings for a CIK, filter by date when retrieving
        return hashlib.md5(cik.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cached data"""
        return self.cache_dir / f"{cache_key}.pkl"

    def get_cached_filings(
        self,
        cik: str,
        ticker: str,
        lookback_years: int
    ) -> Optional[List[Dict]]:
        """
        Get cached filings for a ticker, intelligently filtered by date range.

        Args:
            cik: Company CIK
            ticker: Stock ticker
            lookback_years: Years of filings to retrieve

        Returns:
            List of filing dicts if cached (full or partial), None otherwise
        """
        cache_key = self._get_cache_key(cik)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            # Load ALL cached filings for this ticker
            with open(cache_path, 'rb') as f:
                all_cached_filings = pickle.load(f)

            # Filter by lookback period
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=lookback_years * 365)

            filtered_filings = []
            for filing in all_cached_filings:
                filing_date_str = filing.get('filingDate') or filing.get('filing_date')
                if filing_date_str:
                    try:
                        filing_date = datetime.fromisoformat(filing_date_str.replace('Z', ''))
                        if filing_date >= cutoff_date:
                            filtered_filings.append(filing)
                    except:
                        # If date parsing fails, include it anyway
                        filtered_filings.append(filing)
                else:
                    # No date, include it
                    filtered_filings.append(filing)

            # Update last accessed time
            if ticker in self.metadata['tickers']:
                self.metadata['tickers'][ticker]['last_accessed'] = datetime.now().isoformat()
                self._save_metadata()

            # Determine cache quality
            coverage = (len(filtered_filings) / len(all_cached_filings) * 100) if all_cached_filings else 0

            if len(filtered_filings) > 0:
                logger.info(f"✓ Cache HIT for {ticker} ({lookback_years}y): {len(filtered_filings)} filings "
                          f"(filtered from {len(all_cached_filings)} total, {coverage:.0f}% coverage)")
                return filtered_filings
            else:
                logger.info(f"✗ Cache PARTIAL for {ticker}: Have {len(all_cached_filings)} filings but none in {lookback_years}y range")
                return None

        except Exception as e:
            logger.warning(f"Cache read error for {ticker}: {e}")
            # Remove corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None

    def cache_filings(
        self,
        cik: str,
        ticker: str,
        filings: List[Dict],
        lookback_years: int
    ):
        """
        Cache filings for a ticker, intelligently merging with existing cache.

        Args:
            cik: Company CIK
            ticker: Stock ticker
            filings: List of filing dicts to cache
            lookback_years: Years of filings being cached (for metadata only)
        """
        cache_key = self._get_cache_key(cik)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Load existing cache if it exists
            existing_filings = []
            if cache_path.exists():
                try:
                    with open(cache_path, 'rb') as f:
                        existing_filings = pickle.load(f)
                    logger.info(f"Merging with existing cache: {len(existing_filings)} filings")
                except Exception as e:
                    logger.warning(f"Could not load existing cache: {e}")

            # Merge filings intelligently (avoid duplicates)
            merged_filings = self._merge_filings(existing_filings, filings)

            # Save merged filings to cache
            with open(cache_path, 'wb') as f:
                pickle.dump(merged_filings, f)

            file_size = cache_path.stat().st_size

            # Update metadata
            if ticker not in self.metadata['tickers']:
                self.metadata['tickers'][ticker] = {
                    'cik': cik,
                    'first_cached': datetime.now().isoformat(),
                    'last_accessed': datetime.now().isoformat(),
                    'total_filings': len(merged_filings),
                    'file_size': file_size,
                    'cache_key': cache_key,
                    'last_updated': datetime.now().isoformat()
                }
            else:
                # Update existing ticker metadata
                old_size = self.metadata['tickers'][ticker].get('file_size', 0)
                self.metadata['total_size'] -= old_size

                self.metadata['tickers'][ticker].update({
                    'total_filings': len(merged_filings),
                    'file_size': file_size,
                    'last_accessed': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                })

            self.metadata['total_size'] += file_size
            self._save_metadata()

            # Enforce size limit
            self._enforce_size_limit()

            if len(existing_filings) > 0:
                added_count = len(merged_filings) - len(existing_filings)
                logger.info(f"✓ Updated cache for {ticker}: {len(merged_filings)} total filings "
                          f"(+{added_count} new): {file_size / 1024 / 1024:.2f} MB")
            else:
                logger.info(f"✓ Cached {len(merged_filings)} filings for {ticker}: {file_size / 1024 / 1024:.2f} MB")

        except Exception as e:
            logger.error(f"Could not cache filings for {ticker}: {e}")

    def _merge_filings(self, existing: List[Dict], new: List[Dict]) -> List[Dict]:
        """
        Intelligently merge filings, avoiding duplicates.

        Args:
            existing: Existing cached filings
            new: New filings to merge

        Returns:
            Merged list without duplicates
        """
        # Create index of existing filings by accession number
        existing_index = {}
        for filing in existing:
            accession = filing.get('accessionNumber') or filing.get('accession_number')
            if accession:
                existing_index[accession] = filing

        # Add new filings that don't exist
        added_count = 0
        for filing in new:
            accession = filing.get('accessionNumber') or filing.get('accession_number')
            if accession:
                if accession not in existing_index:
                    existing_index[accession] = filing
                    added_count += 1
                # If exists, keep the existing one (assume it's already processed)
            else:
                # No accession number, add it anyway
                existing.append(filing)
                added_count += 1

        if added_count > 0:
            logger.info(f"Merged: Added {added_count} new filings to cache")

        # Return all filings
        return list(existing_index.values())

    def _extract_form_types(self, filings: List[Dict]) -> Dict[str, int]:
        """Extract form type counts from filings"""
        form_counts = defaultdict(int)
        for filing in filings:
            form_type = filing.get('form', 'Unknown')
            form_counts[form_type] += 1
        return dict(form_counts)

    def _extract_date_range(self, filings: List[Dict]) -> Dict[str, str]:
        """Extract date range from filings"""
        dates = []
        for filing in filings:
            filing_date = filing.get('filingDate') or filing.get('filing_date')
            if filing_date:
                dates.append(filing_date)

        if dates:
            dates_sorted = sorted(dates)
            return {
                'from': dates_sorted[0],
                'to': dates_sorted[-1]
            }
        return {'from': 'N/A', 'to': 'N/A'}

    def clear_ticker_cache(self, ticker: str) -> bool:
        """
        Clear all cached filings for a specific ticker.

        Args:
            ticker: Stock ticker to clear

        Returns:
            True if cleared successfully
        """
        if ticker not in self.metadata['tickers']:
            return False

        try:
            ticker_data = self.metadata['tickers'][ticker]
            cache_key = ticker_data.get('cache_key')
            file_size = ticker_data.get('file_size', 0)

            # Delete cache file
            if cache_key:
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    cache_path.unlink()
                    self.metadata['total_size'] -= file_size

            # Remove from metadata
            del self.metadata['tickers'][ticker]
            self._save_metadata()

            logger.info(f"Cleared cache for {ticker}")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache for {ticker}: {e}")
            return False

    def clear_all_cache(self) -> bool:
        """
        Clear entire cache.

        Returns:
            True if cleared successfully
        """
        try:
            # Delete all cache files
            for ticker_data in self.metadata['tickers'].values():
                for entry in ticker_data['cache_entries']:
                    cache_key = entry['cache_key']
                    cache_path = self._get_cache_path(cache_key)
                    cache_path.unlink(missing_ok=True)

            # Reset metadata
            self.metadata = {
                'tickers': {},
                'total_size': 0,
                'created_at': datetime.now().isoformat()
            }
            self._save_metadata()

            logger.info("Cleared entire cache")
            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def _enforce_size_limit(self):
        """Enforce maximum cache size by removing least recently used tickers"""
        if self.metadata['total_size'] <= self.max_size_bytes:
            return

        logger.info(f"Cache size ({self.metadata['total_size'] / 1024 / 1024 / 1024:.2f} GB) exceeds limit, cleaning up...")

        # Get all tickers sorted by last accessed time (oldest first)
        ticker_list = []
        for ticker, ticker_data in self.metadata['tickers'].items():
            last_accessed = datetime.fromisoformat(ticker_data['last_accessed'])
            ticker_list.append((last_accessed, ticker, ticker_data))

        ticker_list.sort(key=lambda x: x[0])

        # Remove oldest tickers until under limit
        for last_accessed, ticker, ticker_data in ticker_list:
            if self.metadata['total_size'] <= self.max_size_bytes:
                break

            cache_key = ticker_data.get('cache_key')
            file_size = ticker_data.get('file_size', 0)

            # Delete cache file
            if cache_key:
                cache_path = self._get_cache_path(cache_key)
                if cache_path.exists():
                    cache_path.unlink()
                    self.metadata['total_size'] -= file_size

            # Remove ticker from metadata
            del self.metadata['tickers'][ticker]

            logger.info(f"Evicted cache for {ticker} (LRU cleanup)")

        self._save_metadata()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_size_mb = self.metadata['total_size'] / 1024 / 1024
        max_size_mb = self.max_size_bytes / 1024 / 1024

        total_filings = sum(
            ticker_data.get('total_filings', 0)
            for ticker_data in self.metadata['tickers'].values()
        )

        return {
            'total_tickers': len(self.metadata['tickers']),
            'total_filings': total_filings,
            'total_size_mb': round(total_size_mb, 2),
            'max_size_mb': round(max_size_mb, 2),
            'usage_percent': round((total_size_mb / max_size_mb) * 100, 1) if max_size_mb > 0 else 0,
            'cache_dir': str(self.cache_dir)
        }

    def get_ticker_info(self, ticker: str) -> Optional[Dict]:
        """Get cached info for a specific ticker"""
        return self.metadata['tickers'].get(ticker)

    def list_all_cached_tickers(self) -> List[Dict]:
        """Get list of all cached tickers with their info"""
        result = []
        for ticker, data in self.metadata['tickers'].items():
            total_filings = data.get('total_filings', 0)
            total_size = data.get('file_size', 0)

            # Get date range from cache file
            date_range = {'from': 'N/A', 'to': 'N/A'}
            form_types = {}

            try:
                cache_key = data.get('cache_key')
                if cache_key:
                    cache_path = self._get_cache_path(cache_key)
                    if cache_path.exists():
                        with open(cache_path, 'rb') as f:
                            filings = pickle.load(f)
                            if filings:
                                form_types = self._extract_form_types(filings)
                                date_range = self._extract_date_range(filings)
            except:
                pass

            result.append({
                'ticker': ticker,
                'cik': data['cik'],
                'total_filings': total_filings,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'last_accessed': data['last_accessed'],
                'form_types': form_types,
                'date_range': date_range,
                'last_updated': data.get('last_updated', data.get('first_cached', 'N/A'))
            })

        # Sort by last accessed (most recent first)
        result.sort(key=lambda x: x['last_accessed'], reverse=True)
        return result

    def get_cached_filing_content(self, cik: str, accession_number: str) -> Optional[str]:
        """
        Get cached filing content if available.

        Args:
            cik: Company CIK
            accession_number: Filing accession number

        Returns:
            Filing content string or None if not cached
        """
        try:
            # Create content cache key
            content_key = f"{cik}_{accession_number.replace('-', '')}"
            content_dir = self.cache_dir / 'content'
            content_file = content_dir / f"{content_key}.txt"

            if content_file.exists():
                try:
                    # Try reading with strict UTF-8 first
                    with open(content_file, 'r', encoding='utf-8', errors='strict') as f:
                        content = f.read()
                        logger.debug(f"✓ Content cache HIT for {accession_number} ({len(content)} bytes)")
                        return content
                except UnicodeDecodeError:
                    # Fall back to replacing invalid sequences with replacement character
                    logger.warning(f"Invalid UTF-8 in cached file {content_file}, using replacement strategy")
                    with open(content_file, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        logger.debug(f"✓ Content cache HIT for {accession_number} ({len(content)} bytes)")
                        return content

        except Exception as e:
            logger.debug(f"Error reading content cache: {e}")

        return None

    def cache_filing_content(self, cik: str, accession_number: str, content: str) -> bool:
        """
        Cache filing content to disk.

        Args:
            cik: Company CIK
            accession_number: Filing accession number
            content: Filing text content

        Returns:
            True if cached successfully
        """
        try:
            content_dir = self.cache_dir / 'content'
            content_dir.mkdir(parents=True, exist_ok=True)

            # Create content cache key
            content_key = f"{cik}_{accession_number.replace('-', '')}"
            content_file = content_dir / f"{content_key}.txt"

            # Write content to file
            with open(content_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update total size
            file_size = content_file.stat().st_size
            self.metadata['total_size'] += file_size

            logger.debug(f"✓ Cached filing content for {accession_number} ({file_size} bytes)")

            # Enforce size limit
            self._enforce_size_limit()

            return True

        except Exception as e:
            logger.error(f"Error caching filing content: {e}")
            return False

    def clear_content_cache(self, cik: str = None, ticker: str = None) -> bool:
        """
        Clear cached filing content.

        Args:
            cik: Clear content for specific CIK (optional)
            ticker: Clear content for specific ticker (optional)

        Returns:
            True if cleared successfully
        """
        try:
            content_dir = self.cache_dir / 'content'
            if not content_dir.exists():
                return True

            if cik:
                # Clear content for specific CIK
                import glob as glob_module
                pattern = str(content_dir / f"{cik}_*.txt")
                for file in glob_module.glob(pattern):
                    Path(file).unlink()
                logger.info(f"Cleared content cache for CIK {cik}")

            else:
                # Clear all content
                import shutil
                if content_dir.exists():
                    shutil.rmtree(content_dir)
                logger.info("Cleared all content cache")

            return True

        except Exception as e:
            logger.error(f"Error clearing content cache: {e}")
            return False

    def get_content_cache_stats(self) -> Dict[str, Any]:
        """Get content cache statistics"""
        content_dir = self.cache_dir / 'content'

        if not content_dir.exists():
            return {
                'cached_files': 0,
                'total_size_mb': 0,
                'content_cache_dir': str(content_dir)
            }

        try:
            total_size = 0
            file_count = 0

            for file in content_dir.glob('*.txt'):
                file_count += 1
                total_size += file.stat().st_size

            return {
                'cached_files': file_count,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'content_cache_dir': str(content_dir)
            }
        except Exception as e:
            logger.error(f"Error getting content cache stats: {e}")
            return {
                'cached_files': 0,
                'total_size_mb': 0,
                'error': str(e)
            }


# Global cache instance
_cache_instance = None


def get_filing_cache() -> FilingCache:
    """Get global filing cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = FilingCache()
    return _cache_instance

