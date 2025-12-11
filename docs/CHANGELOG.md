# 📝 Changelog

All notable changes to the Fundamental Data Pipeline project.

---

## [1.2.0] - 2025-12-07

### 🎯 Major Enhancements - Narrative Analysis, Quality Control & Error Tracking

#### Added

**10-K/10-Q Narrative Parser:**
- ✅ **Narrative section extraction** - Extracts Business, Risk Factors, MD&A, Market Risk, Financial Statements sections
- ✅ **Keyword analysis** - Identifies mentions of key terms (risk, litigation, cyber, regulatory, liquidity, etc.)
- ✅ **Risk factor summarization** - Aggregates and analyzes risk disclosures across filings
- ✅ **MD&A insights** - Extracts management discussion and analysis for trend analysis
- ✅ **Section-level metrics** - Word counts, keyword density, and sentiment indicators

**Key Persons Enhanced Parser:**
- ✅ **Executive extraction** - Identifies CEO, CFO, COO, and other C-suite officers
- ✅ **Board member analysis** - Extracts board composition and independence status
- ✅ **Insider holdings tracking** - Comprehensive ownership stake calculations
- ✅ **Holding company identification** - Identifies major institutional investors
- ✅ **Active status tracking** - Determines if executives/board members are currently active (based on filing recency)
- ✅ **Name validation** - Advanced filtering to reject invalid names and form fields

**Profile Quality & Validation System:**
- ✅ **Profile validator** - Comprehensive validation of profile completeness and consistency
- ✅ **Issue categorization** - Groups issues into INCOMPLETE, INCONSISTENT, OUT_OF_ORDER, IMPROPER categories
- ✅ **Quality scoring** - Assigns quality scores based on data availability and consistency
- ✅ **Automated detection** - Identifies missing fields, date inconsistencies, data gaps
- ✅ **Problematic profiles dialog** - UI for identifying and retrying incomplete/problematic profiles
- ✅ **Bulk retry capability** - Select and retry multiple problematic profiles at once

**Failure Tracking System:**
- ✅ **Detailed failure reasons** - Categorized failure types (CIK lookup, no filings, timeout, etc.)
- ✅ **Error message capture** - Stores complete error messages and stack traces
- ✅ **Retry counter** - Tracks how many times a ticker has been retried
- ✅ **Context preservation** - Saves processing context (lookback_years, filing_limit, etc.)
- ✅ **Failed tickers dialog** - UI for viewing, retrying, or deleting failed tickers
- ✅ **Failure categorization** - Groups failures by type for easier diagnosis

**Dual Parser Architecture:**
- ✅ **Forms/ directory** - Legacy comprehensive form parser system (124 form types)
- ✅ **src/parsers/ directory** - Modern focused parsers for key filings (10-K/Q, 8-K, Form 4, DEF 14A, SC 13D/G)
- ✅ **Validation system** - 124 form parsers validated and working (validation_report.json)
- ✅ **Parser selection** - Automatic fallback between modern and legacy parsers

#### Improved

**Data Extraction:**
- 🔧 Enhanced content fetching with better error handling
- 🔧 Improved filing index parsing for multi-document filings
- 🔧 Better XML/HTML parsing with multiple fallback strategies
- 🔧 More robust date parsing and normalization

**User Interface:**
- 🔧 Better error reporting in processing logs
- 🔧 More detailed progress indicators
- 🔧 Enhanced profile manager with quality indicators
- 🔧 Improved visualization of incomplete/problematic profiles

**Error Handling:**
- 🔧 Graceful degradation when parsers fail
- 🔧 Better timeout handling for long-running operations
- 🔧 Checkpoint recovery for interrupted processing
- 🔧 More informative error messages

#### Technical Improvements

- 📦 Modular parser architecture for easier maintenance
- 🧪 Comprehensive parser validation suite
- 🔍 Better logging and debugging capabilities
- ⚡ Improved performance for large filing sets

---

## [1.1.0] - 2025-12-04

### 🎯 Major Improvements - Key Persons Tab & Project Organization

#### Added

