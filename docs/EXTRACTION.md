# 🔗 Data Extraction & Relationship Analysis

**Version**: 2.0.0  
**Last Updated**: December 12, 2025  
**Status**: Production Ready

---

## 📋 Overview

This document covers the data extraction pipeline, focusing on how the application extracts, parses, and correlates information from SEC filings to identify business relationships, company mentions, and key data points.

### Key Components

- **SEC Filing Parsers**: 7 modern parsers + 50+ legacy format parsers
- **Extractors**: 8 specialized extractors for different data types
- **Relationship Integration**: NER-based company mention extraction
- **Quality Assurance**: Validation and error handling throughout

---

## 📊 Data Extraction Pipeline

### Architecture Overview

```
SEC EDGAR API
    ↓
Fetch Filings (Cached)
    ↓
┌─────────────────────────────────────┐
│      Format Detection               │
│  - Identify form type (8-K, etc.)   │
│  - Auto-select parser               │
└──────────┬──────────────────────────┘
           ↓
    ┌──────────────┐
    │   Parsers    │
    ├──────────────┤
    │  8-K Parser  │ → Material Events
    │ Form4 Parser │ → Insider Trading
    │ 13D/G Parser │ → Institutional Ownership
    │ DEF14A Parser│ → Executive Compensation
    │ 10-K Parser  │ → Financial Data
    │ Key Persons  │ → Executives & Board
    └──────────────┘
           ↓
    ┌──────────────┐
    │ Extractors   │ → Process parsed data
    ├──────────────┤
    │  NER Extract │ → Company mentions
    │ Relationship │ → Business relationships
    │  Financial   │ → Time series metrics
    └──────────────┘
           ↓
    ┌──────────────┐
    │  Profile     │ → Aggregate results
    │ Aggregation  │ → Validate data
    └──────────────┘
           ↓
    MongoDB Storage
```

---

## 🔍 Parsers & Extractors

### 1. Material Events Parser (8-K)

**File**: `src/parsers/form_8k_parser.py`  
**Data Extracted**:
- Corporate events and announcements
- Management changes
- Acquisitions and mergers
- Bankruptcy filings
- Changes in company control
- Financial results pre-announcement

**Example Output**:
```python
{
    'material_events': [
        {
            'date': '2025-10-15',
            'event_type': 'Management Change',
            'description': 'CEO resignation',
            'impact': 'negative'
        }
    ],
    'event_count': 42,  # Total events in lookback period
    'most_recent_event': '2025-12-01',
    'most_common_type': 'Financial Results'
}
```

### 2. Insider Trading Parser (Form 4)

**File**: `src/parsers/form4_parser.py`  
**Data Extracted**:
- Insider buy/sell transactions
- Transaction dates and amounts
- Current insider holdings
- Transaction signals (bullish/bearish)
- Key persons involved

**Example Output**:
```python
{
    'insiders': [
        {
            'name': 'Jane Doe',
            'title': 'CEO',
            'transactions': [
                {
                    'date': '2025-11-10',
                    'type': 'purchase',
                    'shares': 50000,
                    'price_per_share': 150.25,
                    'total_value': 7512500.0
                }
            ],
            'net_transaction': {'shares': 50000, 'value': 7512500.0},
            'signal': 'Bullish'
        }
    ],
    'insider_count': 8
}
```

### 3. Institutional Ownership Parser (SC 13D/G)

**File**: `src/parsers/sc13_parser.py`  
**Data Extracted**:
- Institutional investor stakes
- Ownership percentages
- Activist investor intents
- Schedule 13D filing details (activist)
- Schedule 13G filing details (passive)

**Example Output**:
```python
{
    'institutions': [
        {
            'name': 'BlackRock Fund Management',
            'ownership_percent': 8.3,
            'shares_owned': 12500000,
            'is_activist': False,
            'purpose': 'Investment'
        }
    ],
    'activist_count': 2,
    'total_institutional_percent': 45.2
}
```

### 4. Corporate Governance Parser (DEF 14A)

**File**: `src/parsers/def14a_parser.py`  
**Data Extracted**:
- Executive compensation
- CEO to employee pay ratio
- Board composition
- Board independence metrics
- Shareholder proposals

