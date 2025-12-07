# Filing Content Cache - Verification & Testing Guide

## Quick Verification (2 minutes)

### Step 1: Check Cache Directory Before Running
```bash
cd D:\development project\Fundamental_Data_Pipeline
dir cache\filings\

# You should see:
# - [hash].pkl files (metadata)
# - cache_metadata.json
# - content/ directory (may be empty initially)
```

### Step 2: Run Relationship Extraction Once
```bash
python main.py

# Process a company (e.g., AAPL):
1. Go to Dashboard_Generate tab
2. Search for AAPL
3. Add to queue
4. Enable "Skip Relationship Extraction (Faster)" - UNCHECK THIS FOR TEST
5. Click "Start Processing"
6. Watch the logs for:
   - "Fetching filing content for [ACCESSION]"
   - Processing should take 15-30 seconds
```

### Step 3: Check Cache After First Run
```bash
dir cache\filings\content\

# You should NOW see:
# - 0000320193_*.txt files (AAPL filings)
# - Each file is 50-500 KB
# - Multiple files = multiple cached filings

# Count files:
dir cache\filings\content\ /s
# Should show: 10-15 files (for 1 company)
```

### Step 4: Run Relationship Extraction Again
```bash
# Process same company (AAPL) again:
1. Search for AAPL again
2. Add to queue
3. Click "Start Processing"
4. Watch the logs for:
   - "✓ Content cache HIT for [ACCESSION]"
   - Processing should take 1-2 seconds (NOT 15-30!)

# Compare timing:
First run: 15-30 seconds
Second run: 1-2 seconds
Ratio: 15-30x faster!
```

---

## Detailed Verification

### Verify Content Is Actually Cached

**Check 1: File System**
```bash
# Navigate to cache directory
cd D:\development project\Fundamental_Data_Pipeline\cache\filings\content

# List files
dir

# Each file format: [CIK]_[ACCESSION_WITHOUT_DASHES].txt
# Examples:
# - 0000320193_0001234567250001.txt  (AAPL filing)
# - 0000320193_0001234567250002.txt  (AAPL filing)
# - 0001018724_0001234567250003.txt  (AMZN filing)

# Check file size (should NOT be tiny):
dir /s
# Each file should be 50-500 KB
# If all files are 0 bytes = NOT CACHING PROPERLY
```

**Check 2: Console Logs**
```
FIRST RUN logs should show:
  "Fetching filing content for [ACCESSION]"
  "✓ Cached filing content for [ACCESSION] (250000 bytes)"
  Duration: 10-30 seconds

SECOND RUN logs should show:
  "✓ Content cache HIT for [ACCESSION] (250000 bytes)"
  Duration: 1-2 seconds
```

**Check 3: Cache Stats**
```python
# Run this in Python console:
from src.utils.filing_cache import get_filing_cache

cache = get_filing_cache()

# Get stats
metadata_stats = cache.get_cache_stats()
content_stats = cache.get_content_cache_stats()

print("Metadata cache:", metadata_stats)
print("Content cache:", content_stats)

# Expected output:
# Metadata cache: {
#   'total_tickers': 14,
#   'total_filings': 26320,
#   'total_size_mb': 1.72,
#   'max_size_mb': 2048,
#   'usage_percent': 0.08
# }

# Content cache: {
#   'cached_files': 100,  # Should NOT be 0!
#   'total_size_mb': 45.5,
#   'content_cache_dir': '...'
# }
```

---

## Test Scenarios

### Scenario 1: Single Company (AAPL)

**Expected Results**:
```
Run 1:
- Relationship extraction time: 15-30 seconds
- Cache content files added: 10-15
- Content cache size: 50-200 MB
- Log: "✓ Cached filing content for [ACCESSION]"

Run 2:
- Relationship extraction time: 1-2 seconds  ← 15-30x faster!
- Cache content files: Same (no new added)
- Content cache size: Same
- Log: "✓ Content cache HIT for [ACCESSION]"

Verification:
✓ Second run is much faster
✓ Content files exist in cache/filings/content/
✓ Logs show "cache HIT" on second run
```

