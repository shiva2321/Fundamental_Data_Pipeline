# 📊 Fundamental Data Pipeline

**Institutional-Grade Financial Analysis System**

A comprehensive Python-based desktop application for analyzing SEC EDGAR company filings, generating financial profiles, and providing AI-powered investment insights using local LLM models.

---

## 🌟 Key Features

### 📈 **Complete Financial Analysis**
- **Automated Data Collection**: Fetches all historical SEC filings (10-K, 10-Q, 8-K, DEF 14A, Form 4, SC 13D/G)
- **Financial Metrics**: Revenue, assets, liabilities, equity, net income, cash flow
- **Time Series Analysis**: Historical trends, growth rates, volatility metrics
- **Financial Ratios**: ROE, ROA, debt-to-equity, profit margins, and more
- **Health Scoring**: Comprehensive 0-100 health score with profitability, leverage, and growth components
### 🔍 **Advanced Filing Analysis**
- **Material Events (8-K)**: Corporate events, management changes, accounting issues
- **Insider Trading (Form 4)**: Buy/sell transactions with dollar amounts and signals
- **Institutional Ownership (SC 13D/G)**: Activist investors, ownership percentages, intentions
- **Corporate Governance (DEF 14A)**: CEO compensation, pay ratios, board independence
- **Key Persons**: Executives, board members, insider holdings with active status tracking
- **Intelligent Fallback**: Automatic format detection and parsing strategy selection
### 🤖 **AI-Powered Insights**
- **Local LLM Integration**: Uses Ollama (llama3.2, mistral, phi, etc.)
- **Multi-Model Analysis**: Compare recommendations across different AI models
- **Comprehensive Prompts**: Includes financial data + events + governance + insider trading
- **Investment Recommendations**: Buy/Sell/Hold with confidence scores
- **Risk Assessment**: Multi-source risk analysis
- **Catalyst Identification**: Identifies growth opportunities
- **Quality Metrics**: Per-form extraction quality scoring and validation
### 📊 **Interactive Visualizations**
- **Financial Trends**: Revenue, assets, liabilities, net income over time
- **Growth Analysis**: Period-over-period growth rates with interactive charts
- **Hover Tooltips**: Detailed data on mouse hover
- **Zoom & Pan**: Interactive chart navigation
- **Export Charts**: Save charts as images
- **Multiple Views**: Absolute values, percentage change, indexed
- **Resizable Columns**: Adjust table column widths
- **Collapsible Sections**: Expand/collapse data sections

### 💾 **Data Management**
- **MongoDB Storage**: Efficient profile storage and retrieval
- **Batch Processing**: Process multiple companies in queue
- **Incremental Updates**: Update existing profiles with new data
- **Profile Manager**: View, edit, delete, and visualize profiles
- **Export Options**: Export profiles as JSON
- **Automated Validation**: Quick parser import and functionality checks

---

## 📁 Project Structure

```
Fundamental_Data_Pipeline/
├── main.py                 # Application entry point
├── src/                    # Source code package
│   ├── parsers/           # SEC filing parsers
│   │   ├── def14a_parser.py
│   │   ├── form4_parser.py
│   │   ├── form_8k_parser.py
│   │   ├── sc13_parser.py
│   │   ├── filing_content_parser.py
│   ├── clients/           # External service clients
│   │   ├── sec_edgar_api_client.py
│   │   ├── mongo_client.py
│   │   └── company_ticker_fetcher.py
│   ├── ui/               # User interface components
│   │   ├── desktop_app_pyside.py
│   │   ├── visualization_window.py
│   │   ├── ollama_manager_dialog.py
│   │   └── profile_period_editor.py
│   ├── analysis/         # Data analysis modules
│   │   ├── ai_analyzer.py
│   │   └── unified_profile_aggregator.py
│   └── utils/            # Utility modules
│       ├── config.py
│       ├── email_notifier.py
│       └── ollama_model_manager.py
├── config/               # Configuration files
│   └── config.yaml
├── docs/                 # Documentation
│   ├── AI_SETUP_GUIDE.md
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   ├── GETTING_STARTED.md
│   ├── KEY_PERSONS_FINAL_FIX.md
│   └── QUICK_REFERENCE_KEY_PERSONS.md
├── tools/                # Testing and utility scripts
├── requirements.txt      # Python dependencies
├── run.bat              # Windows launcher
└── run.sh               # Linux/Mac launcher
└── requirements.txt    # Python dependencies
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+ required

# MongoDB required (local or cloud)
# Download from: https://www.mongodb.com/try/download/community

# Ollama required for AI features (optional)
# Download from: https://ollama.ai
python --version
```

### Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd Fundamental_Data_Pipeline

# 2. Create virtual environment
python -m venv .venv
# 3. Activate virtual environment
# Windows:
# 3. Activate virtual environment (Windows)
# Linux/Mac:
source .venv/bin/activate
.venv\Scripts\activate

# 4. Install dependencies

# 5. Install Ollama models (for AI features)
ollama pull llama3.2
ollama pull mistral
ollama pull phi
pip install -r requirements.txt
```
### Configuration
### Fetch Sample Filings
Edit `config/config.yaml`:
python try.py
```yaml
mongodb:
  uri: "mongodb://localhost:27017/"
  database: "sec_profiles"

profile_settings:
  lookback_years: 30
  ai_enabled: true
  ai_model: "llama3.2"
  email_notifications: false
# This will download sample filings to sec_filings/
```
### Running the Application
### Run Tests

# Windows
run.bat
python validate_all_parsers.py
# Linux/Mac
./run.sh
python test_parsers_offline.py
# Or directly
python main.py
python integrated_fetch_parse_test.py --ticker AAPL
- `Forms/` - 150+ form parsers

---
## 📖 Usage Guide
```
### 1. **Generate Company Profiles**
```
1. Click **Dashboard_Generate** tab
2. Enter ticker symbols (e.g., `AAPL, MSFT, GOOGL`)
3. Click **Add to Queue**
4. Click **Start Processing**
5. Monitor progress in Queue Monitor tab
python test_parsers_offline.py
### 2. **View Profiles**
python integrated_fetch_parse_test.py --ticker AAPL
1. Click **Profile Manager** tab
2. Select a profile from the list
3. Click **Visualize Selected**
4. Explore tabs:
   - **Overview**: Company info, latest financials, health summary
   - **Decision Summary**: Key metrics, investment recommendation
   - **Financial Trends**: Charts of revenue, assets, liabilities, net income
   - **Financial Ratios**: ROE, ROA, margins, ratios
   - **Growth Analysis**: Period-over-period growth rates
   - **Health Indicators**: Detailed health scoring breakdown
   - **AI/ML Analysis**: AI-powered investment insights
```
### 3. **AI Analysis**
4. Update quality metrics
**Multi-Model Analysis:**
1. Go to Settings tab
2. Enable AI analysis
3. Select multiple models (llama3.2, mistral, phi, llama2)
4. Generate profiles
5. AI/ML Analysis tab shows consensus and individual model recommendations
---
**Single Model:**
- Set one model in config
- Get faster analysis from that model
## 📊 Current Status
### 4. **Interactive Charts**
**Forms Tested**: 10-K, 10-Q, 8-K, 3, 4, 5, DEF 14A, SC 13G, and 140+ more
- **Hover**: See exact values on data points
- **Double-click**: Open chart in interactive window
- **Zoom**: Scroll wheel to zoom in/out
- **Pan**: Click and drag to pan
- **Reset**: Home button to reset view
See [TEST_RESULTS_SUMMARY.md](TEST_RESULTS_SUMMARY.md) for detailed results.