**Example Output**:
```python
{
    'compensation': {
        'ceo_total_comp': 18500000,
        'ceo_salary': 1500000,
        'ceo_bonus': 3000000,
        'ceo_stock_awards': 14000000,
        'median_employee_pay': 85000,
        'pay_ratio': 217.6  # 217x median
    },
    'board': {
        'total_directors': 11,
        'independent_directors': 10,
        'independence_ratio': 0.909
    }
}
```

### 5. Financial Data Parser (10-K/10-Q)

**File**: `src/parsers/ten_k_parser.py`  
**Data Extracted**:
- Revenue, net income, assets, liabilities
- Cash flow information
- Industry/business segment data
- Risk factors and MD&A
- Quarterly/annual financial statements

**Example Output**:
```python
{
    'financials': {
        '2025-12-31': {
            'revenue': 450000000000,
            'net_income': 84000000000,
            'total_assets': 650000000000,
            'total_liabilities': 450000000000,
            'equity': 200000000000,
            'operating_cash_flow': 120000000000
        }
    },
    'time_series': {
        'revenue_growth': 0.084,      # 8.4% growth
        'profit_margin': 0.1867,      # 18.67%
        'roa': 0.1292,                # 12.92%
        'roe': 0.42                   # 42%
    }
}
```

### 6. Key Persons Extractor

**File**: `src/parsers/key_persons_parser.py`  
**Data Extracted** (Parallel extraction from multiple form types):
- Executive officers and titles
- Board of directors
- Insider holdings
- Beneficial ownership details

**Extraction Strategy**:
```python
# Parallel extraction (3 tasks simultaneous):
with ThreadPoolExecutor(max_workers=3) as executor:
    insiders_future = executor.submit(extract_form4_data, filings)
    board_future = executor.submit(extract_def14a_board, filings)
    holdings_future = executor.submit(extract_sc13_holders, filings)
    
    # All complete in ~40s instead of ~60s sequential
```

**Example Output**:
```python
{
    'executives': [
        {
            'name': 'John Smith',
            'title': 'Chief Executive Officer',
            'start_date': '2020-01-15',
            'shares_owned': 5000000,
            'active': True
        }
    ],
    'board_members': [
        {
            'name': 'Jane Doe',
            'title': 'Director',
            'independent': True,
            'committees': ['Audit', 'Compensation']
        }
    ]
}
```

---

## 🔗 Relationship Extraction

### Architecture

The relationship extraction system uses NER (Named Entity Recognition) patterns to identify and classify business relationships.

```
Filing Text
    ↓
┌──────────────────────────┐
│  Fast Company Extractor  │
│  (NER-based patterns)    │
└──────┬───────────────────┘
       ↓
Company Mentions (with context)
       ↓
┌──────────────────────────┐
│  Context Analyzer        │
│  (Identify relationship)  │
└──────┬───────────────────┘
       ↓
Structured Relationships
  - Customer
  - Supplier
  - Partner
  - Competitor
  - Acquisition Target
```

### Fast Company Extraction

**File**: `src/extractors/ner_company_extractor.py`

**Performance**: 30x faster than database-based matching

**Patterns Used**:

1. **Suffix Matching** (Confidence: 0.95)
   ```
   "Apple Inc.", "Microsoft Corporation", "Samsung Electronics Co., Ltd."
   Pattern: [A-Z][A-Za-z\s&]+(Inc|Corp|LLC|Ltd|Limited|Ltd|Co|Co\\.?(?:Ltd)?|Corporation|Company|Group)
   ```

2. **Relationship Patterns** (Confidence: 0.98)
   ```
   "customers include [Company]"
   "partnership with [Company]"
   "acquired [Company]"
   "compete with [Company]"
   ```

3. **Context-Based** (Confidence: 0.75)
   ```
   Capitalized phrases in specific contexts
   ```

### Relationship Classification

**Extracted Relationships**:
- **Customer**: "Our largest customers include Apple Inc."
- **Supplier**: "We purchase materials from [Company]"
- **Partner**: "Strategic partnership with [Company]"
- **Competitor**: "Competing with [Company] in [market]"
- **Acquisition**: "We acquired [Company] for $X"

### Example Output

