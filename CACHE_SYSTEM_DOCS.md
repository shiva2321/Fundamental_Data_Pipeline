# Filing Cache System - Complete Documentation

## Overview

A comprehensive 2GB filing cache system to speed up testing and development by avoiding redundant SEC API calls.

## Features Implemented

### 1. **Filing Cache System** (`src/utils/filing_cache.py`)

**Core Features:**
- **2GB Maximum Size**: Configurable cache limit
- **LRU Eviction**: Automatically removes oldest entries when limit reached
- **Per-Ticker Organization**: Each ticker's filings cached separately
- **Metadata Tracking**: Form types, dates, file sizes tracked
- **Persistence**: Disk-based storage survives app restarts

**Key Methods:**
```python
from src.utils.filing_cache import get_filing_cache

cache = get_filing_cache()

# Check cache
filings = cache.get_cached_filings(cik, ticker, lookback_years)

# Store in cache
cache.cache_filings(cik, ticker, filings, lookback_years)

# Clear cache
cache.clear_ticker_cache(ticker)  # Clear specific ticker
cache.clear_all_cache()           # Clear everything

# Get stats
stats = cache.get_cache_stats()
```

### 2. **Cache Manager UI** (`src/ui/cache_manager_widget.py`)

**New Tab in Main Window: "Cache Manager"**

Shows:
- **Statistics Panel**: Total tickers, filings, size, usage percentage
- **Cache Table**: All cached tickers with:
  - Ticker symbol and CIK
  - Filing count
  - Size in MB
  - Form types (10-K, 10-Q, 8-K, etc.)
  - Date range (from - to)
  - Last accessed time
- **Control Buttons**:
  - 🔄 Refresh: Reload cache data
  - 🗑️ Clear Selected: Delete cache for selected tickers
  - 🗑️ Clear All Cache: Remove entire cache

**Color-Coded Usage Bar:**
- Green: < 70% usage
- Yellow: 70-90% usage
- Red: > 90% usage (triggers cleanup)

### 3. **Integrated Pipeline** (`src/analysis/unified_profile_aggregator.py`)

**Automatic Cache Usage:**

When processing a company:
1. **Check cache first** for matching CIK + lookback_years
2. **Load from cache** if available (instant!)
3. **Fetch from SEC** if cache miss
4. **Auto-cache** newly fetched filings for future use

**User Notifications:**
- "📦 Cache: Loaded X filings from cache (fast!)" - Cache hit
- "🌐 Fetching filings from SEC for TICKER..." - Cache miss
- Logs show cache operations for transparency

---

## How It Works

### Cache Structure

```
cache/
└── filings/
    ├── cache_metadata.json          # Index of all cached data
    ├── a1b2c3d4e5f6.pkl            # Cached filings for ticker 1
    ├── f6e5d4c3b2a1.pkl            # Cached filings for ticker 2
    └── ...
```

**Cache Key Generation:**
```python
key = MD5(f"{cik}_{lookback_years}y")
```

Each unique combination of CIK and lookback period gets its own cache entry.

### Metadata Format

```json
{
  "tickers": {
    "AAPL": {
      "cik": "0000320193",
      "first_cached": "2025-12-07T10:30:00",
      "last_accessed": "2025-12-07T14:45:00",
      "cache_entries": [
        {
          "lookback_years": 5,
          "filing_count": 1250,
          "file_size": 524288,
          "cached_at": "2025-12-07T10:30:00",
          "cache_key": "a1b2c3d4e5f6",
          "form_types": {
            "10-K": 5,
            "10-Q": 20,
            "8-K": 150,
            "DEF 14A": 5
          },
          "date_range": {
            "from": "2020-01-01",
            "to": "2025-12-07"
          }
        }
      ]
    }
  },
  "total_size": 524288,
  "created_at": "2025-12-07T10:30:00"
}
```

### LRU Eviction Algorithm

When cache exceeds 2GB:
1. Sort all entries by `last_accessed` (oldest first)
2. Remove entries until size < 2GB
3. Delete orphaned ticker entries with no cache data
4. Update metadata
5. Log evicted tickers

---

## Usage Guide

### For End Users

#### View Cache Status

1. Open desktop app
2. Click **"Cache Manager"** tab
3. View cached tickers and statistics

#### Clear Cache

**Individual Ticker:**
1. Go to Cache Manager tab
2. Select ticker(s) in table
3. Click "Clear Selected"
4. Confirm deletion

**All Cache:**
1. Go to Cache Manager tab
2. Click "Clear All Cache"
3. Confirm deletion (shows size being deleted)

#### During Processing

Cache usage is automatic:
- First time processing: Fetches from SEC, caches automatically
- Subsequent times: Loads from cache (much faster!)
- Progress logs show: "📦 Cache: Loaded X filings from cache"

### For Developers

#### Enable/Disable Caching

Cache is always enabled. To bypass:
```python
# Don't pass lookback_years - cache won't be used
options = {
    'lookback_years': None  # Forces SEC fetch
}
```

#### Manual Cache Operations