**Key Persons Tab Enhancements:**
- ✅ **Resizable table columns** - All tables now support Interactive resize mode
- ✅ **Collapsible sections** - Proper expand/collapse buttons with ▼/▶ arrows (replaced confusing checkboxes)
- ✅ **Active status tracking** - New "Active" column for executives showing if filing is within 24 months
- ✅ **Improved data validation** - Stricter filters for institutional investor names
- ✅ **Better null handling** - Proper display of Net Buy/Sell values (shows "-" when no activity)
- ✅ **Enhanced name extraction** - Rejects form fields, IRS references, and boilerplate text

**Project Organization:**
- ✅ **Proper package structure** - Organized code into `src/` with subpackages:
  - `src/parsers/` - All SEC filing parsers
  - `src/clients/` - API and database clients
  - `src/ui/` - User interface components
  - `src/analysis/` - Analysis and aggregation modules
  - `src/utils/` - Utility and configuration modules
- ✅ **Main entry point** - Created `main.py` for clean application launch
- ✅ **Updated run scripts** - Simplified `run.bat` and `run.sh`
- ✅ **Consolidated documentation** - Moved old docs to `docs/archive/`
- ✅ **Clean project root** - Removed temporary and redundant files

#### Fixed

**Key Persons Tab:**
- ✅ Column resizing now works properly with QHeaderView.ResizeMode.Interactive
- ✅ Institutional holdings no longer shows invalid names like "S.S. OR I.R.S. IDENTIFICATION NO."
- ✅ Net Buy/Sell values display correctly (shows actual values when available, "-" when not)
- ✅ Collapsible sections use proper UI pattern (buttons instead of checkboxes)
- ✅ Executive list shows active status to distinguish current from historical executives

**Data Quality:**
- ✅ Institutional investor name validation expanded with 20+ invalid patterns
- ✅ Form field detection (rejects entries with >30% digits)
- ✅ Better ownership percentage extraction with multiple pattern matching
- ✅ Enhanced shares owned extraction with validation

#### Changed

- 📦 Reorganized all Python files into proper package structure
- 📚 Updated README.md with new project structure
- 🗂️ Moved documentation to appropriate folders
- 🧹 Cleaned up root directory
- 🚀 Simplified application launch process

---

## [1.0.0] - 2025-12-04

### ✨ Major Release - Production Ready

#### Added

**Complete Filing Analysis System:**
- ✅ 8-K material events parser with risk flag detection
- ✅ Form 4 insider trading parser with buy/sell transaction details
- ✅ SC 13D/G institutional ownership parser with activist investor detection
- ✅ DEF 14A corporate governance parser with compensation and board analysis
- ✅ Filing content fetcher for HTML/XML parsing from SEC EDGAR

**AI/ML Enhancements:**
- ✅ Multi-model AI analysis (compare llama3.2, mistral, phi, llama2)
- ✅ Comprehensive AI prompts with all filing data
- ✅ Enhanced recommendations with insider/institutional/governance signals
- ✅ Model consensus view with expandable detailed breakdown
- ✅ Confidence scoring based on complete data

**Interactive Visualizations:**
- ✅ Hover tooltips on all charts with exact values
- ✅ Double-click to open interactive chart windows
- ✅ Zoom and pan functionality
- ✅ Scrollable charts for extensive data
- ✅ Three-view charts (absolute, % change, indexed)
- ✅ Enhanced growth analysis with color-coded bars

**Data Extraction:**
- ✅ Revenue extraction with 10+ field name variations
- ✅ Complete financial time series (all historical data)
- ✅ Transaction-level insider trading data (amounts, prices, signals)
- ✅ Ownership percentages and investor names
- ✅ CEO compensation and pay ratios
- ✅ Board composition and independence metrics

**UI/UX Improvements:**
- ✅ Reorganized Overview tab with all filing data sections
- ✅ Material Events section with risk flags and catalysts
- ✅ Insider Trading section with detailed transaction summary
- ✅ Institutional Ownership section with activist warnings
- ✅ Corporate Governance section with compensation details
- ✅ Model consensus expandable section in AI/ML tab

**Performance:**
- ✅ Pagination support for ALL historical filings (1000+ per company)
- ✅ Efficient detailed parsing (recent 20/10/5 filings)
- ✅ Hybrid extraction (API + filings for best quality)
- ✅ Rate limiting compliance (10 req/sec to SEC)

