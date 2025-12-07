# 🛡️ Quality Control & Error Management

**Comprehensive guide to profile validation, failure tracking, and error recovery in the Fundamental Data Pipeline**

---

## Table of Contents

1. [Overview](#overview)
2. [Profile Validation System](#profile-validation-system)
3. [Failure Tracking System](#failure-tracking-system)
4. [UI Components](#ui-components)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Overview

The quality control system ensures data integrity and provides robust error management through two main components:

1. **Profile Validator** - Validates profiles for completeness and consistency
2. **Failure Tracker** - Tracks and manages processing failures with detailed diagnostics

These systems work together to:
- Identify incomplete or inconsistent data
- Track why tickers fail to process
- Enable easy retry/recovery workflows
- Maintain data quality standards
- Provide detailed diagnostics for debugging

---

## Profile Validation System

### Purpose

The Profile Validator (`src/utils/profile_validator.py`) automatically checks profiles for:
- Missing required fields
- Data type inconsistencies
- Chronological order issues
- Invalid value ranges
- Overall data quality

### Validation Checks

#### 1. **Required Fields Check**

Validates presence of critical top-level fields:
```python
required_fields = [
    'cik',
    'company_info',
    'filing_metadata',
    'generated_at'
]
```

#### 2. **Company Info Validation**

Checks structure and content:
```python
company_info = {
    'ticker': 'AAPL',        # Must be present
    'name': 'Apple Inc.',    # Must be present
    'cik': '0000320193'      # Must be present
}
```

#### 3. **Filing Metadata Validation**

Validates date ranges and filing counts:
```python
filing_metadata = {
    'total_filings': 1234,              # Should be > 0
    'earliest_filing': '2010-01-15',    # Must be valid date
    'most_recent_filing': '2024-11-30', # Must be valid date
    'filing_date_range_years': 14.5     # Should be reasonable
}
```

#### 4. **Financial Data Validation**

Checks time series consistency:
```python
# Validates:
# - Periods are in chronological order
# - Values are in reasonable ranges
# - No extreme outliers (unless justified)
# - Data types are consistent
```

#### 5. **Ratio Validation**

Ensures ratios are in reasonable ranges:
```python
reasonable_ranges = {
    'roe': (-100, 500),        # ROE between -100% and 500%
    'roa': (-50, 100),         # ROA between -50% and 100%
    'debt_to_equity': (0, 50), # D/E ratio between 0 and 50
    'current_ratio': (0, 20)   # Current ratio between 0 and 20
}
```

### Issue Categories

#### **INCOMPLETE**
Missing required fields or empty data structures.

Examples:
- `INCOMPLETE: Missing required field: financial_ratios`
- `INCOMPLETE: Missing company_info.ticker`
- `INCOMPLETE: Empty financial_time_series`

#### **INCONSISTENT**
Data type mismatches or invalid values.

Examples:
- `INCONSISTENT: company_info is not a dictionary`
- `INCONSISTENT: ROE value out of reasonable range: 1234.5`
- `INCONSISTENT: Invalid date format in filing_metadata`

#### **OUT_OF_ORDER**
Dates or periods not in proper chronological order.

Examples:
- `OUT_OF_ORDER: Periods not in chronological order`
- `OUT_OF_ORDER: most_recent_filing is before earliest_filing`

#### **IMPROPER**
Invalid data ranges or nonsensical values.

Examples:
- `IMPROPER: Negative revenue: -1000000`
- `IMPROPER: Future filing date: 2026-01-01`
- `IMPROPER: Debt-to-equity ratio extremely high: 87.5`

### Quality Scoring

The validator assigns quality scores based on:

```python
# Scoring algorithm
completeness_score = (fields_present / total_required_fields) * 100
consistency_score = 100 - (inconsistencies * 10)  # -10 per issue
overall_score = (completeness_score + consistency_score) / 2

# Quality grades
grades = {
    95-100: 'A+',
    90-94:  'A',
    80-89:  'B',
    70-79:  'C',
    60-69:  'D',
    0-59:   'F'
}
```

### Usage Example

```python
from src.utils.profile_validator import ProfileValidator

# Validate a profile
is_valid, status, issues = ProfileValidator.validate_profile(profile)

if not is_valid:
    print(f"Profile has issues: {status}")
    for issue in issues:
        print(f"  - {issue}")
    
    # Categorize issues
    categories = ProfileValidator.categorize_issues(issues)
    print(f"Issue breakdown: {categories}")
    # Output: {'INCOMPLETE': 2, 'INCONSISTENT': 1, 'OUT_OF_ORDER': 1}
```

---

## Failure Tracking System

### Purpose

The Failure Tracker (`src/utils/failure_tracker.py`) captures detailed information about processing failures, enabling:
- Root cause analysis
- Systematic retry workflows
- Failure pattern identification
- Quality improvement

### Failure Reasons

Enumerated failure types:

| Reason | Description |
|--------|-------------|
| `COMPANY_NOT_FOUND` | Ticker not found in SEC database |
| `CIK_LOOKUP_FAILED` | Failed to resolve ticker to CIK |
| `NO_FILINGS` | Company has no available filings |
| `FILING_FETCH_ERROR` | Failed to fetch filings from SEC API |
| `DATA_EXTRACTION_ERROR` | Failed to extract data from filings |
| `INSUFFICIENT_DATA` | Too little data for meaningful analysis |
| `AI_ANALYSIS_FAILED` | AI/LLM analysis generation failed |
| `PROFILE_SAVE_ERROR` | Failed to save profile to database |
| `TIMEOUT_ERROR` | Processing exceeded time limit |
| `UNKNOWN_ERROR` | Unclassified error |
| `CANCELLED` | User cancelled processing |

### Tracked Information

For each failure:

```python
{
    'ticker': 'TSLA',
    'reason': 'DATA_EXTRACTION_ERROR',
    'reason_code': 'DATA_EXTRACTION_ERROR',
    'error_msg': 'Failed to parse Form 4 XML: malformed XML',
    'timestamp': '2024-12-07T10:30:45.123Z',
    'details': {
        'form_type': 'Form 4',
        'accession_number': '0001234567-24-000123',
        'parser': 'Form4ContentParser',
        'stack_trace': '...'
    },
    'context': {
        'lookback_years': 30,
        'filing_limit': 1000,
        'ai_enabled': True
    },
    'retry_count': 2
}
```

### Usage Example

```python
from src.utils.failure_tracker import FailureTracker, FailureReason

# Initialize tracker
tracker = FailureTracker()

# Track a failure
try:
    process_ticker('AAPL')
except Exception as e:
    tracker.track_failure(
        ticker='AAPL',
        reason=FailureReason.DATA_EXTRACTION_ERROR,
        error_msg=str(e),
        details={'parser': 'Form4ContentParser'},
        context={'lookback_years': 30}
    )

# Get statistics
stats = tracker.get_statistics()
print(f"Total failures: {stats['total_failures']}")
print(f"By reason: {stats['by_reason']}")
# Output: {'DATA_EXTRACTION_ERROR': 5, 'TIMEOUT_ERROR': 2, ...}

# Export for analysis
tracker.export_to_json('failures_2024-12-07.json')
```

---

## UI Components

### 1. Problematic Profiles Dialog

**Access**: Profile Manager → "Find Problematic Profiles" button

**Features**:
- Scans all profiles in database
- Shows quality score and grade
- Lists specific issues per profile
- Allows bulk retry of problematic profiles
- Exports report for auditing

**Workflow**:
1. Click "Scan Profiles" button
2. Wait for validation to complete
3. Review list of problematic profiles
4. Select profiles to retry (Ctrl+Click for multiple)
5. Click "Retry Selected" to regenerate profiles

**Table Columns**:
- Ticker
- CIK
- Company Name
- Total Issues
- Quality Score
- Quality Grade (A+, A, B, C, D, F)
- Last Updated

**Issue Breakdown**:
Shows count by category:
```
INCOMPLETE: 3 issues
INCONSISTENT: 2 issues
OUT_OF_ORDER: 1 issue
IMPROPER: 0 issues
```

### 2. Failed Tickers Dialog

**Access**: Dashboard → "View Failed Tickers" button

**Features**:
- Shows all failed processing attempts
- Categorizes by failure reason
- Displays error messages and stack traces
- Allows retry with same or modified settings
- Delete failed entries to clean up

**Workflow**:
1. Click "View Failed Tickers"
2. Review failure reasons
3. Select tickers to retry
4. Optionally modify settings (lookback_years, etc.)
5. Click "Retry Selected"

**Table Columns**:
- Ticker
- Failure Reason
- Error Message (truncated)
- Timestamp
- Retry Count
- Context (lookback_years, etc.)

**Actions**:
- **Retry Selected**: Retry with original settings
- **Retry All**: Retry all failed tickers
- **Delete Selected**: Remove from failure tracking
- **Clear All**: Remove all failed tickers
- **Export**: Save to JSON file

---

## Best Practices

### Profile Validation

1. **Run validation after batch processing**
   ```python
   # After processing multiple tickers
   problematic = []
   for profile in all_profiles:
       is_valid, _, _ = ProfileValidator.validate_profile(profile)
       if not is_valid:
           problematic.append(profile['ticker'])
   
   # Retry problematic profiles
   retry_queue.extend(problematic)
   ```

2. **Set quality thresholds**
   ```python
   # Only accept profiles with quality score > 70
   quality_score = ProfileValidator.calculate_quality_score(profile)
   if quality_score < 70:
       log.warning(f"Low quality profile: {ticker} (score: {quality_score})")
       # Consider retrying or flagging for manual review
   ```

3. **Monitor issue trends**
   - Track which issue categories are most common
   - Identify systematic problems (e.g., always missing certain fields)
   - Fix root causes in parsers/aggregators

### Failure Tracking

1. **Review failures regularly**
   - Check failed tickers dialog after each batch
   - Look for patterns in failure reasons
   - Address systematic issues

2. **Retry strategically**
   ```python
   # Don't retry tickers with permanent failures
   permanent_failures = [
       FailureReason.COMPANY_NOT_FOUND,
       FailureReason.NO_FILINGS
   ]
   
   # Only retry temporary failures
   retryable = [f for f in failures 
                if f['reason_code'] not in permanent_failures]
   ```

3. **Set retry limits**
   ```python
   # Avoid infinite retry loops
   MAX_RETRIES = 3
   
   if ticker_retry_count >= MAX_RETRIES:
       log.error(f"Max retries exceeded for {ticker}")
       # Move to permanent failure list
   ```

4. **Analyze failure context**
   - Check if failures occur with specific settings
   - Example: High `lookback_years` might cause timeouts
   - Adjust settings for problematic tickers

### Data Quality Maintenance

1. **Periodic quality audits**
   - Weekly: Scan all profiles for issues
   - Monthly: Review failure statistics
   - Quarterly: Validate data consistency

2. **Automated quality reports**
   ```python
   # Generate weekly quality report
   total_profiles = len(all_profiles)
   problematic = len([p for p in all_profiles 
                      if not ProfileValidator.is_valid(p)])
   
   quality_rate = (total_profiles - problematic) / total_profiles * 100
   print(f"Data Quality Rate: {quality_rate:.1f}%")
   ```

3. **Incremental improvements**
   - Track quality metrics over time
   - Set improvement goals (e.g., 95% quality rate)
   - Continuously refine parsers and validators

---

## Troubleshooting

### Common Issues

#### Issue: Many profiles marked as INCOMPLETE

**Cause**: Missing optional fields being treated as required

**Solution**: 
1. Review ProfileValidator code
2. Ensure only truly required fields are checked
3. Update validator to handle optional fields gracefully

#### Issue: High DATA_EXTRACTION_ERROR rate

**Cause**: Filing formats changed or parser bugs

**Solution**:
1. Check error details for specific parsers
2. Review recent SEC filing format changes
3. Update parsers with better error handling
4. Add fallback parsing strategies

#### Issue: Frequent TIMEOUT_ERROR failures

**Cause**: Processing taking too long (large companies, high lookback_years)

**Solution**:
1. Reduce `lookback_years` for problematic tickers
2. Implement incremental processing
3. Optimize parser performance
4. Increase timeout limits in config

#### Issue: AI_ANALYSIS_FAILED errors

**Cause**: Ollama not running or model unavailable

**Solution**:
1. Check Ollama status: `ollama list`
2. Start Ollama: `ollama serve`
3. Pull required models: `ollama pull llama3.2`
4. Verify model names in config.yaml

### Debug Workflow

1. **Check failure details**
   ```python
   # In Failed Tickers Dialog
   # Click on failed ticker
   # Review "Error Message" and "Details" columns
   ```

2. **Enable debug logging**
   ```python
   # In config.yaml
   logging:
     level: DEBUG
     
   # Or in code
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Test individual components**
   ```python
   # Test specific parser
   from src.parsers.form4_parser import Form4Parser
   
   parser = Form4Parser()
   result = parser.parse_form4_filings(filings, cik)
   print(result)
   ```

4. **Validate input data**
   ```python
   # Check SEC API response
   from src.clients.sec_edgar_api_client import SECEdgarClient
   
   client = SECEdgarClient()
   filings = client.get_company_filings('0000320193')
   print(f"Total filings: {len(filings)}")
   ```

### Recovery Strategies

#### Strategy 1: Selective Retry
Retry only specific failure types:
```python
# Retry only transient errors
retryable_reasons = [
    FailureReason.TIMEOUT_ERROR,
    FailureReason.FILING_FETCH_ERROR,
    FailureReason.AI_ANALYSIS_FAILED
]

tickers_to_retry = [
    f['ticker'] for f in failures 
    if f['reason_code'] in retryable_reasons
]
```

#### Strategy 2: Reduced Settings Retry
Retry with reduced settings to avoid timeouts:
```python
# Retry with reduced lookback
retry_options = {
    'lookback_years': 10,  # Instead of 30
    'filing_limit': 500,   # Instead of 1000
    'ai_enabled': False    # Skip AI if it's failing
}
```

#### Strategy 3: Manual Intervention
For persistent failures:
1. Export failure details to JSON
2. Analyze offline
3. Fix root cause (parser bug, data issue, etc.)
4. Clear failed entries
5. Reprocess with fix in place

---

## Summary

The quality control system provides:

✅ **Automatic validation** of all generated profiles  
✅ **Detailed failure tracking** with root cause analysis  
✅ **Easy retry workflows** through UI dialogs  
✅ **Quality scoring** to measure data completeness  
✅ **Issue categorization** for systematic improvements  
✅ **Export capabilities** for offline analysis  

**Best Practice**: Run "Find Problematic Profiles" after each batch processing session to maintain data quality!

