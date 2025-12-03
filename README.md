# Fundamental Data Pipeline

A comprehensive desktop application for fetching, processing, and analyzing SEC company fundamental data with a native PyQt5 interface.

## 🌟 Features

- **Modern Desktop Interface**: Native PyQt5 desktop application with intuitive multi-tab user interface
- **Unified Profile System**: Combines financial data and ML features into a single, well-organized profile
- **SEC Company Database**: Fetches company information from SEC's official ticker JSON file
- **Smart Company Search**: Search by ticker symbol, company name, or CIK with instant results
- **Interactive Desktop Application**: Six main tabs for comprehensive data management
- **Batch Processing**: Generate profiles for multiple companies at once with progress tracking
- **Advanced Analytics**: Health scores, trend analysis, growth rates, volatility metrics, and company comparison
- **MongoDB Storage**: Efficient storage in organized database structure
- **Non-blocking Operations**: Multi-threaded profile generation without freezing the UI

## 📊 Database Structure

- **Database Name**: `Entities`
- **Collection**: `Fundamental_Data_Pipeline`
- **Profile Structure**: Single unified document per company containing:
  - Company information (ticker, name, CIK)
  - Filing metadata
  - Financial time series data
  - Latest financial metrics
  - Financial ratios
  - Growth rates
  - Statistical summaries
  - Trend features
  - Health indicators
  - Volatility metrics
  - Lifecycle features
  - Anomaly detection
  - ML-ready feature vectors

## 🚀 Quick Start

### Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure MongoDB is running**:
   ```bash
   # Default: mongodb://localhost:27017
   ```

3. **Configure settings** (optional):
   Edit `config/config.yaml` to customize database settings

### Running the Application

#### Windows
```bash
run.bat
```

#### Linux/macOS
```bash
bash run.sh
```

#### Direct Python
```bash
python app.py
```

The desktop application will launch with a native PyQt5 interface.

## 📖 Desktop Application Guide

For detailed information about using the desktop application, see [DESKTOP_APP_GUIDE.md](DESKTOP_APP_GUIDE.md)

### Main Interface

The desktop application provides six main tabs:

1. **🏠 Home** - Dashboard with system statistics and quick actions
2. **🔍 Search** - Search companies by ticker, name, or CIK
3. **📈 Generate Profiles** - Single and batch profile generation with progress tracking
4. **📊 View Profiles** - Browse, view details, and manage generated profiles
5. **📉 Analytics** - Portfolio statistics and company comparison
6. **⚙️ Settings** - Database configuration and backup/restore operations
   - Health score distribution
   - Company comparison (up to 5 companies)
   - Interactive charts and visualizations

6. **⚙️ Settings**
   - Database configuration
   - Refresh company ticker cache
   - View all collections
   - Clear cache files

### Command Line Interface

The CLI provides:
1. Search for companies
2. Generate single company profile
3. View existing profiles
4. Batch generate profiles
5. Database statistics
6. Launch web dashboard
7. Exit

## 🏗️ Architecture

### Core Components

1. **company_ticker_fetcher.py**
   - Fetches and caches SEC company ticker data
   - Provides search and lookup functionality
   - Auto-refreshes cache after 7 days

2. **unified_profile_aggregator.py**
   - Combines financial data and ML features
   - Generates comprehensive company profiles
   - Calculates derived metrics and ratios

3. **sec_edgar_api_client.py**
   - Interfaces with SEC EDGAR API
   - Fetches company filings and facts
   - Rate limiting and error handling

4. **mongo_client.py**
   - MongoDB wrapper with helper methods
   - Connection management
   - Bulk operations support

5. **dashboard.py**
   - Streamlit web application
   - Interactive visualizations
   - Real-time data updates

6. **main_unified.py**
   - Command-line interface
   - Batch processing support
   - System statistics

## 📊 Profile Sections Explained

### Company Information
- Ticker symbol
- Company name
- CIK (10-digit format)

### Filing Metadata
- Total filings count
- Form type distribution
- Filings per year
- Date range of available data

### Financial Data
Latest values for:
- Revenue
- Assets
- Liabilities
- Stockholders' Equity
- Net Income
- Cash and equivalents
- Operating Income
- Gross Profit
- EPS (Basic and Diluted)
- Shares Outstanding

### Financial Ratios
- Debt to Assets
- Debt to Equity
- Current Ratio
- Profit Margin
- Asset Turnover
- Return on Equity (ROE)
- Return on Assets (ROA)
- Cash Ratio

### Growth Rates
- Period-over-period growth
- Average growth rate
- Latest growth rate
- Median growth rate

### Health Indicators
- Overall health score (0-100)
- Profitability score
- Leverage score
- Growth score
- Health classification (Excellent/Good/Fair/Poor)