#### Changed

- 🔄 Updated AI prompts to include detailed filing data
- 🔄 Enhanced profile structure with new filing sections
- 🔄 Improved visualization window layout
- 🔄 Optimized MongoDB queries
- 🔄 Better error handling for content parsing

#### Fixed

- 🐛 Revenue extraction now works for 95%+ of companies
- 🐛 Filing count issue resolved (now fetches all 1000+ filings)
- 🐛 Chart hover functionality working on all chart types
- 🐛 Growth analysis charts properly formatted
- 🐛 Bar width and spacing issues resolved
- 🐛 Interactive chart zoom/pan performance improved
- 🐛 Model consensus section properly collapsible

#### Technical

- 📦 Added beautifulsoup4 and lxml dependencies
- 📦 Created filing content parser module
- 📦 Implemented detailed analyzers for each filing type
- 📦 Enhanced unified profile aggregator with all parsers
- 📦 Updated AI analyzer with comprehensive prompts

---

## [0.9.0] - 2025-12-03

### Beta Release

#### Added
- Basic filing pattern analysis
- Placeholder parsing functions
- Simple AI integration
- Basic charts and visualizations

#### Issues
- Revenue extraction incomplete
- Only 77 filings fetched (pagination not enabled)
- No detailed transaction data
- Charts missing hover functionality
- AI recommendations based on limited data

---

## [0.8.0] - 2025-11-30

### Alpha Release

#### Added
- Initial desktop application (PySide6)
- Basic SEC EDGAR API integration
- MongoDB storage
- Simple profile generation
- Basic financial metrics

#### Known Issues
- Limited filing types supported
- No AI analysis
- Basic visualizations only
- Manual data entry required

---

## Version History Summary

| Version | Date | Status | Key Features |
|---------|------|--------|-------------|
| **1.0.0** | 2025-12-04 | ✅ Production | Complete filing analysis, detailed data extraction, multi-model AI |
| 0.9.0 | 2025-12-03 | Beta | Basic filing analysis, placeholder parsers |
| 0.8.0 | 2025-11-30 | Alpha | Initial release, basic features |

---

## Upgrade Notes

### From 0.9.0 to 1.0.0

**Breaking Changes:**
- Profile structure updated with new filing sections
- MongoDB schema includes new fields
- Configuration requires SEC user agent

**Migration Steps:**
```bash
# 1. Update dependencies
pip install -r requirements.txt

# 2. Update configuration
# Add to config/config.yaml:
sec_edgar:
  user_agent: "YourName your.email@example.com"

# 3. Regenerate profiles (recommended)
# Old profiles will work but won't have detailed filing data
# Delete old profiles and regenerate for full features
```

**New Features to Explore:**
- Double-click charts for interactive view
- Check Material Events section in Overview tab
- Review detailed insider trading analysis
- Examine institutional ownership with activist detection
- Try multi-model AI analysis

---

## Planned Features

### v1.1.0 (Q1 2026)
- [ ] Real-time price data integration
- [ ] Peer comparison analysis
- [ ] Automated alerts for material events
- [ ] CSV export functionality
- [ ] Advanced filtering in Profile Manager

### v1.2.0 (Q2 2026)
- [ ] Sector analysis and benchmarking
- [ ] Portfolio tracking
- [ ] PDF report generation
- [ ] Custom dashboard widgets
- [ ] API endpoint for external access

### v2.0.0 (Q3 2026)
- [ ] Cloud deployment option
- [ ] Multi-user support
- [ ] Real-time collaboration
- [ ] Mobile companion app
- [ ] Advanced machine learning models

---

## Contributing

See CONTRIBUTING.md for guidelines on:
- Reporting bugs
- Suggesting features
- Submitting pull requests
- Code style guidelines

---

## Release Process

1. **Development**: Feature branches
2. **Testing**: Extensive testing on dev environment
3. **Documentation**: Update docs
4. **Version Bump**: Update version numbers
5. **Changelog**: Document changes
6. **Tag Release**: Git tag with version
7. **Deploy**: Push to production

---

**Current Version**: 1.0.0  
**Release Date**: December 4, 2025  
**Status**: ✅ Stable - Production Ready