```python
{
    'relationships': [
        {
            'company_name': 'Apple Inc.',
            'relationship_type': 'Customer',
            'confidence': 0.98,
            'source_filing': '10-K 2025-12-31',
            'context': 'Apple Inc. accounts for 15% of our revenue',
            'filing_date': '2025-12-31'
        },
        {
            'company_name': 'TSMC',
            'relationship_type': 'Supplier',
            'confidence': 0.95,
            'source_filing': '10-Q 2025-09-30',
            'context': 'Primary chip supplier',
            'filing_date': '2025-09-30'
        }
    ],
    'unique_relationships': 47,
    'by_type': {
        'Customer': 15,
        'Supplier': 12,
        'Partner': 10,
        'Competitor': 8,
        'Acquisition': 2
    }
}
```

---

## 🎯 Extraction Quality & Validation

### Quality Metrics

Each extraction is scored on:
- **Completeness**: Did we extract all available data?
- **Accuracy**: Is the extracted data correct?
- **Confidence**: How confident are we in the results?

### Validation Checks

```python
class ExtractionValidator:
    
    def validate_financial_data(self, financials):
        # Check: Revenue >= Net Income
        assert financials['revenue'] >= financials['net_income']
        
        # Check: Assets = Liabilities + Equity
        assert financials['total_assets'] == (
            financials['total_liabilities'] + financials['equity']
        )
        
    def validate_insider_trading(self, transactions):
        # Check: All transaction dates are valid
        for txn in transactions:
            assert parse_date(txn['date']) <= today()
        
        # Check: Share counts are positive
        assert all(t['shares'] > 0 for t in transactions)
```

---

## 🚀 Performance Optimization

### Parallel Extraction

All extractors run simultaneously within the parallel profile aggregator:

```
Filings Fetched
    ↓
┌─────────────────────────────────┐
│ Task 1: Material Events (2s)   │
├─────────────────────────────────┤
│ Task 2: Insider Trading (2s)   │ All running
├─────────────────────────────────┤ simultaneously
│ Task 3: Governance (3s)        │ = ~5s total
├─────────────────────────────────┤
│ Task 4: Key Persons (2s)       │
└─────────────────────────────────┘
```

### Caching Strategy

- **Filing Cache**: Filings cached after first fetch (3-4x faster subsequent runs)
- **Parsed Data Cache**: Intermediate results cached during batch processing
- **Relationship Cache**: Previous relationships cached to avoid re-extraction

---

## 🔧 Configuration & Customization

### Parser Configuration

```python
# src/utils/config.py

PARSER_CONFIG = {
    'max_filings_per_type': 100,      # Process 100 most recent
    'form_4_lookback': 5,              # Years of insider trading
    'def14a_lookback': 3,              # Years of governance
    'relationship_filings': 3,         # Recent filings for relationships
    'timeout_per_task': 60,            # Seconds per extraction task
}
```

### Custom Configuration

```python
from src.utils.config import PARSER_CONFIG

# Increase insider trading lookback
PARSER_CONFIG['form_4_lookback'] = 10

# Limit filings to speed up processing
PARSER_CONFIG['max_filings_per_type'] = 20
```

---

## ⚠️ Known Limitations

### 1. Relationship Graph Limitations

- Processes 3 most recent filings (for performance)
- Some generic company mentions may appear in every graph
- Graph visualization not fully interactive

**Workaround**: Use filing viewer to inspect individual relationships in detail

### 2. NER Limitations

- May miss companies without formal suffixes
- Foreign company names sometimes misidentified
- Subsidiary names sometimes confused with parent companies

**Workaround**: Verify important relationships in original filings

### 3. Form Parsing Challenges

- Legacy format differences between companies
- Missing XML tags in some filings
- Inconsistent data formatting

**Workaround**: Multiple parsers with automatic fallback strategy

---

## 📚 Related Documentation

- [PARALLELIZATION.md](PARALLELIZATION.md) - Parallel extraction architecture
- [PERFORMANCE.md](PERFORMANCE.md) - Performance metrics
- [CACHE_SYSTEM.md](CACHE_SYSTEM.md) - Filing cache system
- [README.md](../README.md) - Project overview

---

## 🤝 Contributing

For extraction improvements:

1. **Add new parser**: Create in `src/parsers/`
2. **Test thoroughly**: Process 10+ different companies
3. **Document output schema**: What data does it extract?
4. **Validate results**: Check accuracy against original filings
5. **Update this guide**: Document new capabilities

---

## 📊 Version History

- **v2.0.0 (Dec 12, 2025)**: NER-based extraction, 30x faster relationships
- **v1.5.0**: Parallel extraction optimization
- **v1.0.0**: Initial extraction pipeline

