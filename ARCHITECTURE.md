# System Architecture - Fundamental Data Pipeline

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACES                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────┐              ┌────────────────────┐         │
│  │   Web Dashboard    │              │    CLI Interface   │         │
│  │   (dashboard.py)   │              │ (main_unified.py)  │         │
│  │                    │              │                    │         │
│  │ • Home             │              │ • Search           │         │
│  │ • Search           │              │ • Generate         │         │
│  │ • Generate         │              │ • View             │         │
│  │ • View             │              │ • Batch            │         │
│  │ • Analytics        │              │ • Statistics       │         │
│  │ • Settings         │              │ • Launch Dashboard │         │
│  └────────────────────┘              └────────────────────┘         │
│           │                                    │                     │
└───────────┼────────────────────────────────────┼─────────────────────┘
            │                                    │
            └────────────────┬───────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CORE SERVICES                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │         Unified Profile Aggregator                        │       │
│  │      (unified_profile_aggregator.py)                      │       │
│  │                                                            │       │
│  │  • Fetch filings from SEC                                 │       │
│  │  • Aggregate financial data                               │       │
│  │  • Calculate ratios & metrics                             │       │
│  │  • Generate ML features                                   │       │
│  │  • Create unified profile                                 │       │
│  │  • Store in MongoDB                                       │       │
│  └──────────────────────────────────────────────────────────┘       │
│            │                             │                           │
│            ▼                             ▼                           │
│  ┌─────────────────┐          ┌──────────────────┐                  │
│  │  Company Ticker │          │  SEC EDGAR API   │                  │
│  │     Fetcher     │          │     Client       │                  │
│  │                 │          │                  │                  │
│  │ • Load tickers  │          │ • Fetch filings  │                  │
│  │ • Cache data    │          │ • Rate limiting  │                  │
│  │ • Search by:    │          │ • Error handling │                  │
│  │   - Ticker      │          │ • Company facts  │                  │
│  │   - Name        │          │                  │                  │
│  │   - CIK         │          │                  │                  │
│  └─────────────────┘          └──────────────────┘                  │
│            │                             │                           │
└────────────┼─────────────────────────────┼───────────────────────────┘
             │                             │
             ▼                             ▼
┌─────────────────────────┐   ┌──────────────────────────────┐
│   SEC Website           │   │      MongoDB Database        │
│                         │   │                              │
│ company_tickers.json    │   │  Database: Entities          │
│ (10,196+ companies)     │   │  Collection:                 │
│                         │   │   Fundamental_Data_Pipeline  │
│ • Ticker symbols        │   │                              │
│ • Company names         │   │  Documents:                  │
│ • CIK numbers           │   │  • Unified profiles          │
│                         │   │  • One per company           │
│ Cached locally for      │   │  • All data combined         │
│ 7 days                  │   │                              │
└─────────────────────────┘   └──────────────────────────────┘
```

## Data Flow

### Profile Generation Flow

```
User Input (Ticker/CIK/Name)
          │
          ▼
    ┌─────────────┐
    │   Search    │ ─── Company Ticker Fetcher ─── SEC Tickers JSON
    │  Company    │                                  (cached)
    └─────────────┘
          │
          ▼
    Get CIK Number
          │
          ▼
    ┌─────────────────┐
    │  Fetch Filings  │ ─── SEC EDGAR API Client ─── SEC EDGAR API
    │   from SEC      │                                (rate limited)
    └─────────────────┘
          │
          ▼
    ┌────────────────────────────────────┐
    │   Unified Profile Aggregator       │
    │                                    │
    │  1. Extract financial time series  │
    │  2. Calculate latest values        │
    │  3. Compute financial ratios       │
    │  4. Calculate growth rates         │
    │  5. Generate statistical summary   │
    │  6. Analyze trends                 │
    │  7. Compute health indicators      │
    │  8. Calculate volatility           │
    │  9. Determine lifecycle stage      │
    │ 10. Detect anomalies               │
    │ 11. Generate ML features           │
    └────────────────────────────────────┘
          │
          ▼
    ┌─────────────┐
    │   Store in  │ ─── MongoDB Wrapper ─── MongoDB
    │   MongoDB   │                          (Entities DB)
    └─────────────┘
          │
          ▼
    Unified Profile Created!