### Lifecycle Features
- Years of available data
- Filing frequency
- Growth stage classification
- Maturity level

### Volatility Metrics
- Standard deviation
- Variance
- Maximum swing
- Volatility classification

### ML Features
Flat feature vector ready for machine learning models with normalized metrics.

## 🔧 Configuration

Edit `config/config.yaml`:

```yaml
mongodb:
  db_name: Entities
  uri: mongodb://localhost:27017
  collection: Fundamental_Data_Pipeline
```

## 📝 Example: Generate a Profile

### Via Dashboard
1. Go to "Company Search"
2. Enter ticker (e.g., "AAPL")
3. Click "Generate Profile for this Company"
4. Navigate to "Generate Profiles" page
5. Click "Generate Unified Profile"

### Via CLI
```python
from company_ticker_fetcher import CompanyTickerFetcher
from unified_profile_aggregator import UnifiedSECProfileAggregator
from mongo_client import MongoWrapper
from sec_edgar_api_client import SECEdgarClient

# Initialize
mongo = MongoWrapper(uri="mongodb://localhost:27017", database="Entities")
sec_client = SECEdgarClient()
aggregator = UnifiedSECProfileAggregator(mongo, sec_client)
ticker_fetcher = CompanyTickerFetcher()

# Find company
company = ticker_fetcher.get_by_ticker("AAPL")

# Generate profile
profile = aggregator.aggregate_company_profile(
    cik=company['cik'],
    company_info=company,
    output_collection="Fundamental_Data_Pipeline"
)
```

## 🔍 Searching Companies

The system fetches the official SEC company tickers JSON file which contains all publicly traded companies in the US.

### Search Methods

1. **By Ticker**: Exact match (case-insensitive)
   ```python
   company = ticker_fetcher.get_by_ticker("MSFT")
   ```

2. **By Company Name**: Partial match
   ```python
   results = ticker_fetcher.search_by_name("Apple", limit=10)
   ```

3. **By CIK**: With or without leading zeros
   ```python
   company = ticker_fetcher.get_by_cik("0000320193")
   ```

## 🎯 Use Cases

1. **Investment Research**: Analyze company financials and health
2. **Portfolio Management**: Track multiple companies
3. **Risk Assessment**: Evaluate volatility and financial health
4. **Trend Analysis**: Identify growth patterns
5. **Machine Learning**: Use feature vectors for predictive models
6. **Comparative Analysis**: Compare companies side-by-side

## 📈 Performance

- **Profile Generation**: ~5-15 seconds per company (depends on SEC API)
- **Batch Processing**: Includes automatic rate limiting
- **Database Queries**: Optimized indexes for fast retrieval
- **Caching**: Company ticker data cached locally for 7 days

## 🛠️ Troubleshooting

### MongoDB Connection Issues
- Ensure MongoDB is running: `mongod`
- Check connection URI in `config/config.yaml`
- Verify database permissions

### SEC API Errors
- SEC API has rate limits (10 requests/second)
- The system includes automatic rate limiting
- Some companies may have no filings available

### Dashboard Not Loading
- Install requirements: `pip install -r requirements.txt`
- Run the desktop app: `python app.py`
- The app will prefer a PyQt5 desktop GUI when available, and will automatically fall back to a Tkinter UI if PyQt5 is not usable on your platform.

### No Companies Found
- Refresh ticker cache from Settings page
- Check internet connection
- Verify SEC website is accessible

## 📦 Dependencies

- `pymongo`: MongoDB driver
- `requests`: HTTP requests
- `numpy`: Numerical computing
- `pyyaml`: YAML configuration
- `sec-edgar-api`: SEC EDGAR API client
- `pandas`: Data manipulation
- `plotly`: Interactive charts (optional)

## 🔐 Data Privacy

- All data is fetched from public SEC filings
- No personal information is stored
- Local MongoDB storage only
- No external data sharing

## 📄 License

This project is for educational and research purposes.

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional financial metrics
- More visualization types
- Enhanced ML features
- Export functionality
- Advanced filtering

## 📞 Support

For issues or questions:
1. Check this README
2. Review error logs
3. Verify MongoDB connection
4. Check SEC API status

## 🔄 Updates

### Version 2.0 (Current)
- ✅ Unified profile system (combines financial + ML features)
- ✅ SEC company ticker integration
- ✅ Streamlit dashboard
- ✅ Batch processing
- ✅ Advanced analytics
- ✅ Health scoring system

### Future Enhancements
- [ ] Export to Excel/CSV
- [ ] PDF report generation
- [ ] Email alerts
- [ ] Historical comparisons
- [ ] Industry benchmarking
- [ ] Real-time updates
- [ ] API endpoint creation

---

**Happy analyzing! 📊**