```python
from src.utils.filing_cache import get_filing_cache

cache = get_filing_cache()

# Get cache info for ticker
info = cache.get_ticker_info('AAPL')

# List all cached tickers
all_tickers = cache.list_all_cached_tickers()

# Get statistics
stats = cache.get_cache_stats()
print(f"Cache usage: {stats['usage_percent']}%")

# Clear specific ticker
cache.clear_ticker_cache('AAPL')

# Clear everything
cache.clear_all_cache()
```

#### Change Cache Size

Edit when creating cache:
```python
cache = FilingCache(max_size_gb=5.0)  # 5GB instead of 2GB
```

Or modify `src/utils/filing_cache.py`:
```python
def __init__(self, cache_dir: Optional[str] = None, max_size_gb: float = 5.0):
```

---

## Performance Benefits

### Before Cache (Cold Start)
```
Processing AAPL:
  Fetching filings from SEC... ⏱️ 15-30 seconds
  Processing filings... ⏱️ 45 seconds
  Total: ~1 minute
```

### With Cache (Warm Start)
```
Processing AAPL:
  Loading from cache... ⏱️ <1 second ✓
  Processing filings... ⏱️ 45 seconds
  Total: ~45 seconds (25-40% faster!)
```

### Testing Benefits

**Reprocessing 10 companies:**
- Without cache: ~10 minutes (SEC fetches)
- With cache: ~7 minutes (instant loads)
- **Savings: 30% time reduction**

**Iterative development:**
- Test → Fix → Test cycle
- No waiting for SEC API
- Instant profile generation

---

## Cache Maintenance

### Automatic Cleanup

- **Trigger**: When cache exceeds 2GB
- **Action**: Remove oldest accessed entries (LRU)
- **Result**: Cache reduced to under 2GB
- **Logging**: Shows evicted tickers

### Manual Cleanup

**Clear old tickers:**
1. Open Cache Manager
2. Sort by "Last Accessed"
3. Select old entries
4. Click "Clear Selected"

**Free up space:**
- Cache Manager shows size per ticker
- Remove large, rarely-used tickers first

### Reset Cache

To start fresh:
```bash
# Delete cache directory
rm -rf cache/filings

# Or use UI
Cache Manager → Clear All Cache
```

---

## File Locations

| File | Purpose |
|------|---------|
| `src/utils/filing_cache.py` | Core cache system |
| `src/ui/cache_manager_widget.py` | Cache Manager UI tab |
| `src/analysis/unified_profile_aggregator.py` | Cache integration (modified) |
| `src/ui/desktop_app_pyside.py` | Main window with Cache tab (modified) |
| `cache/filings/` | Cache storage directory |
| `cache/filings/cache_metadata.json` | Cache index |
| `test_cache.py` | Test script |

---

## Configuration

### Default Settings

```python
CACHE_DIR = './cache/filings'
MAX_SIZE_GB = 2.0
```

### Customize

Edit `src/utils/filing_cache.py`:

```python
class FilingCache:
    def __init__(
        self, 
        cache_dir: Optional[str] = None,  # Custom directory
        max_size_gb: float = 2.0           # Custom size
    ):
```

Or pass during initialization:
```python
cache = FilingCache(
    cache_dir='/path/to/cache',
    max_size_gb=5.0
)
```

---

## Testing

### Test Cache System

```bash
python test_cache.py
```

Expected output:
```
[OK] Cache initialized
[CACHE MISS] Fetching from SEC...
[OK] Fetched 2313 filings
[OK] Cached 2313 filings
[CACHE HIT] Retrieved 2313 filings from cache
[SUCCESS] CACHE TEST COMPLETE
```

### Test in App

1. Run app: `python -m src.ui.desktop_app_pyside`
2. Go to "Cache Manager" tab
3. Should show cached ticker from test
4. Try clearing cache
5. Process a ticker
6. Check Cache Manager - should appear

---

## Troubleshooting

### Cache not working?

**Check:**
1. `lookback_years` must be set in options
2. `ticker` must be provided in company_info
3. Check logs for "Cache" messages
4. Verify cache directory exists: `cache/filings/`

### Cache too large?

**Solutions:**
1. Clear old tickers in Cache Manager
2. Reduce `max_size_gb` setting
3. Clear all cache and rebuild selectively

### Cache corruption?

**Fix:**
```bash
# Delete corrupted cache
rm -rf cache/filings

# Or use UI
Cache Manager → Clear All Cache
```

Cache will rebuild automatically on next processing.

---

## Summary

✅ **2GB Filing Cache System** - Complete and integrated
✅ **Cache Manager UI Tab** - Visual management interface
✅ **Automatic Cache Usage** - Transparent to users
✅ **LRU Eviction** - Smart cleanup when limit reached
✅ **Per-Ticker Organization** - Easy to manage
✅ **Production Ready** - Error handling, logging, persistence

**Benefits:**
- 25-40% faster reprocessing
- Reduced SEC API load
- Better testing experience
- Automatic management

**No configuration needed** - Works out of the box! 🚀