```

## Profile Structure

```
Unified Company Profile Document
│
├── cik: "0000320193"
├── generated_at: "2024-11-29T12:00:00"
├── last_updated: "2024-11-29T12:00:00"
│
├── company_info
│   ├── ticker: "AAPL"
│   ├── name: "Apple Inc."
│   └── cik_numeric: 320193
│
├── filing_metadata
│   ├── total_filings: 156
│   ├── form_counts: {"10-K": 12, "10-Q": 48, ...}
│   ├── filings_per_year: {"2024": 12, "2023": 12, ...}
│   ├── most_recent_filing: "2024-11-01"
│   ├── oldest_filing: "2010-01-15"
│   └── filing_date_range_days: 5400
│
├── financial_time_series
│   ├── Revenues: {"2024-09-30": 391035000000, ...}
│   ├── Assets: {"2024-09-30": 364980000000, ...}
│   ├── NetIncomeLoss: {...}
│   └── ... (11 metrics)
│
├── latest_financials
│   ├── Revenues: 391035000000
│   ├── Assets: 364980000000
│   ├── NetIncomeLoss: 93736000000
│   └── ... (all latest values)
│
├── financial_ratios
│   ├── debt_to_equity: 1.4567
│   ├── return_on_equity: 0.4821
│   ├── profit_margin: 0.2398
│   ├── return_on_assets: 0.2567
│   └── ... (8 ratios)
│
├── growth_rates
│   ├── Revenues
│   │   ├── avg_growth_rate: 8.45
│   │   ├── latest_growth_rate: 6.07
│   │   └── median_growth_rate: 7.23
│   └── ... (for each metric)
│
├── statistical_summary
│   ├── Revenues
│   │   ├── mean: 283456789012
│   │   ├── std: 45678901234
│   │   ├── min: 156789012345
│   │   ├── max: 391035000000
│   │   └── coefficient_of_variation: 0.1612
│   └── ... (for each metric)
│
├── trend_features
│   ├── Revenues
│   │   ├── slope: 12345678.9012
│   │   ├── r_squared: 0.9567
│   │   ├── trend_direction: "increasing"
│   │   ├── trend_strength: "strong"
│   │   └── acceleration: 2345678.90
│   └── ... (for each metric)
│
├── health_indicators
│   ├── overall_health_score: 78.45
│   ├── profitability_score: 85.23
│   ├── leverage_score: 72.11
│   ├── growth_score: 76.89
│   └── health_classification: "Good"
│
├── volatility_metrics
│   ├── Revenues
│   │   ├── std_dev: 12.34
│   │   ├── variance: 152.35
│   │   ├── max_swing: 34.56
│   │   └── volatility_classification: "Moderate"
│   └── ... (for each metric)
│
├── lifecycle_features
│   ├── years_of_data: 14.8
│   ├── filing_frequency: 10.5
│   ├── growth_stage: "Stable"
│   └── maturity: "Mature"
│
├── anomaly_features
│   ├── Revenues
│   │   ├── anomaly_count: 2
│   │   ├── anomaly_percentage: 3.45
│   │   └── max_z_score: 2.87
│   └── ... (for metrics with anomalies)
│
└── ml_features (flat feature vector)
    ├── latest_Revenues: 391035000000
    ├── latest_Assets: 364980000000
    ├── ratio_return_on_equity: 0.4821
    ├── ratio_profit_margin: 0.2398
    ├── growth_Revenues_avg: 8.45
    ├── health_overall_health_score: 78.45
    ├── avg_volatility: 15.67
    └── years_of_data: 14.8
```

## Component Interaction

```
┌───────────────────────────────────────────────────────────┐
│                    Application Layer                       │
│                                                            │
│  Dashboard (Streamlit)          CLI (Interactive)         │
│        │                               │                  │
│        └───────────────┬───────────────┘                  │
│                        │                                   │
└────────────────────────┼───────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────┐
│                        │         Business Logic            │
│                        ▼                                   │
│           ┌────────────────────────┐                       │
│           │  Initialize Services   │                       │
│           └────────────────────────┘                       │
│                        │                                   │
│        ┌───────────────┼────────────────┐                  │
│        │               │                │                  │
│        ▼               ▼                ▼                  │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Ticker  │    │   SEC    │    │  Mongo   │              │
│  │Fetcher  │    │  Client  │    │ Wrapper  │              │
│  └─────────┘    └──────────┘    └──────────┘              │
│        │               │                │                  │
│        └───────────────┼────────────────┘                  │
│                        │                                   │
│                        ▼                                   │
│           ┌────────────────────────┐                       │
│           │ Unified Aggregator     │                       │
│           │                        │                       │
│           │ • Fetches data         │                       │
│           │ • Processes metrics    │                       │
│           │ • Generates profile    │                       │
│           │ • Stores results       │                       │
│           └────────────────────────┘                       │
│                        │                                   │
└────────────────────────┼───────────────────────────────────┘
                         │