---
## 🏗️ Architecture
## 🎯 Roadmap
### Core Components
- [ ] REST API for parser access
```
Fundamental_Data_Pipeline/
├── desktop_app_pyside.py          # Main application (PySide6)
├── visualization_window.py         # Chart and visualization
├── unified_profile_aggregator.py  # Profile generation engine
├── sec_edgar_api_client.py        # SEC EDGAR API client
├── ai_analyzer.py                 # AI/ML analysis
├── mongo_client.py                # MongoDB interface
│
├── Filing Parsers:
│   ├── form_8k_parser.py          # Material events (8-K)
│   ├── form4_parser.py            # Insider trading (Form 4)
│   ├── sc13_parser.py             # Institutional ownership (SC 13D/G)
│   ├── def14a_parser.py           # Corporate governance (DEF 14A)

│   ├── key_persons_parser.py      # Key persons extraction (executives, board, insiders, holdings)
│   └── filing_content_parser.py   # Content fetching & parsing
│
├── UI Components:
│   ├── ollama_manager_dialog.py   # Ollama model management
│   ├── ollama_model_manager.py    # Model manager backend
│   └── profile_period_editor.py   # Period editor dialog
│
├── Utilities:
│   ├── company_ticker_fetcher.py  # Ticker lookup
│   ├── email_notifier.py          # Email notifications
│   └── config.py                  # Configuration
│
├── config/
│   └── config.yaml                # Application settings
│
└── docs/
    ├── ARCHITECTURE.md            # Technical architecture
    ├── AI_SETUP_GUIDE.md          # Ollama setup guide
    ├── IMPLEMENTATION_DETAILS.md  # Implementation details
    └── GETTING_STARTED.md         # Getting started guide
```

### Data Flow

```
1. User adds ticker → Queue
2. SEC EDGAR API → Fetch ALL filings (1000+)
3. Parse filings:
   - 10-K/10-Q → Financial metrics
   - 8-K → Material events
   - Form 4 → Insider transactions (buy/sell amounts)
   - SC 13D/G → Ownership data (investor names, %)
   - DEF 14A → Compensation (CEO pay, ratios)
4. Calculate:
   - Financial ratios
   - Growth rates
   - Health scores
   - Trends and volatility
5. AI Analysis:
   - Create comprehensive prompt with ALL data
   - Send to Ollama models
   - Generate recommendations
6. Store in MongoDB
7. Display in UI with interactive charts
```

---

## 📊 Data Extracted

### Financial Metrics (from 10-K/10-Q):
- Revenue, Assets, Liabilities, Equity
- Net Income, Operating Income, EBIT, EBITDA
- Cash, Cash Equivalents, Current Assets/Liabilities
- Long-term Debt, Total Debt
- Stockholders Equity

### Material Events (from 8-K):
- Management changes (CEO, CFO departures)
- Accounting issues (restatements, auditor changes)
- Acquisitions, divestitures
- Major agreements
- Financial obligations
- Event frequency patterns

### Insider Trading (from Form 4):
- Transaction type (buy, sell, option exercise)
- Number of shares
- Price per share
- Total transaction value
- Insider name and title
- Net buying/selling amounts
- Buy/sell signal (Bullish/Bearish)

### Institutional Ownership (from SC 13D/G):
- Investor name
- Ownership percentage
- Number of shares owned
- Activist vs passive investor
- Activist intentions (board changes, strategic alternatives)
- Ownership concentration

### Corporate Governance (from DEF 14A):
- CEO total compensation
- CEO salary, bonus, stock awards
- Pay ratio (CEO to median employee)
- Board size and composition
- Number of independent directors
- Independence ratio

### Key Persons (Consolidated View):
- **Executives**: CEO, CFO, COO, CTO, and other key officers with titles
- **Board Members**: Directors with independence status
- **Insider Holdings**: Individual insider ownership with shares and transaction signals
- **Holding Companies**: Major institutional shareholders with ownership percentages and stakes
- **Activist Investors**: Identified activists with their stated intentions

---

## 🤖 AI Models

### Supported Models

**Via Ollama:**
- `llama3.2` - Fast, accurate (recommended)
- `llama2` - Stable, reliable
- `mistral` - Good balance
- `phi` - Lightweight, fast

### AI Output

```json
{
  "investment_thesis": "Comprehensive analysis...",
  "recommendation": "Buy|Hold|Sell",
  "confidence": 0.85,
  "strengths": ["...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "risks": ["...", "..."],
  "catalysts": ["...", "..."],
  "insider_signals": "Strong Bullish - $3.8M net buying",
  "institutional_signals": "Cautious - Activist pressure",
  "governance_assessment": "Mixed - Strong board but high CEO pay"
}
```

---

## 🔧 Configuration Options

### `config/config.yaml`