### Scenario 2: Multiple Companies (AAPL, MSFT, NVDA)

**Expected Results**:
```
Run 1 (all companies fresh):
- AAPL: 15-30 seconds (fetch & cache)
- MSFT: 15-30 seconds (fetch & cache)
- NVDA: 15-30 seconds (fetch & cache)
- Total: 45-90 seconds
- Content files added: 30-45
- Cache size: 200-500 MB

Run 2 (all companies cached):
- AAPL: 1-2 seconds (from cache)
- MSFT: 1-2 seconds (from cache)
- NVDA: 1-2 seconds (from cache)
- Total: 5-10 seconds
- Speedup: 10x faster!
- Content files: Same
- Cache size: Same

Run 3 (mix of cached + new filings):
- AAPL: 1-2 seconds (cached)
- MSFT: 1-2 seconds (cached)
- NVDA: 1-2 seconds (cached, partially - some new filings added)
- Total: 5-10 seconds
- Content files: Slightly more (new filings)
- Cache size: Slightly more
```

### Scenario 3: Cache Growth Over Multiple Runs

**Expected Pattern**:
```
After Run 1: cache size = X MB (first set of companies)
After Run 2: cache size ≈ X MB (same companies, same content)
After Run 3: cache size ≈ X MB (same, still under limit)
...
After Run 20: cache size → 2000 MB (hits limit)
After Run 21: cache size → ~2000 MB (LRU cleanup keeps it at limit)

Signs of healthy cache:
✓ Cache grows over time
✓ Eventually stabilizes at ~2GB limit
✓ Repeated runs don't add to cache size
✓ Cache hits increase over time
```

---

## Troubleshooting

### Problem: Cache directory is empty or very small

**Diagnosis**:
```bash
# Check if content directory exists:
dir cache\filings\content\

# If directory doesn't exist or is empty:
# Content caching is NOT working
```

**Solutions**:
1. Check logs for errors during first run
2. Verify src/parsers/filing_content_parser.py has cache code
3. Verify src/utils/filing_cache.py has cache_filing_content method
4. Check disk space (2GB available?)
5. Check file permissions (can write to cache/)

### Problem: Second run is still slow

**Diagnosis**:
```python
# Check if files exist:
from pathlib import Path
content_dir = Path('cache/filings/content')
files = list(content_dir.glob('*.txt'))
print(f"Cached content files: {len(files)}")

# If 0 files:
# Files are not being created/saved
```

**Solutions**:
1. Check first run logs for "Cached filing content" messages
2. Verify directory permissions (cache/filings/content/ writable?)
3. Check disk space
4. Manually verify file size (should NOT be 0 bytes)

### Problem: Content files are 0 bytes

**Diagnosis**:
```bash
dir cache\filings\content\ /s

# If all files show 0 bytes:
# Content was started to be cached but empty
```

**Solutions**:
1. Delete 0-byte files: `del cache\filings\content\*.txt`
2. Rerun to generate valid cache
3. Check logs for errors during saving

---

## Performance Benchmarking

### Measure Actual Performance Gain