┌────────────────────────┼───────────────────────────────────┐
│                        │         Data Layer                │
│                        ▼                                   │
│  ┌─────────────────────────────────────────────┐           │
│  │              MongoDB                        │           │
│  │                                             │           │
│  │  Database: Entities                         │           │
│  │  Collection: Fundamental_Data_Pipeline      │           │
│  │                                             │           │
│  │  {                                          │           │
│  │    "cik": "0000320193",                     │           │
│  │    "company_info": {...},                   │           │
│  │    "filing_metadata": {...},                │           │
│  │    "financial_time_series": {...},          │           │
│  │    "latest_financials": {...},              │           │
│  │    "financial_ratios": {...},               │           │
│  │    "growth_rates": {...},                   │           │
│  │    "health_indicators": {...},              │           │
│  │    "ml_features": {...}                     │           │
│  │  }                                          │           │
│  └─────────────────────────────────────────────┘           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Technology Stack

```
┌─────────────────────────────────────────────┐
│             Frontend/UI                      │
├─────────────────────────────────────────────┤
│ • Streamlit (Web Dashboard)                 │
│ • Plotly (Interactive Charts)               │
│ • Python CLI (Terminal Interface)           │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│           Application Logic                  │
├─────────────────────────────────────────────┤
│ • Python 3.x                                │
│ • NumPy (Numerical Computing)               │
│ • Pandas (Data Manipulation)                │
│ • Custom Business Logic                     │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│          Data Access Layer                   │
├─────────────────────────────────────────────┤
│ • PyMongo (MongoDB Driver)                  │
│ • Custom MongoWrapper                       │
│ • Caching Layer                             │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│         External Services                    │
├─────────────────────────────────────────────┤
│ • SEC EDGAR API (Filings)                   │
│ • SEC Company Tickers JSON                  │
│ • sec-edgar-api Package                     │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│            Data Storage                      │
├─────────────────────────────────────────────┤
│ • MongoDB (Document Database)               │
│ • Local File Cache (JSON)                  │
└─────────────────────────────────────────────┘
```

## File Dependencies

```
dashboard.py
├── config.py
├── mongo_client.py
├── company_ticker_fetcher.py
├── unified_profile_aggregator.py
│   ├── sec_edgar_api_client.py
│   └── mongo_client.py
└── streamlit, plotly, pandas, numpy

main_unified.py
├── config.py
├── mongo_client.py
├── company_ticker_fetcher.py
├── unified_profile_aggregator.py
│   ├── sec_edgar_api_client.py
│   └── mongo_client.py
└── subprocess (for launching dashboard)

company_ticker_fetcher.py
├── requests
├── json
└── datetime

unified_profile_aggregator.py
├── sec_edgar_api_client.py
├── mongo_client.py
├── numpy
└── datetime

sec_edgar_api_client.py
├── sec-edgar-api
└── time

mongo_client.py
└── pymongo

config.py
└── pyyaml
```

## Deployment Architecture (Future)

```
┌────────────────────────────────────────────────────┐
│                  Load Balancer                      │
└────────────────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────────┐       ┌──────────▼─────────┐
│  Web Server 1    │       │  Web Server 2      │
│  (Streamlit)     │       │  (Streamlit)       │
└───────┬──────────┘       └──────────┬─────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    Application Server        │
        │  (Python Backend)            │
        │  • Profile Aggregator        │
        │  • Ticker Fetcher            │
        │  • SEC Client                │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────────┐       ┌──────────▼─────────┐
│  MongoDB         │       │  Redis Cache       │
│  (Primary)       │       │  (Ticker Data)     │
└───────┬──────────┘       └────────────────────┘
        │
┌───────▼──────────┐
│  MongoDB         │
│  (Replica)       │
└──────────────────┘
```

This architecture shows the complete system from user interfaces down to data storage, highlighting all components and their interactions.

