# 📊 Data Dictionary - Complete Reference

**Comprehensive guide to every data point, metric, and feature in the Fundamental Data Pipeline**

This document explains **what** each data point is, **how** it's calculated, **why** it's useful, and **what insights** it provides.

---

## Table of Contents

1. [Profile Structure Overview](#profile-structure-overview)
2. [Company Information](#company-information)
3. [Financial Time Series](#financial-time-series)
4. [Financial Ratios](#financial-ratios)
5. [Growth Rates](#growth-rates)
6. [Health Indicators](#health-indicators)
7. [Material Events (8-K)](#material-events-8-k)
8. [Insider Trading (Form 4)](#insider-trading-form-4)
9. [Institutional Ownership (SC 13D/G)](#institutional-ownership-sc-13dg)
10. [Corporate Governance (DEF 14A)](#corporate-governance-def-14a)
11. [Key Persons](#key-persons)
12. [AI Analysis](#ai-analysis)
13. [Statistical Summary](#statistical-summary)
14. [Volatility Metrics](#volatility-metrics)

---

## Profile Structure Overview

Every company profile stored in MongoDB contains these main sections:

```python
{
    "cik": "0001065280",                    # SEC Company Identifier
    "company_info": {...},                   # Company metadata
    "filing_metadata": {...},                # Filing statistics
    "financial_time_series": {...},          # Historical financials
    "latest_financials": {...},              # Most recent values
    "financial_ratios": {...},               # Calculated ratios
    "growth_rates": {...},                   # Growth analysis
    "health_indicators": {...},              # Health scoring
    "material_events": {...},                # 8-K analysis
    "insider_trading": {...},                # Form 4 analysis
    "institutional_ownership": {...},        # SC 13D/G analysis
    "corporate_governance": {...},           # DEF 14A analysis
    "key_persons": {...},                    # Executives, Board, Insiders, Holdings
    "ai_analysis": {...},                    # AI insights
    "statistical_summary": {...},            # Stats
    "volatility_metrics": {...},             # Volatility
    "generated_at": "2025-12-04T10:30:00",  # Timestamp
    "last_updated": "2025-12-04T10:30:00"   # Last update
}
```

---

## Company Information

### `company_info`

**Purpose**: Basic company identification and metadata  
**Source**: SEC EDGAR submissions API

```python
{
    "ticker": "NFLX",                    # Stock ticker symbol
    "name": "NETFLIX INC",               # Official company name
    "cik": "0001065280",                 # Central Index Key (10-digit)
    "cik_numeric": 1065280,              # CIK as integer
    "sic": "7841",                       # Standard Industrial Classification
    "sic_description": "Video tape rental", # Industry description
    "entity_type": "operating",          # Entity type (operating/shell/etc)
    "fiscal_year_end": "1231",           # Fiscal year end (MMDD)
    "state_of_incorporation": "DE",      # State incorporated
    "phone": "408-540-3700",             # Contact phone
    "business_address": {...}            # Headquarters address
}
```

#### Field Explanations:

**ticker** (string)
- **What**: Stock exchange trading symbol
- **How**: Retrieved from SEC company tickers cache
- **Why**: Primary identifier for investors
- **Insights**: Used for searching and display

**cik** (string, 10-digit)
- **What**: SEC's unique company identifier
- **How**: Assigned by SEC, padded with leading zeros
- **Why**: Permanent identifier (tickers can change)
- **Insights**: Used for all SEC API requests

**sic** (string, 4-digit)
- **What**: Industry classification code
- **How**: Assigned by SEC based on business activity
- **Why**: Categorize companies by industry
- **Insights**: Useful for peer comparison (future feature)

**entity_type** (string)
- **What**: Type of corporate entity
- **Values**: "operating", "investment", "shell company"
- **Why**: Identify active vs inactive companies
- **Insights**: "shell company" = red flag

---

## Financial Time Series

### `financial_time_series`

**Purpose**: Historical financial data for trend analysis  
**Source**: SEC XBRL company facts API + 10-K/10-Q filings  
**Time Range**: Up to 30 years (configurable)

```python
{
    "Revenues": {
        "2024-12-31": 33723000000.0,     # Q4 2024
        "2024-09-30": 33000000000.0,     # Q3 2024
        "2024-06-30": 32500000000.0,     # Q2 2024
        ...                               # All historical quarters
    },
    "Assets": {
        "2024-12-31": 54934835000.0,
        ...
    },
    "Liabilities": {
        "2024-12-31": 28980800000.0,
        ...
    },
    "StockholdersEquity": {
        "2024-12-31": 25954035000.0,
        ...
    },
    "NetIncomeLoss": {
        "2024-12-31": 8562680000.0,
        ...
    },
    "CashAndCashEquivalents": {
        "2024-12-31": 9287287000.0,
        ...
    },
    ...
}
```

### Metrics Extracted:

#### 1. **Revenues** (Total Revenue, Sales)

**What**: Total income from all business operations  
**XBRL Tags Checked**:
- `Revenues`
- `RevenueFromContractWithCustomerExcludingAssessedTax`
- `SalesRevenueNet`
- `RevenueFromContractWithCustomer`
- `SalesRevenueGoodsNet`
- 10+ more variations

**How Calculated**: 
- Primary: XBRL API lookup
- Fallback: Manual 10-K/10-Q parsing
- Hybrid: Combine both sources for completeness

**Why Important**:
- **Top line growth** indicator
- Company size measurement
- Competitive positioning
- Market share proxy

**Insights Provided**:
- Revenue growth = expanding business
- Flat revenue = stagnant market or competition
- Declining revenue = losing market share (red flag)
- Seasonal patterns visible in quarterly data

**Used In**:
- Growth rate calculations
- Revenue growth charts
- Health scoring (growth component)
- Peer comparison
- AI analysis (top priority metric)

---

#### 2. **Assets** (Total Assets)

**What**: Everything the company owns that has economic value  
**XBRL Tag**: `Assets`

**Components**:
- Current assets (cash, receivables, inventory)
- Long-term assets (property, equipment, intangibles)

**Why Important**:
- Company's **resource base**
- Balance sheet strength
- Operational capacity
- Collateral for borrowing

**Insights**:
- Growing assets = expanding operations
- Asset quality matters (cash > intangibles)
- Asset turnover (revenue/assets) = efficiency
- Compare to liabilities for solvency

**Used In**:
- Return on Assets (ROA) calculation
- Balance sheet analysis
- Asset growth charts
- Health scoring (profitability component)

---

#### 3. **Liabilities** (Total Liabilities)

**What**: All debts and obligations the company owes  
**XBRL Tag**: `Liabilities`

**Components**:
- Current liabilities (short-term debt, payables)
- Long-term liabilities (bonds, long-term debt)

**Why Important**:
- **Financial risk** indicator
- Debt burden assessment
- Solvency analysis
- Interest expense driver

**Insights**:
- Rising liabilities = increasing leverage (risky)
- High debt-to-equity = financial stress
- Short-term liabilities > current assets = liquidity risk
- Debt maturity schedule matters (not in basic data)

**Used In**:
- Debt-to-Equity ratio
- Current ratio (if current assets/liabilities available)
- Health scoring (leverage component)
- Risk assessment by AI

---

#### 4. **StockholdersEquity** (Shareholders' Equity, Net Worth)

**What**: Company's net worth (Assets - Liabilities)  
**XBRL Tags**: `StockholdersEquity`, `Equity`

**Formula**: `Equity = Assets - Liabilities`

**Why Important**:
- **Ownership value**
- Book value of company
- Cushion against losses
- Return on Equity denominator

**Insights**:
- Growing equity = profitable operations
- Negative equity = insolvent (critical red flag)
- Declining equity = losses or distributions
- Compare to market cap for price-to-book ratio

**Used In**:
- Return on Equity (ROE) calculation
- Debt-to-Equity ratio
- Book value per share
- Health scoring

---

#### 5. **NetIncomeLoss** (Net Income, Profit/Loss)

**What**: Bottom-line profit after all expenses, taxes, interest  
**XBRL Tags**: `NetIncomeLoss`, `ProfitLoss`

**Formula**: `Net Income = Revenue - All Expenses - Taxes - Interest`

**Why Important**:
- **Profitability** indicator
- Earnings per share driver
- Dividend source
- Ultimate success metric

**Insights**:
- Positive = profitable company
- Negative = unprofitable (losses)
- Growing net income = improving profitability
- Net margin = net income / revenue (efficiency)

**Used In**:
- ROE and ROA calculations
- Net profit margin
- Growth rate analysis
- Health scoring (profitability component)
- AI analysis (critical metric)

---

#### 6. **CashAndCashEquivalents** (Cash)

**What**: Liquid cash and short-term investments  
**XBRL Tag**: `CashAndCashEquivalents`

**Why Important**:
- **Liquidity** indicator
- Ability to meet obligations
- Investment capacity
- Dividend payment ability

**Insights**:
- High cash = strong liquidity (safe)
- Low cash = potential liquidity issues
- Cash burn rate (if losses)
- Cash generation from operations

**Used In**:
- Liquidity analysis
- Cash charts
- Health scoring
- Risk assessment

---

#### 7. **OperatingIncomeLoss** (Operating Income, EBIT)

**What**: Profit from core business operations  
**XBRL Tag**: `OperatingIncomeLoss`

**Formula**: `Operating Income = Revenue - Operating Expenses`

**Why Important**:
- **Core business profitability**
- Excludes financing effects
- Operating efficiency
- Industry comparison

**Insights**:
- Positive = core business is profitable
- Operating margin = operating income / revenue
- Compare to net income for non-operating effects
- Trend shows core business health

**Used In**:
- Operating margin calculation
- Profitability analysis
- AI analysis

---

#### 8. **CurrentAssets** / **CurrentLiabilities**

**What**: Short-term assets/obligations (within 1 year)  
**XBRL Tags**: `AssetsCurrent`, `LiabilitiesCurrent`

**Why Important**:
- **Short-term liquidity**
- Working capital calculation
- Current ratio calculation

**Current Ratio Formula**: `Current Assets / Current Liabilities`

**Insights**:
- Current ratio > 2.0 = strong liquidity
- Current ratio 1.0-2.0 = adequate
- Current ratio < 1.0 = liquidity risk (red flag)

**Used In**:
- Current ratio (if available)
- Working capital analysis
- Liquidity scoring

---

#### 9. **LongTermDebt**

**What**: Debt obligations due beyond 1 year  
**XBRL Tag**: `LongTermDebt`

**Why Important**:
- **Long-term leverage**
- Interest expense burden
- Refinancing risk
- Credit rating factor

**Insights**:
- High long-term debt = leverage risk
- Debt-to-equity ratio calculation
- Interest coverage important
- Maturity schedule matters

**Used In**:
- Debt-to-equity ratio
- Leverage analysis
- Health scoring (leverage component)
- Risk assessment

---

### Complete List of Extracted Metrics:

| Metric | XBRL Tag(s) | Importance | Used For |
|--------|-------------|------------|----------|
| **Revenues** | Revenues, SalesRevenueNet, etc. | 🔴 Critical | Growth, margins, size |
| **Assets** | Assets | 🔴 Critical | ROA, balance sheet |
| **Liabilities** | Liabilities | 🔴 Critical | Leverage, risk |
| **Equity** | StockholdersEquity | 🔴 Critical | ROE, book value |
| **Net Income** | NetIncomeLoss | 🔴 Critical | Profitability, EPS |
| **Cash** | CashAndCashEquivalents | 🟡 Important | Liquidity |
| **Operating Income** | OperatingIncomeLoss | 🟡 Important | Core profitability |
| **Current Assets** | AssetsCurrent | 🟡 Important | Liquidity ratio |
| **Current Liabilities** | LiabilitiesCurrent | 🟡 Important | Liquidity ratio |
| **Long-Term Debt** | LongTermDebt | 🟡 Important | Leverage |
| **Cost of Revenue** | CostOfRevenue | 🟢 Optional | Gross margin |
| **Gross Profit** | GrossProfit | 🟢 Optional | Margin analysis |
| **EBITDA** | (Calculated) | 🟢 Optional | Cash flow proxy |

**Total Metrics**: 15-20 depending on company's reporting

---

## Financial Ratios

### `financial_ratios`

**Purpose**: Key performance metrics calculated from financial data  
**Source**: Calculated from latest_financials  
**Frequency**: One calculation per profile (most recent period)

```python
{
    "return_on_equity": 0.3498,          # 34.98% ROE
    "return_on_assets": 0.1558,          # 15.58% ROA
    "debt_to_equity": 1.117,             # 111.7% debt/equity
    "net_profit_margin": 0.2546,         # 25.46% margin
    "operating_margin": 0.2234,          # 22.34% margin
    "gross_margin": 0.4123,              # 41.23% margin
    "asset_turnover": 0.6123,            # 0.61x turnover
    "equity_multiplier": 2.245           # 2.25x leverage
}
```

### Ratio Definitions:

#### 1. **Return on Equity (ROE)**

**Formula**: `Net Income / Stockholders' Equity`

**What**: Profit generated per dollar of shareholder investment  
**Range**: -100% to +∞ (typically 5-25% is good)

**Interpretation**:
- **> 20%**: Excellent profitability
- **15-20%**: Good profitability
- **10-15%**: Average profitability
- **5-10%**: Below average
- **< 5%**: Poor profitability
- **Negative**: Company is losing money

**Why Important**:
- **Key profitability metric**
- Measures management effectiveness
- Shows return to shareholders
- Compare to industry average
- Warren Buffett's favorite metric

**What Insights**:
- High ROE = efficient capital use
- Improving ROE = better management
- ROE > cost of equity = value creation
- ROE from high leverage = risky

**Red Flags**:
- ROE > 50%: Unsustainably high or leverage-driven
- Negative ROE: Unprofitable company
- Declining ROE: Deteriorating business

**Used By AI**:
- Primary profitability indicator
- Decision summary metric (#1)
- Investment thesis component
- Peer comparison (future)

---

#### 2. **Return on Assets (ROA)**

**Formula**: `Net Income / Total Assets`

**What**: Profit generated per dollar of assets  
**Range**: -50% to +50% (typically 3-10% is good)

**Interpretation**:
- **> 10%**: Excellent asset efficiency
- **5-10%**: Good efficiency
- **2-5%**: Average
- **< 2%**: Poor efficiency
- **Negative**: Losses

**Why Important**:
- **Asset utilization** measure
- Industry comparison
- Capital intensity indicator
- Management efficiency

**What Insights**:
- High ROA = efficient operations
- Low ROA = capital-intensive business or inefficiency
- Compare across similar industries
- Technology companies: high ROA (low assets)
- Manufacturers: lower ROA (high assets)

**Difference from ROE**:
- ROA ignores leverage (debt)
- ROE includes leverage effect
- `ROE = ROA × Equity Multiplier`

**Used By AI**:
- Profitability assessment
- Decision summary metric (#2)
- Operational efficiency indicator

---

#### 3. **Debt-to-Equity Ratio**

**Formula**: `Total Liabilities / Stockholders' Equity`

**What**: Leverage ratio showing debt relative to equity  
**Range**: 0 to +∞ (typically 0.3-1.5 is normal)

**Interpretation**:
- **< 0.3**: Conservative (low leverage)
- **0.3-1.0**: Moderate leverage
- **1.0-2.0**: High leverage
- **> 2.0**: Very high leverage (risky)
- **> 5.0**: Extreme leverage (danger)

**Why Important**:
- **Financial risk** indicator
- Solvency assessment
- Interest expense burden
- Credit rating factor

**What Insights**:
- Low ratio = less financial risk, lower returns
- High ratio = higher financial risk, higher potential returns
- Ratio > 2.0 = vulnerability to downturns
- Negative equity = insolvency (critical)

**Industry Variation**:
- Technology: 0.2-0.8 (low leverage)
- Utilities: 1.0-2.5 (high leverage, stable cash flows)
- Finance: 5.0-15.0 (different calculation for banks)

**Red Flags**:
- Ratio > 3.0 in non-financial companies
- Rapidly increasing ratio
- Negative equity

**Used By AI**:
- Risk assessment
- Decision summary metric (#3)
- Leverage scoring in health indicators

---

#### 4. **Net Profit Margin**

**Formula**: `Net Income / Revenue`

**What**: Percentage of revenue that becomes profit  
**Range**: -100% to +100% (typically 5-20%)

**Interpretation**:
- **> 20%**: Excellent margins
- **10-20%**: Good margins
- **5-10%**: Average margins
- **< 5%**: Thin margins
- **Negative**: Unprofitable

**Why Important**:
- **Profitability efficiency**
- Pricing power indicator
- Cost control measure
- Competitive advantage

**What Insights**:
- High margin = pricing power or efficiency
- Improving margin = better cost control
- Compare to industry average
- Margin compression = competitive pressure

**Industry Examples**:
- Software: 20-30% (high margin)
- Retail: 2-5% (low margin)
- Pharmaceuticals: 15-25% (high margin)

**Used By AI**:
- Profitability assessment
- Competitive position
- Business model quality

---

#### 5. **Operating Margin**

**Formula**: `Operating Income / Revenue`

**What**: Profit from operations as % of revenue  
**Range**: -50% to +50% (typically 5-25%)

**Why Important**:
- **Core business profitability**
- Excludes financing/tax effects
- Better for comparison
- Shows operating efficiency

**What Insights**:
- Measures core business strength
- Higher than net margin = tax/interest burden
- Lower than net margin = non-operating income
- Improving trend = operational improvements

**Used By AI**:
- Core business assessment
- Operational efficiency

---

#### 6. **Gross Margin**

**Formula**: `Gross Profit / Revenue`  
**Alt Formula**: `(Revenue - Cost of Revenue) / Revenue`

**What**: Profit before operating expenses  
**Range**: 0% to 100% (typically 20-80%)

**Why Important**:
- **Fundamental profitability**
- Pricing power
- Production efficiency
- Business model indicator

**What Insights**:
- High gross margin = strong pricing power
- Low gross margin = commodity business
- Gross margin > 40% = good business model
- Declining margin = pricing pressure

**Industry Examples**:
- Software: 70-90% (very high)
- Retail: 20-40% (low to moderate)
- Manufacturing: 30-50% (moderate)

**Used By AI**:
- Business model quality
- Competitive moat assessment

---

#### 7. **Asset Turnover**

**Formula**: `Revenue / Total Assets`

**What**: How efficiently assets generate revenue  
**Range**: 0.1 to 3.0+ (varies widely by industry)

**Why Important**:
- **Asset efficiency**
- Capital intensity measure
- Sales productivity

**What Insights**:
- High turnover = efficient asset use
- Low turnover = capital-intensive business
- Retail/services: high turnover
- Utilities/manufacturing: low turnover

**DuPont Analysis**:
`ROE = Net Margin × Asset Turnover × Equity Multiplier`

**Used By AI**:
- Efficiency assessment
- Industry positioning

---

#### 8. **Equity Multiplier**

**Formula**: `Total Assets / Stockholders' Equity`

**What**: Leverage measure (how much assets per equity dollar)  
**Range**: 1.0 to 10.0+ (typically 1.5-3.0)

**Interpretation**:
- **1.0**: No debt (100% equity financed)
- **2.0**: 50% debt, 50% equity
- **3.0**: 67% debt, 33% equity
- **> 5.0**: Highly leveraged

**Why Important**:
- **Leverage component** in DuPont analysis
- Shows capital structure
- Risk indicator

**What Insights**:
- Higher multiplier = more leverage = more risk
- ROE amplification from leverage
- `ROE = ROA × Equity Multiplier`

**Used By AI**:
- DuPont analysis
- Capital structure assessment

---

### Ratio Summary Table:

| Ratio | Formula | Good Range | What It Shows |
|-------|---------|------------|---------------|
| **ROE** | Net Income / Equity | 15-25% | Shareholder returns |
| **ROA** | Net Income / Assets | 5-15% | Asset efficiency |
| **Debt/Equity** | Liabilities / Equity | 0.3-1.0 | Financial leverage |
| **Net Margin** | Net Income / Revenue | 10-20% | Overall profitability |
| **Operating Margin** | Operating Income / Revenue | 10-20% | Core business profit |
| **Gross Margin** | Gross Profit / Revenue | 30-60% | Pricing power |
| **Asset Turnover** | Revenue / Assets | 0.5-2.0 | Asset productivity |
| **Equity Multiplier** | Assets / Equity | 1.5-2.5 | Leverage measure |

---

## Growth Rates

### `growth_rates`

**Purpose**: Measure how fast key metrics are growing  
**Source**: Calculated from financial_time_series  
**Method**: Period-over-period percentage change

```python
{
    "Revenues": {
        "avg_growth_rate": 12.5,         # Average 12.5% growth
        "median_growth_rate": 11.2,      # Median 11.2%
        "min_growth_rate": -5.3,         # Worst period: -5.3%
        "max_growth_rate": 28.4,         # Best period: 28.4%
        "volatility": 8.7,               # Standard deviation
        "growth_periods": [              # All periods
            {
                "from": "2023-12-31",
                "to": "2024-12-31",
                "growth_rate": 15.2
            },
            ...
        ]
    },
    "NetIncomeLoss": {...},
    "Assets": {...},
    ...
}
```

### Growth Metrics Explained:

#### **avg_growth_rate** (Average Growth Rate)

**Formula**: `Average of all period-over-period % changes`

**Example**:
```
Revenue 2023: $100M
Revenue 2024: $115M
Growth = ($115 - $100) / $100 = 15%
```

**What**:Average growth across all periods  
**Why**: Smooths out volatility  
**Good Values**:
- **> 20%**: High growth (growth stock)
- **10-20%**: Moderate growth
- **5-10%**: Stable growth
- **< 5%**: Slow growth
- **Negative**: Declining (red flag)

**Insights**:
- Consistent with company maturity
- Compare to industry growth
- Higher growth = higher valuation
- Sustainable growth matters

**Used In**:
- Decision Summary (#4 metric)
- Growth classification
- AI analysis
- Valuation context

---

#### **median_growth_rate** (Median Growth)

**What**: Middle value of all growth rates  
**Why**: Less affected by outliers  
**When Better**: If extreme periods skew average

**Example**:
```
Growth rates: [5%, 10%, 12%, 50%, 8%]
Average: 17% (skewed by 50%)
Median: 10% (more representative)
```

---

#### **min_growth_rate** / **max_growth_rate**

**What**: Worst and best growth periods  
**Why**: Shows range of outcomes  
**Insights**:
- Large range = volatile business
- Negative min = experienced decline
- Very high max = one-time event possible

---

#### **volatility** (Standard Deviation)

**What**: How much growth rates vary  
**Low Volatility**: < 5% (stable)  
**Medium**: 5-15% (normal)  
**High**: > 15% (unstable)

**Why Important**:
- **Predictability** indicator
- Risk measure
- Business stability

**Insights**:
- Low volatility = predictable growth
- High volatility = uncertain outcomes
- Utilities: low volatility
- Tech: higher volatility

---

## Health Indicators

### `health_indicators`

**Purpose**: Comprehensive 0-100 health score with components  
**Source**: Calculated from ratios and growth rates  
**Frequency**: Once per profile

```python
{
    "overall_health_score": 75.3,        # 0-100 scale
    "classification": "Good",            # Excellent/Good/Fair/Poor
    "profitability_score": 82.0,         # 0-100
    "leverage_score": 71.0,              # 0-100
    "growth_score": 68.0,                # 0-100
    "component_scores": {...}            # Detailed breakdown
}
```

### Health Score Components:

#### **overall_health_score** (0-100)

**Formula**:
```python
overall = (profitability_score × 0.40 +
           leverage_score × 0.30 +
           growth_score × 0.30)
```

**Weights**:
- Profitability: **40%** (most important)
- Leverage: **30%** (risk factor)
- Growth: **30%** (future potential)

**Classification**:
- **90-100**: Excellent (top 10%)
- **70-89**: Good (above average)
- **50-69**: Fair (average)
- **30-49**: Poor (below average)
- **0-29**: Critical (bottom 10%)

**What**: Overall company health  
**Why**: Quick assessment metric  
**Insights**: Single number company quality

---

#### **profitability_score** (0-100)

**Components**:
- ROE (40% weight)
- ROA (30% weight)
- Net Profit Margin (30% weight)

**Scoring**:
- ROE > 20% → 100 points
- ROE 15-20% → 80-100 points
- ROE 10-15% → 60-80 points
- ROE 5-10% → 40-60 points
- ROE < 5% → 0-40 points

**What**: How profitable the company is  
**Why**: Profitability = value creation  
**Insights**: High score = strong earnings

---

#### **leverage_score** (0-100)

**Components**:
- Debt-to-Equity ratio (primary)
- Equity multiplier (secondary)

**Scoring** (inverse - lower debt = higher score):
- D/E < 0.3 → 100 points (conservative)
- D/E 0.3-1.0 → 70-100 points (moderate)
- D/E 1.0-2.0 → 40-70 points (high)
- D/E 2.0-3.0 → 20-40 points (very high)
- D/E > 3.0 → 0-20 points (extreme)

**What**: Financial risk level  
**Why**: High debt = high risk  
**Insights**: Low score = risky capital structure

---

#### **growth_score** (0-100)

**Components**:
- Revenue growth (50% weight)
- Net income growth (30% weight)
- Asset growth (20% weight)

**Scoring**:
- Growth > 20% → 100 points
- Growth 15-20% → 80-100 points
- Growth 10-15% → 60-80 points
- Growth 5-10% → 40-60 points
- Growth 0-5% → 20-40 points
- Negative growth → 0-20 points

**What**: How fast company is growing  
**Why**: Growth = future potential  
**Insights**: High score = expanding business

---

## Material Events (8-K)

### `material_events`

**Purpose**: Track significant corporate events between reports  
**Source**: 8-K filings from SEC  
**Importance**: Early warning system for risks/opportunities

```python
{
    "total_8k_count": 150,
    "recent_count": 4,                   # Last 90 days
    "avg_events_per_quarter": 3.2,
    "risk_flags": [
        "High 8-K frequency: 12 filings in 90 days (unusual)"
    ],
    "positive_catalysts": [
        "Consistent disclosure activity (good transparency)"
    ],
    "event_frequency": {                 # Monthly breakdown
        "2024-12": 2,
        "2024-11": 1,
        ...
    },
    "events": [...]                      # Recent events
}
```

### 8-K Item Categories:

#### **Item 1.01**: Entry into Material Agreement

**What**: Major contracts, partnerships, deals  
**Why Important**: Revenue/cost impact  
**Insight**: Positive catalyst if favorable terms  
**Example**: Major licensing deal, supplier contract

**Red Flag If**: Termination of previous agreement  
**Bullish If**: New partnership with major company

---

#### **Item 1.02**: Termination of Material Agreement

**What**: End of significant contracts  
**Why Important**: Lost revenue source  
**Insight**: Usually negative  
**Red Flag**: Large customer/supplier termination

---

#### **Item 2.02**: Results of Operations

**What**: Earnings announcements  
**Why Important**: First look at quarterly results  
**Insight**: Often filed before 10-Q  
**Look For**: Guidance, commentary

---

#### **Item 4.02**: Non-Reliance on Previous Financials

**What**: Accounting restatement announced  
**Why Important**: 🔴 MAJOR RED FLAG  
**Insight**: Financial reporting issues  
**Impact**: Stock price drop, investigations

**This is critical**: Company admitting errors in past reports

---

#### **Item 5.02**: Departure/Election of Officers/Directors

**What**: CEO, CFO, director changes  
**Why Important**: Management stability  
**Insights**:
- **CEO/CFO departure**: Red flag (especially if unexpected)
- **New directors**: Positive (if reputable)
- **Mass departures**: Major red flag

---

#### **Item 8.01**: Other Events

**What**: Catch-all for material news  
**Examples**: Product launches, strategic changes  
**Why Important**: Company discretion on disclosure  
**Insight**: Review content for significance

---

### Material Events Analysis:

**total_8k_count**:
- **What**: All 8-K filings in database  
- **Normal**: 4-12 per year (quarterly earnings + events)  
- **High**: > 20 per year (active company or issues)  
- **Very High**: > 30 per year (potential instability)

**recent_count** (90 days):
- **What**: Recent material events  
- **Normal**: 1-3 per quarter  
- **High**: > 5 (elevated activity)  
- **Red Flag**: > 10 (unusual activity)

**avg_events_per_quarter**:
- **Ideal**: 2-4 (earnings + 1-2 events)  
- **Low**: < 2 (may indicate limited transparency)  
- **High**: > 6 (volatile or complex events)

**risk_flags**:
- **What**: Automated detection of concerning patterns  
- **Examples**:
  - High frequency (> 10 in 90 days)
  - Clustered filings (3+ in 30 days)
  - Decreased activity (transparency concern)

**positive_catalysts**:
- **What**: Favorable patterns identified  
- **Examples**:
  - Consistent disclosure (3-8 events/quarter)
  - Regular reporting pattern
  - Material agreements announced

---

## Insider Trading (Form 4)

### `insider_trading`

**Purpose**: Track executives' buying/selling of company stock  
**Source**: Form 4 filings + detailed XML parsing  
**Why Critical**: Insiders know more than public

```python
{
    "total_form4_count": 245,
    "recent_count_90d": 12,
    "sentiment": "Normal Activity",
    "activity_level": "Moderate",
    "detailed_analysis": {
        "available": True,
        "net_value": 3800000.0,          # $3.8M net buying
        "overall_signal": "Strong Bullish",
        "buy_sell_ratio": 4.17,          # 4x more buying
        "total_buy_value": 5000000.0,
        "total_sell_value": 1200000.0,
        "top_buyers": [
            ("CEO John Doe", 3),          # 3 buy transactions
            ("CFO Jane Smith", 2)
        ],
        "top_sellers": [
            ("Director Bob", 1)
        ],
        "summary": "Net buying of $3,800,000 (25,000 shares)"
    }
}
```

### Insider Trading Signals:

#### **Net Value** (Buy - Sell in dollars)

**What**: Dollar amount of net insider activity  
**How**: Sum of all buy transactions - sell transactions  
**Why Important**: Follow the money

**Interpretation**:
- **> $1M net buying**: 🟢 Strong Bullish
- **$100K-$1M net buying**: 🟢 Bullish  
- **-$100K to +$100K**: ⚪ Neutral
- **-$100K to -$1M net selling**: 🔴 Bearish
- **< -$1M net selling**: 🔴 Strong Bearish

**Insights**:
- Insiders know company prospects
- Buying = confidence in future
- Selling = may indicate concerns (or just diversification)
- Size matters: $10K vs $1M very different

**Caveats**:
- Sales for diversification normal
- Pre-planned sales (10b5-1 plans)
- Option exercises create automatic sales
- Look at pattern, not single transaction

---

#### **Buy/Sell Ratio**

**Formula**: `Total Buy Value / Total Sell Value`

**What**: Ratio of buying to selling  
**Interpretation**:
- **> 3.0**: Strong buying bias
- **1.5-3.0**: Moderate buying
- **0.67-1.5**: Balanced
- **< 0.67**: Selling bias

**Example**:
```
Buys: $5M
Sells: $1.2M
Ratio: 5.0 / 1.2 = 4.17
Interpretation: 4x more buying (very bullish)
```

---

#### **Top Buyers / Top Sellers**

**What**: Which insiders are buying/selling  
**Why Important**: CEO/CFO actions most meaningful

**Significance Hierarchy**:
1. **CEO/CFO**: Most important (strategic knowledge)
2. **Directors**: Important (board level view)
3. **10% Owners**: Important (large stake)
4. **Other Officers**: Moderate importance
5. **Low-level insiders**: Less significant

**Red Flags**:
- CEO/CFO selling heavily
- Multiple executives selling simultaneously
- Sales at high price before decline

**Bullish Signs**:
- CEO/CFO buying
- Multiple insiders buying
- Buying at current price (not options)

---

#### **Activity Level**

**Classification**:
- **Very High**: > 10 transactions/month
- **High**: 5-10 transactions/month
- **Moderate**: 2-5 transactions/month
- **Low**: 1 transaction/month
- **Very Low**: < 1 transaction/month

**What It Means**:
- **High activity**: Active insider participation (or option vesting)
- **Low activity**: Limited insider moves
- **Pattern changes**: More meaningful than absolute level

---

## Institutional Ownership (SC 13D/G)

### `institutional_ownership`

**Purpose**: Track large shareholders and activists  
**Source**: SC 13D/G filings + HTML parsing  
**Why Critical**: 🔴 Activist investors can force changes

```python
{
    "total_sc13_count": 8,
    "activist_count": 2,                  # SC 13D filings
    "institutional_interest": "High (Activist presence)",
    "detailed_analysis": {
        "available": True,
        "largest_shareholders": [
            {
                "investor_name": "Vanguard Group",
                "ownership_percent": 8.2,
                "shares_owned": 45000000,
                "is_activist": False
            },
            {
                "investor_name": "Activist Fund XYZ",
                "ownership_percent": 5.8,
                "shares_owned": 32000000,
                "is_activist": True,
                "activist_intent": "Board/Governance Changes"
            }
        ],
        "ownership_concentration": {
            "top_1": 8.2,                  # Top holder: 8.2%
            "top_3": 18.5,                 # Top 3: 18.5%
            "concentration_level": "Moderate"
        },
        "activist_details": [
            {
                "investor": "Activist Fund XYZ",
                "ownership": 5.8,
                "intent": "Board/Governance Changes",
                "filing_date": "2024-11-15"
            }
        ]
    }
}
```

### SC 13D vs SC 13G:

#### **SC 13D** (Activist)

**What**: Filed when investor owns > 5% AND intends to influence company  
**Why Critical**: 🔴 Activist situation  
**Intent Types**:
- **Board/Governance Changes**: Seeking board seats, CEO change
- **Strategic Alternatives**: Push for sale, merger, spin-off
- **Acquisition Intent**: May try to buy company
- **General Activism**: Maximize shareholder value

**Implications**:
- **Positive**: May unlock value, force improvements
- **Negative**: Management distraction, uncertainty
- **Stock Impact**: Usually positive short-term (activist premium)

**Famous Activists**:
- Carl Icahn
- Bill Ackman
- Elliott Management
- ValueAct Capital

---

#### **SC 13G** (Passive)

**What**: Filed when investor owns > 5% but passive investment  
**Why Important**: Shows institutional confidence  
**Examples**: Vanguard, BlackRock, mutual funds

**Implications**:
- Institutional endorsement
- Long-term holders
- Less dramatic than 13D

---

### Ownership Metrics:

#### **Ownership Concentration**

**top_1 (Largest Shareholder %)**:
- **< 5%**: Diffuse ownership
- **5-10%**: Moderate concentration
- **10-25%**: High concentration
- **> 25%**: Very high (control stake)

**top_3 (Top 3 Combined %)**:
- **< 15%**: Low concentration
- **15-30%**: Moderate concentration
- **30-50%**: High concentration
- **> 50%**: Controlling group

**concentration_level**:
- **Low**: Dispersed ownership, hard to influence
- **Moderate**: Normal institutional holding
- **High**: Concentrated power, easier to coordinate

**Why Important**:
- Concentrated ownership = easier activist campaigns
- Dispersed ownership = harder to effect change
- Very high concentration = possible control issues

---

### Activist Intent Categories:

1. **Board/Governance Changes**
   - Seeking board seats
   - CEO/management change
   - Governance improvements
   
2. **Strategic Alternatives**
   - Sale of company
   - Merger or acquisition
   - Spin-off divisions
   - Asset sales

3. **Acquisition Intent**
   - Buyer building position
   - Takeover attempt
   - Friendly or hostile

4. **Investment Only**
   - Actually passive despite 13D
   - "Investment purposes" language

**Detection**: Parsed from Item 4 (Purpose) in SC 13D filing

---

## Corporate Governance (DEF 14A)

### `corporate_governance`

**Purpose**: Assess management quality and alignment  
**Source**: DEF 14A proxy statements + table parsing  
**Why Important**: Good governance = better results

```python
{
    "total_proxy_count": 10,
    "governance_score": 85.0,             # 0-100 score
    "detailed_compensation": {
        "available": True,
        "latest": {
            "ceo_total_comp": 15500000.0,  # $15.5M
            "ceo_salary": 1000000.0,
            "pay_ratio": 206.7             # CEO makes 207x median
        },
        "trends": {
            "ceo_comp_growth_percent": 35.2,  # 35% growth
            "pay_ratio_trend": "Increasing"
        },
        "red_flags": [
            "High CEO-to-median pay ratio (207:1)",
            "CEO compensation grew 35.2% (rapid increase)"
        ]
    },
    "detailed_board": {
        "available": True,
        "board_size": 12,
        "independent_directors": 10,
        "independence_ratio": 0.83,        # 83% independent
        "governance_assessment": "Strong (>75% independent directors)"
    }
}
```

### Governance Metrics:

#### **Governance Score** (0-100)

**Components**:
- Regular proxy filings (30 points)
- Consistent timing (30 points)
- Years of coverage (20 points)
- Filing count (20 points)

**Scoring**:
- **90-100**: Excellent governance
- **70-89**: Good governance
- **50-69**: Adequate governance
- **< 50**: Poor governance

**What**: Overall governance quality  
**Why**: Good governance correlates with performance

---

#### **CEO Total Compensation**

**What**: All CEO pay (salary + bonus + stock + options)  
**Why Important**: Alignment with shareholders

**Interpretation**:
- **< $1M**: Small company or founder-led
- **$1M-$5M**: Small to mid cap
- **$5M-$15M**: Large cap (normal)
- **> $15M**: Very high (question alignment)
- **> $50M**: Excessive (unless exceptional performance)

**What to Check**:
- Growth rate vs stock performance
- Pay for performance alignment
- Peer comparison

---

#### **Pay Ratio** (CEO to Median Employee)

**Formula**: `CEO Total Comp / Median Employee Pay`

**What**: How many median employees = 1 CEO  
**Required By**: SEC (Dodd-Frank)

**Interpretation**:
- **< 50:1**: Low ratio (egalitarian)
- **50-150:1**: Normal ratio
- **150-300:1**: High ratio
- **> 300:1**: Very high ratio

**Good Values** (Depends on Industry):
- **Tech**: 100-300 (high-paid employees)
- **Retail**: 200-800 (low-paid employees)
- **Finance**: 50-150 (high-paid employees)

**Red Flags**:
- **> 500:1**: Excessive inequality
- **Rapidly increasing**: Misalignment
- **High ratio + poor performance**: Pay not justified

**Why Important**:
- Income inequality concern
- Employee morale impact
- Public relations
- Alignment indicator

---

#### **Board Independence**

**independence_ratio**: `Independent Directors / Total Directors`

**What**: Percentage of board that's independent  
**Independent**: No material ties to company (not exec, no business relationships)

**Best Practice**:
- **> 75%**: Excellent independence
- **50-75%**: Good independence  
- **< 50%**: Poor independence (controlled board)

**Why Important**:
- Independent directors protect shareholders
- Less conflicts of interest
- Better oversight of management
- Required by stock exchanges (majority independent)

**Red Flags**:
- **< 50% independent**: Controlled by management/founders
- **CEO is chairman**: Concentrates power
- **Family members on board**: Potential conflicts

---

## Key Persons

### `key_persons`

**Purpose**: Comprehensive extraction of key company personnel, including executives, board members, insider holdings, and major shareholders  
**Source**: DEF 14A, Form 4, SC 13D/G filings  
**Why Important**: Understanding who runs and owns a company is essential for assessing management quality, alignment with shareholders, and potential risks or opportunities

```python
{
    "executives": [                          # Key executives list
        {
            "name": "John Smith",
            "title": "CEO",
            "source": "DEF 14A",
            "filing_date": "2024-04-15"
        },
        {
            "name": "Jane Doe",
            "title": "CFO",
            "source": "DEF 14A",
            "filing_date": "2024-04-15"
        }
    ],
    "board_members": [                       # Board of directors
        {
            "name": "Robert Johnson",
            "role": "Director",
            "is_independent": True,
            "source": "DEF 14A",
            "filing_date": "2024-04-15"
        },
        {
            "name": "Board Summary",          # Board statistics
            "role": "Board Statistics",
            "total_directors": 12,
            "independent_directors": 10,
            "independence_ratio": 0.83
        }
    ],
    "insider_holdings": [                    # Insider ownership
        {
            "name": "John Smith",
            "title": "CEO",
            "shares_owned": 2500000,
            "latest_filing_date": "2024-11-15",
            "net_buy_value": 5000000.0,
            "net_sell_value": 1200000.0,
            "net_shares": 15000,
            "transaction_count": 5,
            "signal": "Bullish"
        }
    ],
    "holding_companies": [                   # Major institutional shareholders
        {
            "name": "Vanguard Group",
            "ownership_percent": 8.2,
            "shares_owned": 45000000,
            "is_activist": False,
            "form_type": "SC 13G",
            "filing_type": "Passive (13G)",
            "latest_filing_date": "2024-02-14"
        },
        {
            "name": "Activist Fund XYZ",
            "ownership_percent": 5.8,
            "shares_owned": 32000000,
            "is_activist": True,
            "activist_intent": "Board/Governance Changes",
            "purpose": "Seeking board representation...",
            "form_type": "SC 13D",
            "filing_type": "Activist (13D)",
            "latest_filing_date": "2024-11-15"
        }
    ],
    "summary": {                             # Aggregated summary
        "ceo": {
            "name": "John Smith",
            "identified": True
        },
        "cfo": {
            "name": "Jane Doe",
            "identified": True
        },
        "chairman": {
            "name": "Not identified",
            "identified": False
        },
        "executive_count": 5,
        "board_member_count": 12,
        "board_independence": {
            "total_directors": 12,
            "independent_directors": 10,
            "independence_ratio": 0.83
        },
        "insider_holdings": {
            "count": 8,
            "total_shares": 15000000,
            "total_buy_value": 25000000.0,
            "total_sell_value": 5000000.0,
            "net_activity": "Buying"
        },
        "institutional_ownership": {
            "holder_count": 5,
            "total_ownership_percent": 28.5,
            "activist_count": 1,
            "largest_holder": "Vanguard Group",
            "largest_stake": 8.2
        }
    },
    "generated_at": "2024-12-04T10:30:00"
}
```

### Key Persons Fields:

#### **executives**

**What**: List of key company executives (CEO, CFO, COO, CTO, etc.)  
**Source**: Parsed from DEF 14A proxy statements  
**Fields**:
- `name`: Full name of the executive
- `title`: Position (CEO, CFO, COO, CTO, President, Chairman, General Counsel)
- `source`: Filing type where identified
- `filing_date`: Date of the filing

**Why Important**:
- Identify who runs the company
- Track management changes
- Assess executive experience and background

---

#### **board_members**

**What**: List of board directors with independence status  
**Source**: Parsed from DEF 14A proxy statements  
**Fields**:
- `name`: Director name
- `role`: "Director" or "Board Statistics" (for summary)
- `is_independent`: Boolean indicating independence
- `total_directors`: Total board size (in summary)
- `independent_directors`: Count of independent directors
- `independence_ratio`: Percentage of independent directors

**Why Important**:
- Board oversight quality
- Governance practices
- Shareholder protection

**Best Practices**:
- **> 75% independent**: Excellent governance
- **50-75%**: Adequate
- **< 50%**: Red flag - management controlled

---

#### **insider_holdings**

**What**: Detailed insider ownership and trading activity  
**Source**: Parsed from Form 4 filings  
**Fields**:
- `name`: Insider name
- `title`: Position (CEO, CFO, Director, 10% Owner, etc.)
- `shares_owned`: Number of shares currently owned
- `latest_filing_date`: Most recent Form 4 filing date
- `net_buy_value`: Total value of purchases
- `net_sell_value`: Total value of sales
- `net_shares`: Net shares bought (positive) or sold (negative)
- `transaction_count`: Number of transactions
- `signal`: Trading signal (Strong Bullish, Bullish, Neutral, Bearish, Strong Bearish)

**Why Important**:
- Insider confidence indicator
- Skin in the game
- Early warning signals

**Interpretation**:
- **High ownership + buying**: Strong confidence
- **Heavy selling by multiple insiders**: Potential red flag
- **CEO/CFO buying**: Very significant
- **Option exercises**: Often followed by sales (less meaningful)

---

#### **holding_companies**

**What**: Major institutional shareholders and their stakes  
**Source**: Parsed from SC 13D/G filings  
**Fields**:
- `name`: Investor/institution name
- `ownership_percent`: Percentage of company owned
- `shares_owned`: Number of shares owned
- `is_activist`: Boolean indicating activist investor
- `activist_intent`: Purpose of activism (if applicable)
- `purpose`: Full purpose statement excerpt
- `form_type`: SC 13D (activist) or SC 13G (passive)
- `filing_type`: "Activist (13D)" or "Passive (13G)"
- `latest_filing_date`: Most recent filing date

**Why Important**:
- Institutional endorsement
- Activist pressure identification
- Ownership concentration

**Activist Intent Categories**:
- **Board/Governance Changes**: Seeking board seats or management changes
- **Strategic Alternatives**: Pushing for sale, merger, or spin-off
- **Acquisition Intent**: Building position for takeover
- **Investment Only**: Passive despite 13D filing

---

#### **summary**

**What**: Aggregated summary of all key persons data  
**Purpose**: Quick overview for analysis and AI

**Fields**:
- `ceo`: CEO identification (name, identified boolean)
- `cfo`: CFO identification
- `chairman`: Chairman identification
- `executive_count`: Total executives identified
- `board_member_count`: Total board members
- `board_independence`: Board independence metrics
- `insider_holdings`: Insider ownership summary
  - `count`: Number of insiders tracked
  - `total_shares`: Total shares held by insiders
  - `total_buy_value`: Total insider buying
  - `total_sell_value`: Total insider selling
  - `net_activity`: "Buying" or "Selling" or "Neutral"
- `institutional_ownership`: Institutional ownership summary
  - `holder_count`: Number of major holders
  - `total_ownership_percent`: Combined ownership
  - `activist_count`: Number of activist investors
  - `largest_holder`: Name of largest shareholder
  - `largest_stake`: Largest ownership percentage

---

### Key Persons Use Cases:

1. **Management Assessment**
   - Who is the CEO/CFO?
   - Are key executives buying or selling?
   - Is there high management turnover?

2. **Governance Analysis**
   - Is the board independent?
   - Are there activist investors?
   - What is ownership concentration?

3. **Investment Signals**
   - Insider buying = confidence
   - Activist involvement = potential catalyst
   - High institutional ownership = validation

4. **Risk Detection**
   - Mass insider selling
   - Activist campaigns
   - Board independence issues

---

## AI Analysis

### `ai_analysis`

**Purpose**: LLM-generated investment insights  
**Source**: Ollama (llama3.2, mistral, phi, llama2)  
**Input**: ALL profile data (financial + events + governance + insider + institutional)

```python
{
    "investment_thesis": "Company has strong financials with 15% revenue growth and high ROE of 28%, but faces activist investor pressure seeking board changes and has elevated CEO compensation (207:1 ratio). Recent insider buying ($3.8M) suggests management confidence. Recommend HOLD pending activist resolution.",
    
    "recommendation": "Hold",           # Buy/Hold/Sell
    "confidence": 0.78,                 # 0.0 to 1.0
    "risk_level": "Medium",             # Low/Medium/High
    
    "strengths": [
        "Strong ROE of 28% above industry average",
        "Consistent revenue growth of 15% annually",
        "Insider buying of $3.8M indicates confidence"
    ],
    
    "weaknesses": [
        "Activist investor seeking board changes (5.8% stake)",
        "High CEO compensation ratio (207:1 vs peer 150:1)",
        "Elevated debt-to-equity of 1.8"
    ],
    
    "growth_prediction": {
        "1yr": {"revenue": 15.0, "earnings": 12.0},
        "3yr": {"revenue": 45.0, "earnings": 38.0},
        "5yr": {"revenue": 82.0, "earnings": 70.0}
    },
    
    "catalysts": [
        "Potential acquisition target given activist interest",
        "New product launches in Q2 2025",
        "International expansion into Asian markets"
    ],
    
    "risks": [
        "Activist campaign may distract management",
        "High leverage limits financial flexibility",
        "Competition intensifying in core markets"
    ],
    
    "insider_signals": "Strong Bullish - Executives accumulating shares ($3.8M net buying in 90 days, 4:1 buy/sell ratio)",
    
    "institutional_signals": "Cautious - Activist Fund XYZ (5.8%) seeking board changes for governance improvements. Moderate ownership concentration (18.5% top 3).",
    
    "governance_assessment": "Mixed - Strong board independence (83%) but concerning CEO pay ratio (207:1, up 35%). Governance score 85/100 suggests good practices overall.",
    
    "provider": "ollama",
    "model": "llama3.2",
    "generated_at": "2025-12-04T10:30:00"
}
```

### AI Output Fields:

#### **investment_thesis**

**What**: 2-3 sentence comprehensive summary  
**Includes**: Financials + Events + Governance + Insider + Institutional  
**Why**: Quick understanding of investment case  
**Quality**: Should reference specific numbers and facts

---

#### **recommendation**

**Values**:
- **Strong Buy**: High confidence positive (conf > 0.80)
- **Buy**: Positive outlook
- **Hold**: Wait and see / mixed signals
- **Sell**: Negative outlook
- **Strong Sell**: High confidence negative

**Based On**:
- Financial health score
- Growth trajectory  
- Risk factors (debt, events, activists)
- Insider/institutional signals
- Governance quality

---

#### **confidence**

**Range**: 0.0 to 1.0  
**Interpretation**:
- **> 0.85**: Very high confidence
- **0.70-0.85**: High confidence
- **0.50-0.70**: Medium confidence
- **< 0.50**: Low confidence

**Factors Lowering Confidence**:
- Conflicting signals (good financials but activist pressure)
- Limited data availability
- High volatility
- Unusual events

---

#### **risk_level**

**Values**: Low / Medium / High

**Factors**:
- **Financial**: Debt levels, profitability
- **Operational**: Business model, competition
- **Governance**: Management quality, board
- **Market**: Industry trends, macro factors
- **Events**: Activists, restatements, departures

---

#### **strengths** / **weaknesses**

**What**: 3-5 bullet points each  
**Should Include**:
- Specific numbers (ROE 28%, revenue growth 15%)
- Comparisons (vs industry avg, vs peers)
- Trends (improving, declining)
- Material facts (insider buying $3.8M)

---

#### **catalysts** / **risks**

**Catalysts** (Positive drivers):
- Product launches
- Market expansion
- Strategic partnerships
- Activist unlocking value
- Industry tailwinds

**Risks** (Negative factors):
- Competition
- Regulatory changes
- Activist pressure
- Management departures
- Industry headwinds

---

#### **insider_signals** / **institutional_signals** / **governance_assessment**

**New in v1.0**: Detailed assessments of each area

**insider_signals Example**:
"Strong Bullish - Executives accumulating shares ($3.8M net buying in 90 days, 4:1 buy/sell ratio)"

**institutional_signals Example**:
"Cautious - Activist Fund XYZ (5.8%) seeking board changes"

**governance_assessment Example**:
"Mixed - Strong board (83% independent) but high CEO pay (207:1 ratio)"

**Why Important**: AI now incorporates ALL data sources, not just financials

---

## Statistical Summary

### `statistical_summary`

**Purpose**: Statistical analysis of time series data  
**Source**: Calculated from financial_time_series

```python
{
    "Revenues": {
        "mean": 30500000000.0,
        "median": 29800000000.0,
        "min": 18000000000.0,
        "max": 33723000000.0,
        "std_dev": 4200000000.0,
        "coefficient_of_variation": 0.138
    },
    ...
}
```

### Statistical Metrics:

**mean**: Average value  
**median**: Middle value (less affected by outliers)  
**min**: Lowest value in history  
**max**: Highest value in history  
**std_dev**: Standard deviation (volatility measure)  
**coefficient_of_variation**: `std_dev / mean` (normalized volatility)

---

## Volatility Metrics

### `volatility_metrics`

**Purpose**: Measure consistency and predictability  
**Source**: Calculated from growth rates

```python
{
    "Revenues": {
        "volatility": 8.7,               # Growth rate std dev
        "consistency": "Moderate",        # Low/Moderate/High
        "trend_direction": "Increasing",  # Increasing/Stable/Decreasing
        "trend_strength": 0.85            # 0-1 (R-squared)
    },
    ...
}
```

### Volatility Fields:

**volatility**: Standard deviation of growth rates  
- **< 5%**: Low volatility (stable)
- **5-15%**: Moderate volatility
- **> 15%**: High volatility (unpredictable)

**consistency**: Qualitative assessment  
**trend_direction**: Overall direction of data  
**trend_strength**: How strong the trend (R²)

---

## Summary of All Data Points

### Total Data Points Per Profile:

| Category | Data Points | Critical? |
|----------|-------------|-----------|
| Company Info | 10-15 | ✅ |
| Financial Time Series | 15-20 metrics × 100+ periods = 1500-2000 | ✅ |
| Latest Financials | 15-20 | ✅ |
| Financial Ratios | 8 | ✅ |
| Growth Rates | 15-20 metrics × 5 stats = 75-100 | ✅ |
| Health Indicators | 10 | ✅ |
| Material Events | 20+ | ✅ |
| Insider Trading | 15+ (30+ with details) | ✅ |
| Institutional Ownership | 10+ (40+ with details) | ✅ |
| Corporate Governance | 15+ (50+ with details) | ✅ |
| AI Analysis | 15+ | ✅ |
| Statistical Summary | 90-120 | Optional |
| Volatility Metrics | 60-80 | Optional |

**Total**: ~2,000-3,000 data points per company profile

---

## Data Usage Map

### What Each Component Is Used For:

| Data | Used In | Used By |
|------|---------|---------|
| **Revenues** | Growth, margins, charts | AI, health score, visualizations |
| **Net Income** | ROE, ROA, margins, growth | AI, health score, decision metrics |
| **Assets** | ROA, charts | Balance sheet analysis |
| **Liabilities** | Debt ratios, charts | Risk assessment, health score |
| **Equity** | ROE, debt ratio | Profitability, leverage |
| **ROE** | Health score, decision | AI (top priority metric) |
| **ROA** | Health score, decision | AI, efficiency analysis |
| **Debt/Equity** | Health score, decision | AI, risk assessment |
| **Growth Rates** | Health score, charts | AI, growth analysis |
| **8-K Events** | Risk assessment | AI (red flags, catalysts) |
| **Form 4** | Insider sentiment | AI (signals) |
| **SC 13D/G** | Activist detection | AI (risks, catalysts) |
| **DEF 14A** | Governance quality | AI (management assessment) |

---

## Data Quality Indicators

### Availability Flags:

Each advanced section includes `"available": True/False`:

```python
"detailed_analysis": {
    "available": True,    # Data successfully parsed
    ...
}
```

**True**: Content parsing succeeded, detailed data available  
**False**: Parsing failed, only pattern analysis available

**Why Important**: User knows level of detail available

---

## Conclusion

This data dictionary documents **every single data point** in the system:

✅ **What** it is (definition)  
✅ **How** it's calculated (formula/method)  
✅ **Why** it's important (business significance)  
✅ **What insights** it provides (interpretation)  
✅ **How it's used** (where in the system)  
✅ **Good/bad values** (benchmarks)  

**For Developers**: Understand data structures and calculations  
**For Users**: Understand what metrics mean and how to interpret  
**For AI Models**: Complete context for analysis

---

**Last Updated**: December 4, 2025  
**Version**: 1.0.0  
**Total Data Points Documented**: 100+