```yaml
mongodb:
  uri: "mongodb://localhost:27017/"  # MongoDB connection
  database: "sec_profiles"           # Database name

profile_settings:
  lookback_years: 30                 # Years of historical data
  ai_enabled: true                   # Enable AI analysis
  ai_model: "llama3.2"               # Default AI model
  multi_model_enabled: false         # Multi-model analysis
  selected_models:                   # Models for multi-model
    - "llama3.2"
    - "mistral"
  email_notifications: false         # Email alerts
  email_recipient: "your@email.com"

sec_edgar:
  user_agent: "YourName your@email.com"  # Required by SEC
  rate_limit: 0.1                    # Seconds between requests
```

---

## 📈 Performance

- **Filings per company**: 1,000+ (all historical with pagination)
- **Detailed parsing**: Recent 20 Form 4s, 10 SC 13s, 5 DEF 14As
- **Processing time**: ~30-60 seconds per company (depends on AI)
- **Storage**: ~500KB-2MB per profile
- **Rate limit**: 10 requests/second to SEC (compliant)

---

## 🛠️ Troubleshooting

### MongoDB Connection Failed
```bash
# Check MongoDB is running
mongod --version

# Start MongoDB service
# Windows: Services → MongoDB
# Linux: sudo systemctl start mongod
```

### Ollama Not Available
```bash
# Check Ollama is running
ollama list

# Start Ollama service
ollama serve

# Pull missing models
ollama pull llama3.2
```

### No Revenue Data
- Revenue extraction uses multiple field names
- Some companies may not report in standard XBRL format
- Check raw financial data in MongoDB for alternatives

### Charts Not Displaying
- Ensure matplotlib backend is installed
- Check PySide6 installation: `pip install PySide6`
- Try reopening visualization window

---

## 📚 Complete Documentation

### Main Guides:
- **README.md** (this file) - Overview and quick start
- **[Getting Started](docs/GETTING_STARTED.md)** - Step-by-step setup guide
- **[Data Dictionary](docs/DATA_DICTIONARY.md)** - Complete reference for all metrics ⭐
- **[Architecture](docs/ARCHITECTURE.md)** - Technical architecture and design
- **[Implementation Details](docs/IMPLEMENTATION_DETAILS.md)** - How everything works
- **[AI Setup Guide](docs/AI_SETUP_GUIDE.md)** - Ollama configuration
- **[Changelog](docs/CHANGELOG.md)** - Version history

### What Each Document Covers:

**📖 DATA_DICTIONARY.md** (⭐ Essential for understanding data):
- Every single data point explained (100+ metrics)
- What each metric is, how it's calculated, why it's important
- Good/bad value ranges and industry benchmarks
- What insights each metric provides
- How each metric is used in analysis
- Complete profile structure documentation

**🏗️ ARCHITECTURE.md**:
- System components and data flow
- Technology stack
- Database schema
- API integrations
- Performance considerations

**🚀 GETTING_STARTED.md**:
- Installation steps
- First-time setup
- Processing your first company
- Common issues and solutions

---

## 📝 License

[Your License Here]

---

## 🤝 Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

---

## 📧 Support

For issues and questions:
- GitHub Issues: [Repository Issues]
- Email: [Your Email]
- **Data Questions**: See [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)
- **Setup Help**: See [GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Technical Details**: See [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🙏 Acknowledgments

- **SEC EDGAR API**: https://www.sec.gov/edgar/sec-api-documentation
- **sec-edgar-api**: Python wrapper for SEC API
- **Ollama**: Local LLM runtime
- **MongoDB**: Database storage
- **PySide6**: Qt framework for Python
- **Matplotlib**: Chart visualization

---

## ⚡ Quick Reference

### Common Commands

```bash
# Run application
python desktop_app_pyside.py

# Install model
ollama pull llama3.2

# Check MongoDB
mongosh
> use sec_profiles
> db.unified_profiles.countDocuments()

# Update dependencies
pip install -r requirements.txt --upgrade
```

### Keyboard Shortcuts

- **Ctrl+Q**: Quit application
- **F5**: Refresh profile list
- **Double-click chart**: Open interactive view

---

## 🔮 Future Enhancements

- [ ] Real-time price data integration
- [ ] Peer comparison analysis
- [ ] Sector analysis
- [ ] Automated alerts for material events
- [ ] Portfolio tracking
- [ ] PDF report generation
- [ ] Cloud deployment option

---

**Version**: 1.0.0  
**Last Updated**: December 2025  
**Status**: ✅ Production Ready