**Script to Test**:
```python
import time
from src.analysis.parallel_profile_aggregator import ParallelProfileAggregator
from src.clients.mongo_client import MongoWrapper
from src.clients.company_ticker_fetcher import CompanyTickerFetcher

# Setup
mongo = MongoWrapper()
ticker_fetcher = CompanyTickerFetcher()
aggregator = ParallelProfileAggregator(mongo=mongo)

companies = ['AAPL', 'MSFT', 'NVDA']  # Test companies

# First run (populate cache)
print("=== RUN 1: First execution (will populate cache) ===")
start = time.time()
for ticker in companies:
    company = ticker_fetcher.get_by_ticker(ticker)
    if company:
        aggregator.aggregate_profile_parallel(
            cik=company['cik'],
            company_info=company,
            options={'extract_relationships': True, 'skip_relationships_for_speed': False}
        )
run1_time = time.time() - start
print(f"Total time: {run1_time:.1f} seconds")

# Check cache
from src.utils.filing_cache import get_filing_cache
cache = get_filing_cache()
content_stats = cache.get_content_cache_stats()
print(f"Cache after run 1: {content_stats['cached_files']} files, {content_stats['total_size_mb']} MB")

# Second run (use cache)
print("\n=== RUN 2: Second execution (will use cache) ===")
start = time.time()
for ticker in companies:
    company = ticker_fetcher.get_by_ticker(ticker)
    if company:
        aggregator.aggregate_profile_parallel(
            cik=company['cik'],
            company_info=company,
            options={'extract_relationships': True, 'skip_relationships_for_speed': False}
        )
run2_time = time.time() - start
print(f"Total time: {run2_time:.1f} seconds")

# Compare
print(f"\n=== RESULTS ===")
print(f"Run 1 (with SEC fetch): {run1_time:.1f} seconds")
print(f"Run 2 (from cache):     {run2_time:.1f} seconds")
print(f"Speedup:                {run1_time/run2_time:.1f}x faster")
print(f"Time saved:             {run1_time - run2_time:.1f} seconds")
```

**Expected Output**:
```
=== RUN 1 ===
Total time: 45.0 seconds

Cache after run 1: 30 files, 125.5 MB

=== RUN 2 ===
Total time: 3.0 seconds

=== RESULTS ===
Run 1 (with SEC fetch): 45.0 seconds
Run 2 (from cache):     3.0 seconds
Speedup:                15.0x faster
Time saved:             42.0 seconds
```

---

## Monitoring Over Time

### Watch Cache Growth

```python
# Check cache stats periodically:
from src.utils.filing_cache import get_filing_cache

cache = get_filing_cache()

# Before processing
print("Before:", cache.get_content_cache_stats())

# ... process some companies ...

# After processing
print("After:", cache.get_content_cache_stats())

# After 50+ companies processed
# Expected: cache size near 2GB, 5000+ files
```

### Cache Health Check

```python
# Run periodically to verify cache health
def check_cache_health():
    from src.utils.filing_cache import get_filing_cache
    import os
    from pathlib import Path
    
    cache = get_filing_cache()
    
    # Metadata cache
    meta_stats = cache.get_cache_stats()
    print(f"Metadata: {meta_stats['total_filings']} filings, {meta_stats['total_size_mb']} MB")
    
    # Content cache
    content_stats = cache.get_content_cache_stats()
    print(f"Content: {content_stats['cached_files']} files, {content_stats['total_size_mb']} MB")
    
    # Check for 0-byte files (indicates problem)
    content_dir = Path('cache/filings/content')
    zero_byte_files = [f for f in content_dir.glob('*.txt') if f.stat().st_size == 0]
    if zero_byte_files:
        print(f"WARNING: {len(zero_byte_files)} zero-byte files detected!")
        
    # Check cache directory exists and is writable
    if not content_dir.exists():
        print("WARNING: Content cache directory doesn't exist!")
    elif not os.access(content_dir, os.W_OK):
        print("WARNING: Content cache directory not writable!")
    else:
        print("✓ Cache health: OK")

check_cache_health()
```

---

## Summary

### What to Check
1. ✅ Cache directory has content files (not just metadata)
2. ✅ Second run is 15-30x faster than first
3. ✅ Logs show "Content cache HIT" on repeat
4. ✅ Cache size grows over time

### Expected After Fix
- First run: 15-30 seconds (normal, includes SEC fetch)
- Second run: 1-2 seconds (15-30x faster!)
- Cache size: 50 MB → 2 GB (grows over time)
- Network: Reduced SEC API calls

### Success Criteria
- ✓ Content files exist and have data (not 0 bytes)
- ✓ Second run is noticeably faster
- ✓ Logs confirm cache hits
- ✓ Cache grows with more processing

**If all checks pass, content caching is working!** 🎉

