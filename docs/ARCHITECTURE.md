# 🏗️ System Architecture

**Technical architecture and design documentation for the Fundamental Data Pipeline**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [Technology Stack](#technology-stack)
5. [Database Schema](#database-schema)
6. [API Integrations](#api-integrations)
7. [Filing Parsers](#filing-parsers)
8. [AI Integration](#ai-integration)
9. [UI Architecture](#ui-architecture)
10. [Performance Considerations](#performance-considerations)
11. [Security & Compliance](#security--compliance)
12. [Deployment](#deployment)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (PySide6)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────────┐     │
│  │   Dashboard    │  │   Profile    │  │   Visualization     │     │
│  │   Generator    │  │   Manager    │  │   Window            │     │
│  │                │  │              │  │                     │     │
│  │ • Add Tickers  │  │ • View List  │  │ • Charts            │     │
│  │ • Queue Mgmt   │  │ • Edit       │  │ • Interactive       │     │
│  │ • Processing   │  │ • Delete     │  │ • Export            │     │
│  └────────────────┘  └──────────────┘  └─────────────────────┘     │
│           │                   │                     │                │
└───────────┼───────────────────┼─────────────────────┼────────────────┘
            │                   │                     │
            ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CORE SERVICES                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │         Unified Profile Aggregator (Core Engine)          │       │
│  │                                                            │       │
│  │  1. Fetch company metadata (SEC Submissions API)          │       │
│  │  2. Fetch ALL filings with pagination (1000+)             │       │
│  │  3. Extract financial data (XBRL Company Facts API)       │       │
│  │  4. Parse material events (8-K parser)                    │       │
│  │  5. Parse insider trading (Form 4 parser)                 │       │
│  │  6. Parse ownership (SC 13D/G parser)                     │       │
│  │  7. Parse governance (DEF 14A parser)                     │       │
│  │  8. Calculate ratios and metrics                          │       │
│  │  9. Calculate growth rates                                │       │
│  │  10. Generate health scores                               │       │
│  │  11. Run AI analysis (Ollama)                             │       │
│  │  12. Store profile (MongoDB)                              │       │
│  └──────────────────────────────────────────────────────────┘       │
│                              │                                        │
│           ┌──────────────────┼──────────────────┐                   │
│           ▼                  ▼                  ▼                    │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────┐            │
│  │  SEC EDGAR API │ │  Filing Content│ │  AI Analyzer │            │
│  │     Client     │ │    Fetcher     │ │   (Ollama)   │            │
│  │                │ │                │ │              │            │
│  │ • Submissions  │ │ • HTTP Fetcher │ │ • llama3.2   │            │
│  │ • Company Facts│ │ • HTML Parser  │ │ • mistral    │            │
│  │ • Rate Limit   │ │ • XML Parser   │ │ • phi        │            │
│  │ • Pagination   │ │ • Content Parse│ │ • llama2     │            │
│  └────────────────┘ └────────────────┘ └──────────────┘            │
│                                                                       │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │   MongoDB Database     │
                        │                       │
                        │ • unified_profiles    │
                        │ • queue               │
                        │ • settings            │
                        └───────────────────────┘
```

---

## System Components

### 1. **Desktop Application** (`desktop_app_pyside.py`)

**Technology**: PySide6 (Qt for Python)  
**Purpose**: Main user interface

**Features**:
- Multi-tab interface (Dashboard, Queue Monitor, Profile Manager, Settings)
- Queue management for batch processing
- Real-time progress tracking
- Profile visualization
- Ollama model management

**Key Methods**:
- `add_ticker_to_queue()`: Add companies to processing queue
- `start_processing()`: Begin batch profile generation
- `visualize_profile()`: Open visualization window
- `update_ollama_status()`: Check AI model availability

---

### 2. **Unified Profile Aggregator** (`unified_profile_aggregator.py`)

**Purpose**: Core engine - generates complete company profiles

**Process Flow**:

```python
def generate_unified_profile(cik, ticker):
    # 1. Company Metadata
    submissions = sec_client.get_submissions(cik)
    company_info = extract_company_info(submissions)
    
    # 2. Filings (ALL with pagination)
    all_filings = extract_all_filings(submissions)  # 1000+ filings
    
    # 3. Financial Time Series
    company_facts = sec_client.get_company_facts(cik)
    time_series = extract_financial_data(company_facts, all_filings)
    
    # 4. Parse Material Events (8-K)
    material_events = form_8k_parser.parse_8k_filings(all_filings)
    
    # 5. Parse Insider Trading (Form 4)
    insider_trading = form4_parser.parse_form4_filings(all_filings)
    detailed_insider = insider_analyzer.analyze_transactions(all_filings, cik)
    
    # 6. Parse Institutional Ownership (SC 13D/G)
    institutional = sc13_parser.parse_sc13_filings(all_filings)
    detailed_ownership = ownership_analyzer.analyze_ownership_details(all_filings, cik)
    
    # 7. Parse Corporate Governance (DEF 14A)
    governance = def14a_parser.parse_def14a_filings(all_filings)
    detailed_comp = comp_analyzer.analyze_compensation_trends(all_filings, cik)
    detailed_board = board_analyzer.analyze_board_composition(all_filings, cik)
    
    # 8. Calculate Metrics
    latest_financials = get_latest_values(time_series)
    financial_ratios = calculate_ratios(latest_financials)
    growth_rates = calculate_growth_rates(time_series)
    health_indicators = calculate_health_score(ratios, growth_rates)
    
    # 9. AI Analysis
    ai_analysis = ai_analyzer.analyze_profile(profile, all_data)
    
    # 10. Store in MongoDB
    mongo_client.save_profile(profile)
    
    return profile
```

**Key Features**:
- Hybrid data extraction (API + filing parsing)
- Automatic pagination handling
- Error handling and fallbacks
- Progress callbacks for UI updates

---

### 3. **SEC EDGAR API Client** (`sec_edgar_api_client.py`)

**Purpose**: Interface to SEC EDGAR REST API

**APIs Used**:

#### **Submissions API**
```
GET https://data.sec.gov/submissions/CIK{cik}.json
```
**Returns**: Company metadata, all filing references

**Features**:
- Automatic pagination (`handle_pagination=True`)
- Fetches ALL historical filings (1000+)
- Appends paginated results to main response

#### **Company Facts API**
```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
```
**Returns**: XBRL financial data (all periods)

**Extracts**:
- Revenues (10+ tag variations)
- Assets, Liabilities, Equity
- Net Income, Operating Income
- Cash, Current Assets/Liabilities
- Long-term Debt

**Rate Limiting**:
- 10 requests/second (SEC requirement)
- 0.1 second delay between requests
- Automatic throttling

**Error Handling**:
- Retry logic (3 attempts)
- Timeout handling (30 seconds)
- HTTP error codes (404, 429, 500)

---

### 4. **Filing Content Fetcher** (`filing_content_parser.py`)

**Purpose**: Fetch and parse actual filing HTML/XML content

**Components**:

#### **SECFilingContentFetcher**
```python
def fetch_filing_content(cik, accession_number):
    # Constructs URL
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{file}"
    
    # Fetches HTML/XML
    response = requests.get(url, headers={'User-Agent': ...})
    
    return response.text
```

#### **Form4ContentParser**
**Parses**: XML from Form 4 filings  
**Extracts**:
- Insider name and title
- Transaction type (buy/sell/option)
- Shares, price, total value
- Shares owned after transaction

**Output**:
```python
{
    'insider_name': 'Jane Smith',
    'insider_title': 'CFO',
    'transactions': [...],
    'net_transaction': {
        'shares': 5000,
        'value': 730000.0
    },
    'signal': 'Bullish'
}
```

#### **SC13ContentParser**
**Parses**: HTML from SC 13D/G filings  
**Extracts**:
- Investor name
- Ownership percentage
- Number of shares
- Purpose statement (for 13D)
- Activist intent classification

#### **DEF14AContentParser**
**Parses**: HTML tables from proxy statements  
**Extracts**:
- CEO total compensation
- Pay ratio
- Board size and independence
- Director names

---

### 5. **Filing Parsers**

#### **Form 8-K Parser** (`form_8k_parser.py`)

**Purpose**: Parse material events

**Process**:
1. Filter 8-K filings from all filings
2. Analyze frequency patterns
3. Identify risk flags (high frequency, clustering)
4. Identify positive catalysts (consistent disclosure)
5. Calculate average events per quarter

**Output**:
```python
{
    'total_8k_count': 150,
    'recent_count': 4,
    'risk_flags': [...],
    'positive_catalysts': [...],
    'avg_events_per_quarter': 3.2
}
```

---

#### **Form 4 Parser** (`form4_parser.py`)

**Purpose**: Parse insider trading patterns

**Process**:
1. Filter Form 4 filings
2. Pattern analysis (frequency, trends)
3. **NEW**: Fetch actual Form 4 XML content (recent 20)
4. Parse transaction details (buy/sell, amounts, prices)
5. Calculate net buying/selling
6. Identify top buyers and sellers
7. Generate buy/sell signal

**Output**:
```python
{
    'total_form4_count': 245,
    'recent_count_90d': 12,
    'detailed_analysis': {
        'net_value': 3800000.0,
        'overall_signal': 'Strong Bullish',
        'buy_sell_ratio': 4.17,
        'top_buyers': [('CEO', 3), ('CFO', 2)],
        'summary': 'Net buying of $3,800,000'
    }
}
```

---

#### **SC 13D/G Parser** (`sc13_parser.py`)

**Purpose**: Parse institutional ownership

**Process**:
1. Filter SC 13D/G filings
2. Separate activist (13D) from passive (13G)
3. **NEW**: Fetch actual SC 13 HTML content (recent 10)
4. Parse investor names and ownership percentages
5. Extract activist intentions from purpose statements
6. Calculate ownership concentration

**Output**:
```python
{
    'total_sc13_count': 8,
    'activist_count': 2,
    'detailed_analysis': {
        'largest_shareholders': [
            {'investor': 'Vanguard', 'ownership': 8.2},
            {'investor': 'Activist Fund', 'ownership': 5.8, 'intent': 'Board Changes'}
        ],
        'ownership_concentration': {
            'top_3': 18.5,
            'level': 'Moderate'
        }
    }
}
```

---

#### **DEF 14A Parser** (`def14a_parser.py`)

**Purpose**: Parse corporate governance

**Process**:
1. Filter DEF 14A filings
2. Analyze proxy filing patterns
3. Calculate governance score (0-100)
4. **NEW**: Fetch actual DEF 14A HTML (recent 5)
5. Parse compensation tables (CEO pay, ratios)
6. Parse board composition (size, independence)
7. Identify compensation red flags

**Output**:
```python
{
    'total_proxy_count': 10,
    'governance_score': 85.0,
    'detailed_compensation': {
        'ceo_total_comp': 15500000.0,
        'pay_ratio': 206.7,
        'trends': {'ceo_comp_growth': 35.2},
        'red_flags': ['High pay ratio (207:1)']
    },
    'detailed_board': {
        'board_size': 12,
        'independent': 10,
        'independence_ratio': 0.83
    }
}
```

---

#### **10-K/10-Q Parser** (`ten_k_parser.py`) **[NEW]**

**Purpose**: Extract narrative sections from annual/quarterly reports for qualitative analysis

**Process**:
1. Filter 10-K and 10-Q filings
2. Fetch filing content (HTML/XML)
3. Extract key sections using regex patterns:
   - Section 1: Business Overview
   - Section 1A: Risk Factors
   - Section 7: Management's Discussion and Analysis (MD&A)
   - Section 7A: Market Risk Disclosures
   - Section 8: Financial Statements
4. Perform keyword analysis on each section
5. Calculate section-level metrics (word count, keyword density)
6. Aggregate insights across multiple reports

**Keyword Tracking**:
- risk, litigation, cyber, regulatory, liquidity
- macroeconomic, revenue, cash, debt

**Output**:
```python
{
    'total_reports': 4,
    'forms_seen': {'10-K': 2, '10-Q': 2},
    'reports': [
        {
            'form': '10-K',
            'filing_date': '2024-02-15',
            'sections': {
                '1': {
                    'summary': {
                        'word_count': 5432,
                        'keyword_counts': {'revenue': 45, 'cash': 23}
                    },
                    'text': '...'
                },
                '1A': {
                    'summary': {
                        'word_count': 12543,
                        'keyword_counts': {'risk': 312, 'litigation': 45}
                    },
                    'text': '...'
                }
            },
            'insights': {
                'risk_intensity': 'High',
                'business_complexity': 'Moderate'
            }
        }
    ],
    'risk_summary': {
        'average_word_count': 11234,
        'keyword_mentions': 856
    },
    'mdna_summary': {
        'average_word_count': 8765,
        'keyword_mentions': 234
    }
}
```

---

#### **Key Persons Parser** (`key_persons_parser.py`) **[NEW]**

**Purpose**: Comprehensive extraction of key company personnel including executives, board members, insider holdings, and institutional investors

**Process**:
1. Parse Form 4 filings (max 100) for insider names and holdings
2. Parse DEF 14A filings (max 10) for executives and board members
3. Parse SC 13D/G filings (max 50) for institutional investors
4. Validate and deduplicate names
5. Calculate active status (filings within 24 months = active)
6. Extract ownership percentages and share counts
7. Identify holding companies

**Name Validation**:
- Minimum length: 5 characters
- Maximum length: 50 characters
- Rejects form fields (>30% digits)
- Rejects IRS/SSN references
- Rejects boilerplate text patterns
- 20+ invalid pattern filters

**Output**:
```python
{
    'executives': [
        {
            'name': 'John Smith',
            'title': 'Chief Executive Officer',
            'shares_owned': '125000',
            'source': 'Form 4',
            'filing_date': '2024-11-15',
            'active': True
        }
    ],
    'board_members': [
        {
            'name': 'Jane Doe',
            'role': 'Independent Director',
            'independent': True,
            'source': 'DEF 14A',
            'filing_date': '2024-04-20',
            'active': True
        }
    ],
    'insider_holdings': [
        {
            'name': 'John Smith',
            'shares': 125000,
            'percentage': '1.2%',
            'source': 'Form 4'
        }
    ],
    'institutional_investors': [
        {
            'name': 'Vanguard Group Inc',
            'shares': 5432100,
            'percentage': '8.7%',
            'filing_type': 'SC 13G',
            'filing_date': '2024-02-14'
        }
    ],
    'holding_companies': [
        {
            'name': 'BlackRock Inc',
            'ownership_percent': '7.3%',
            'purpose': 'Investment purposes'
        }
    ],
    'total_key_persons': 45,
    'active_executives': 12,
    'active_board_members': 11
}
```

---

### 6. **Quality Control System** **[NEW]**

#### **Profile Validator** (`profile_validator.py`)

**Purpose**: Validate profiles for completeness and consistency

**Validation Checks**:
- Required top-level fields (cik, company_info, filing_metadata, generated_at)
- Company info structure (ticker, name, cik)
- Filing metadata (date ranges, filing counts)
- Financial data consistency (time series order, value ranges)
- Ratio validation (reasonable ranges)
- Date consistency (chronological order, no future dates)

**Issue Categories**:
- **INCOMPLETE**: Missing required fields or empty data
- **INCONSISTENT**: Data type mismatches, invalid values
- **OUT_OF_ORDER**: Dates not in chronological order
- **IMPROPER**: Invalid data ranges, nonsensical values

**Quality Scoring**:
- Data completeness score (0-100)
- Consistency score (0-100)
- Overall quality grade (A+, A, B, C, D, F)

**Output**:
```python
{
    'is_valid': False,
    'status': 'Profile has 5 issues',
    'issues': [
        'INCOMPLETE: Missing required field: financial_ratios',
        'OUT_OF_ORDER: Periods not in chronological order',
        'INCONSISTENT: ROE value out of reasonable range'
    ],
    'categories': {
        'INCOMPLETE': 1,
        'OUT_OF_ORDER': 1,
        'INCONSISTENT': 1
    },
    'quality_score': 65.4,
    'quality_grade': 'C'
}
```

---

#### **Failure Tracker** (`failure_tracker.py`)

**Purpose**: Track and manage failed ticker processing

**Failure Reasons**:
- COMPANY_NOT_FOUND
- CIK_LOOKUP_FAILED
- NO_FILINGS
- FILING_FETCH_ERROR
- DATA_EXTRACTION_ERROR
- INSUFFICIENT_DATA
- AI_ANALYSIS_FAILED
- PROFILE_SAVE_ERROR
- TIMEOUT_ERROR
- UNKNOWN_ERROR
- CANCELLED

**Tracked Information**:
- Ticker symbol
- Failure reason (enum + description)
- Error message
- Timestamp
- Processing context (lookback_years, filing_limit)
- Retry count
- Detailed error stack trace

**Features**:
- Retry tracking (prevents infinite retries)
- Failure categorization
- Bulk operations (retry/delete multiple)
- Export to JSON for analysis
- Statistics (failure rate by reason)

---

### 7. **AI Analyzer** (`ai_analyzer.py`)

**Purpose**: Generate AI-powered investment insights

**Integration**: Ollama (local LLM runtime)

**Supported Models**:
- llama3.2 (fast, accurate - recommended)
- mistral (balanced)
- phi (lightweight)
- llama2 (stable)

**Process**:

```python
def analyze_profile(profile):
    # 1. Extract ALL data
    company_info = profile['company_info']
    financials = profile['latest_financials']
    ratios = profile['financial_ratios']
    growth = profile['growth_rates']
    events = profile['material_events']
    insider = profile['insider_trading']
    institutional = profile['institutional_ownership']
    governance = profile['corporate_governance']
    
    # 2. Create comprehensive prompt
    prompt = f"""
    Company: {ticker} - {name}
    
    === FINANCIAL METRICS ===
    Revenue: ${revenue:,.0f} (Growth: {rev_growth}%)
    Net Income: ${net_income:,.0f}
    ROE: {roe:.2%}, ROA: {roa:.2%}
    Debt/Equity: {de_ratio:.2f}
    
    === MATERIAL EVENTS ===
    Recent 8-Ks: {recent_8k_count}
    Risk Flags: {risk_flags}
    Catalysts: {catalysts}
    
    === INSIDER TRADING ===
    Net Activity: {net_insider_value}
    Signal: {insider_signal}
    Buy/Sell Ratio: {buy_sell_ratio}
    Top Buyers: {top_buyers}
    
    === INSTITUTIONAL OWNERSHIP ===
    Largest Shareholder: {top_shareholder} ({ownership_pct}%)
    Activist Investors: {activist_count}
    Activist Intent: {activist_intent}
    
    === CORPORATE GOVERNANCE ===
    Governance Score: {gov_score}/100
    CEO Compensation: ${ceo_comp:,.0f}
    Pay Ratio: {pay_ratio}:1
    Board Independence: {independence_ratio:.0%}
    
    Provide comprehensive investment analysis...
    """
    
    # 3. Send to Ollama
    response = requests.post('http://localhost:11434/api/generate', json={
        'model': 'llama3.2',
        'prompt': prompt,
        'stream': False
    })
    
    # 4. Parse JSON response
    analysis = json.loads(response.json()['response'])
    
    return analysis
```

**Output Format**:
```python
{
    'investment_thesis': str,
    'recommendation': 'Buy|Hold|Sell',
    'confidence': float,
    'risk_level': 'Low|Medium|High',
    'strengths': List[str],
    'weaknesses': List[str],
    'catalysts': List[str],
    'risks': List[str],
    'insider_signals': str,
    'institutional_signals': str,
    'governance_assessment': str
}
```

**Multi-Model Analysis**:
- Runs same prompt through multiple models
- Compares recommendations
- Calculates consensus
- Shows confidence distribution

---

### 7. **Visualization Window** (`visualization_window.py`)

**Purpose**: Display profile data with interactive charts

**Technology**: PySide6 + Matplotlib

**Tabs**:

1. **Overview**
   - Company information
   - Latest financials
   - Material events
   - Insider trading
   - Institutional ownership
   - Corporate governance
   - Health summary

2. **Decision Summary**
   - Key decision metrics (ROE, ROA, D/E, Growth, Health Score)
   - Investment recommendation
   - Risk level

3. **Financial Trends**
   - Revenue, Assets, Liabilities, Net Income charts
   - Absolute values
   - Hover tooltips
   - Double-click for interactive window

4. **Financial Ratios**
   - ROE, ROA, margins over time
   - Ratio evolution charts

5. **Growth Analysis**
   - Period-over-period growth rates
   - Color-coded bars (green=positive, red=negative)
   - Three-view charts (absolute, %, indexed)
   - Interactive zoom/pan

6. **Health Indicators**
   - Overall health score
   - Component scores (profitability, leverage, growth)
   - Detailed breakdown

7. **AI/ML Analysis**
   - Investment thesis
   - Recommendation
   - Strengths, weaknesses, risks, catalysts
   - Insider/institutional/governance signals
   - Multi-model consensus (expandable)

**Chart Features**:
- Hover tooltips with exact values
- Double-click to open interactive window
- Zoom (mouse wheel) and pan (drag)
- Reset, save, configure buttons
- Responsive layout

---

### 8. **Failed Tickers Dialog** (`failed_tickers_dialog.py`) **[NEW]**

**Purpose**: Manage failed ticker processing attempts

**Features**:
- **View all failures**: Table showing ticker, reason, timestamp, error message
- **Categorization**: Group failures by reason (CIK lookup, no filings, timeout, etc.)
- **Retry functionality**: Select tickers to retry with original or modified settings
- **Delete functionality**: Remove failed tickers from tracking
- **Export**: Save failure data to JSON for analysis
- **Statistics**: View failure rate by category

**UI Components**:
- Tabs: All Failures | By Category | Statistics
- Table columns: Ticker, Reason, Error Message, Timestamp, Retry Count, Context
- Action buttons: Retry Selected, Delete Selected, Retry All, Clear All, Export
- Details pane: Shows full error stack trace and processing context

**Signals**:
- `retry_tickers(list)`: Emitted when retrying selected tickers
- `delete_tickers(list)`: Emitted when deleting selected tickers

---

### 9. **Problematic Profiles Dialog** (`problematic_profiles_dialog.py`) **[NEW]**

**Purpose**: Identify and manage incomplete/inconsistent profiles

**Features**:
- **Automatic scanning**: Scans all profiles in database using ProfileValidator
- **Issue categorization**: Groups issues by type (INCOMPLETE, INCONSISTENT, OUT_OF_ORDER, IMPROPER)
- **Quality scoring**: Shows quality score and grade for each profile
- **Detailed view**: Expandable details showing all issues per profile
- **Bulk retry**: Select multiple profiles to regenerate
- **Filter options**: Show only specific issue types
- **Export**: Save problematic profile list for auditing

**UI Components**:
- Tabs: All Problematic | By Issue Type | Quality Distribution
- Table columns: Ticker, CIK, Company Name, Total Issues, Quality Score, Grade, Last Updated
- Issue breakdown: Shows count by category (INCOMPLETE: 3, INCONSISTENT: 2, etc.)
- Action buttons: Scan Profiles, Retry Selected, Retry All, Export Report
- Progress indicator: Shows scanning progress
- Details pane: Lists all specific issues for selected profile

**Validation Process**:
1. Load all profiles from database
2. For each profile, run ProfileValidator.validate_profile()
3. Categorize issues using ProfileValidator.categorize_issues()
4. Calculate quality score
5. Populate table with results
6. Allow user to select and retry problematic profiles

**Signals**:
- `retry_profiles(list)`: Emitted when retrying selected profiles (by CIK)

---

### 10. **MongoDB Client** (`mongo_client.py`)

**Purpose**: Database operations

**Collections**:

#### **unified_profiles**
```javascript
{
    _id: ObjectId,
    ticker: "AAPL",
    cik: "0000320193",
    company_info: {...},
    financial_time_series: {...},
    latest_financials: {...},
    financial_ratios: {...},
    growth_rates: {...},
    health_indicators: {...},
    material_events: {...},
    insider_trading: {...},
    institutional_ownership: {...},
    corporate_governance: {...},
    ai_analysis: {...},
    generated_at: ISODate,
    last_updated: ISODate
}
```

**Indexes**:
- `ticker` (unique)
- `cik` (unique)
- `generated_at`

**Methods**:
- `save_profile(profile)`: Insert or update
- `find_profile(ticker)`: Retrieve by ticker
- `find_all_profiles()`: Get all profiles
- `delete_profile(ticker)`: Remove profile
- `update_profile(ticker, updates)`: Partial update

---

## Data Flow

### Profile Generation Flow:

```
User Input (Ticker)
       │
       ▼
Add to Queue
       │
       ▼
Start Processing
       │
       ├─► 1. Fetch Company Metadata (SEC Submissions API)
       │        │
       │        ├─► Extract: Ticker, Name, CIK, SIC, Address
       │        └─► Extract: All filing references (paginated)
       │
       ├─► 2. Fetch Financial Data (SEC Company Facts API)
       │        │
       │        └─► Extract: Revenue, Assets, Liabilities, Equity,
       │             Net Income, Cash, etc. (15-20 metrics × 100+ periods)
       │
       ├─► 3. Parse Material Events (8-K)
       │        │
       │        ├─► Filter: 8-K filings from all filings
       │        ├─► Analyze: Frequency, clustering, patterns
       │        └─► Identify: Risk flags, positive catalysts
       │
       ├─► 4. Parse Insider Trading (Form 4)
       │        │
       │        ├─► Filter: Form 4 filings
       │        ├─► Fetch: XML content for recent 20 filings
       │        ├─► Parse: Transaction type, shares, price, value
       │        ├─► Calculate: Net buying/selling, buy/sell ratio
       │        └─► Generate: Signal (Bullish/Bearish)
       │
       ├─► 5. Parse Institutional Ownership (SC 13D/G)
       │        │
       │        ├─► Filter: SC 13D/G filings
       │        ├─► Fetch: HTML content for recent 10 filings
       │        ├─► Parse: Investor names, ownership %, purposes
       │        ├─► Classify: Activist intent
       │        └─► Calculate: Ownership concentration
       │
       ├─► 6. Parse Corporate Governance (DEF 14A)
       │        │
       │        ├─► Filter: DEF 14A filings
       │        ├─► Fetch: HTML content for recent 5 filings
       │        ├─► Parse: CEO compensation, pay ratio, board data
       │        ├─► Calculate: Governance score
       │        └─► Identify: Compensation red flags
       │
       ├─► 7. Parse 10-K/10-Q Narratives **[NEW]**
       │        │
       │        ├─► Filter: 10-K and 10-Q filings
       │        ├─► Fetch: HTML/XML content (2 per form type)
       │        ├─► Extract sections: Business, Risk Factors, MD&A, Market Risk
       │        ├─► Keyword analysis: Track mentions of risk, litigation, etc.
       │        ├─► Calculate: Word counts, keyword density
       │        └─► Aggregate: Risk summary, MD&A summary
       │
       ├─► 8. Parse Key Persons **[NEW]**
       │        │
       │        ├─► From Form 4: Extract insider names, titles, holdings
       │        ├─► From DEF 14A: Extract executives, board members
       │        ├─► From SC 13D/G: Extract institutional investors
       │        ├─► Validate names: Remove form fields and invalid entries
       │        ├─► Calculate active status: Check filing recency (24 months)
       │        └─► Aggregate: Executives, board, holdings, institutions
       │
       ├─► 9. Calculate Metrics
       │        │
       │        ├─► Financial Ratios (ROE, ROA, margins, etc.)
       │        ├─► Growth Rates (avg, median, volatility)
       │        ├─► Health Score (profitability, leverage, growth)
       │        └─► Statistical Summary
       │
       ├─► 10. AI Analysis (Ollama)
       │        │
       │        ├─► Create comprehensive prompt with ALL data
       │        ├─► Send to LLM (llama3.2, mistral, phi, llama2)
       │        ├─► Parse JSON response
       │        └─► Extract: Thesis, recommendation, signals
       │
       ├─► 11. Validate Profile **[NEW]**
       │        │
       │        ├─► Check required fields
       │        ├─► Validate data consistency
       │        ├─► Calculate quality score
       │        └─► Log any issues
       │
       └─► 12. Store Profile (MongoDB)
                │
                ├─► Save to unified_profiles collection
                └─► If errors: Track in failure_tracker
```

---

## Technology Stack

### Languages & Frameworks:
- **Python 3.8+**: Core language
- **PySide6**: Desktop UI framework (Qt)
- **MongoDB**: NoSQL database
- **Ollama**: Local LLM runtime

### Key Libraries:

**Data Processing**:
- `requests`: HTTP requests to SEC API
- `beautifulsoup4`: HTML parsing
- `lxml`: XML parsing
- `pandas`: Data manipulation (optional)
- `numpy`: Numerical operations

**SEC API**:
- `sec-edgar-api`: SEC EDGAR wrapper

**Database**:
- `pymongo`: MongoDB driver

**UI**:
- `PySide6`: Qt framework
- `matplotlib`: Chart plotting

**AI**:
- Ollama API (HTTP requests)
- JSON parsing

### External Services:
- **SEC EDGAR API**: https://data.sec.gov
- **MongoDB**: Local or Atlas cloud
- **Ollama**: Local LLM server (port 11434)

---

## Performance Considerations

### Rate Limiting:
- SEC API: 10 requests/second (enforced)
- Delay: 0.1 seconds between requests
- Automatic throttling

### Pagination:
- SEC API limits to 1000 filings per page
- Automatic pagination handling
- Appends results to main response

### Caching:
- Company tickers cached in JSON file
- Profile data cached in MongoDB
- No re-fetching if profile exists (unless force update)

### Parsing Strategy:
- **All filings**: Pattern analysis (counts, trends, frequency)
- **Recent filings**: Detailed content parsing
  - Form 4: 20 most recent
  - SC 13D/G: 10 most recent
  - DEF 14A: 5 most recent

**Why**: Balance between completeness and performance

### Processing Time:
- Metadata fetch: ~2 seconds
- Financial data fetch: ~3 seconds
- Filing content parsing: ~10-20 seconds
- AI analysis: ~5-30 seconds (depends on model)
- **Total**: ~30-60 seconds per company

---

## Security & Compliance

### SEC Fair Access Policy:
- User-Agent header required (identifies requester)
- Rate limiting: 10 req/sec maximum
- No automated excessive requests
- Compliant implementation ✅

### Data Privacy:
- No personal data stored
- Only public SEC filings processed
- MongoDB local or authenticated cloud

### API Keys:
- SEC API: No key required (public)
- Ollama: Local (no network required)
- MongoDB: Connection string in config (not committed to git)

---

## Deployment

### Local Development:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start MongoDB
mongod

# 3. Start Ollama
ollama serve

# 4. Run application
python desktop_app_pyside.py
```

### Production Deployment:
- Desktop application (no server required)
- MongoDB Atlas for cloud database
- Ollama on local machine (for AI features)
- Portable executable possible (PyInstaller)

---

## Future Enhancements

### Architecture Improvements:
- [ ] Add caching layer (Redis) for SEC API responses
- [ ] Implement background worker for queue processing
- [ ] Add REST API for external access
- [ ] Microservices architecture for scaling

### Data Processing:
- [ ] Real-time price data integration
- [ ] Sentiment analysis from earnings calls
- [ ] News integration (company news, sector trends)
- [ ] Peer comparison framework

### AI/ML:
- [ ] Fine-tuned models for financial analysis
- [ ] Predictive models (price targets, earnings)
- [ ] Anomaly detection in financials
- [ ] Portfolio optimization

---

## Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     Desktop Application                       │
│                    (desktop_app_pyside.py)                    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
    ┌──────────────────┐    ┌──────────────────┐
    │ Queue Management │    │ Profile Manager  │
    └──────────────────┘    └──────────────────┘
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
                ┌──────────────────────────┐
                │  Unified Profile          │
                │  Aggregator               │
                └──────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ SEC EDGAR    │  │ Filing       │  │ AI Analyzer  │
│ API Client   │  │ Content      │  │ (Ollama)     │
│              │  │ Fetcher      │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  MongoDB     │
                    └──────────────┘
```

---

**Last Updated**: December 4, 2025  
**Version**: 1.0.0  
**Status**: Production Ready

---

**See Also**:
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - Complete data reference
- [IMPLEMENTATION_DETAILS.md](IMPLEMENTATION_DETAILS.md) - Implementation guide
- [AI_SETUP_GUIDE.md](AI_SETUP_GUIDE.md) - AI configuration
- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide

