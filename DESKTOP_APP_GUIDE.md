# Fundamental Data Pipeline - Desktop Application

A comprehensive desktop application for fetching, processing, and analyzing SEC company fundamental data.

## 🌟 Features

- **Modern PyQt5 Desktop Interface**: Native desktop application with intuitive UI
- **Unified Profile System**: Combines financial data and ML features into a single profile
- **SEC Company Database**: Fetches company information from SEC's official ticker JSON file
- **Smart Company Search**: Search by ticker symbol, company name, or CIK
- **Batch Processing**: Generate profiles for multiple companies at once
- **Advanced Analytics**: Health scores, trend analysis, growth rates, and volatility metrics
- **MongoDB Storage**: Efficient storage in organized database structure
- **Profile Management**: View, compare, and delete company profiles
- **Multi-threaded Operations**: Non-blocking profile generation with progress tracking

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

```bash
python app.py
```

The desktop application will launch with a modern, native interface.

## 📖 User Guide

### Main Window

The application features six main tabs:

#### 1. **🏠 Home** - Dashboard Overview
   - View system statistics
   - See database status
   - Quick access to main functions
   - System configuration information

#### 2. **🔍 Search** - Company Search
   - Search by ticker symbol (e.g., AAPL, MSFT)
   - Search by company name (partial matching)
   - Search by CIK number
   - Quick profile generation from search results
   - Table view of search results with action buttons

#### 3. **📈 Generate Profiles** - Profile Generation
   - Single profile generation for individual companies
   - Batch profile generation for multiple companies
   - Real-time progress tracking with progress bar
   - Error handling and status messages
   - Option to overwrite existing profiles

#### 4. **📊 View Profiles** - Profile Management
   - Browse all generated profiles in the database
   - Filter profiles by ticker symbol
   - View detailed profile information with multiple tabs:
     - Overview: Company info and filing metadata
     - Financials: Latest metrics and time series
     - Ratios: Financial ratios and indicators
     - Health: Financial health indicators
     - Raw JSON: Complete profile data
   - Delete profiles from the database
   - Automatic profile refresh

#### 5. **📉 Analytics** - Portfolio Analysis
   - View portfolio overview statistics
   - Calculate average health scores
   - Count total generated profiles
   - Compare multiple companies (up to 5)
   - Side-by-side company metrics:
     - Health scores
     - Revenue
     - Growth rates

#### 6. **⚙️ Settings** - Configuration
   - Configure MongoDB connection
   - Set database and collection names
   - Backup database to JSON
   - Clear application cache
   - Save and persist settings

### Menu Bar

- **File**
  - Exit: Close the application

- **Tools**
  - Refresh Database: Update all displayed information

- **Help**
  - About: View application information

### Status Bar

Located at the bottom, shows real-time status messages and progress information.

## 🎯 Workflow Examples

### Example 1: Generate Profile for Apple Inc.

1. Go to **Search** tab
2. Select "Ticker Symbol" from dropdown
3. Enter "AAPL"
4. Click **Search**
5. Click **Generate Profile** button
6. Monitor progress in **Generate Profiles** tab
7. View generated profile in **View Profiles** tab

### Example 2: Batch Generate Multiple Companies

1. Go to **Generate Profiles** tab
2. In "Batch Profile Generation" section, enter: `AAPL, MSFT, GOOGL, AMZN`
3. Click **Generate Batch**
4. Monitor progress with the progress bar
5. Profiles will be stored in MongoDB

### Example 3: Compare Companies

1. Go to **Analytics** tab
2. Enter first ticker (e.g., "AAPL") in the comparison input
3. Click **Add to Comparison**
4. Repeat steps 2-3 for up to 5 companies
5. View comparative metrics in the table

### Example 4: Backup Database

1. Go to **Settings** tab
2. Click **Backup Database**
3. Choose save location and filename
4. Database will be exported as JSON file

## 🔧 Configuration

### MongoDB Connection

The application uses MongoDB for data storage. Default connection:
- **URI**: `mongodb://localhost:27017`
- **Database**: `Entities`
- **Collection**: `Fundamental_Data_Pipeline`

Modify these settings in the **Settings** tab or in `config/config.yaml`.

### Environment Variables

You can set these environment variables to override defaults:

```bash
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=Entities

# Application
MAX_THREADS=5
```

## 📝 Data Processing

### Profile Generation Process

When generating a profile, the application:

1. **Validates Input**: Checks if company exists in SEC database
2. **Fetches SEC Data**: Retrieves filings from SEC EDGAR API
3. **Extracts Financials**: Parses financial statements
4. **Calculates Metrics**: Computes ratios, growth rates, and indicators
5. **Generates Features**: Creates ML-ready features
6. **Analyzes Health**: Evaluates financial health
7. **Stores Profile**: Saves to MongoDB

### Threading Model

- **Main Thread**: Handles UI rendering and user interactions
- **Worker Thread**: Handles profile generation (non-blocking)
- **Progress Signals**: Real-time updates from worker to UI

## 🐛 Troubleshooting

### MongoDB Connection Error

**Problem**: "MongoDB: Disconnected" in status

**Solutions**:
1. Ensure MongoDB is running: `mongod`
2. Check connection URI in Settings
3. Verify MongoDB is accessible at configured address

### No Companies Found in Search

**Problem**: Search returns no results

**Solutions**:
1. Ensure ticker cache is loaded
2. Click "Clear Cache" in Settings to refresh company list
3. Try alternative search method (name or CIK)

### Profile Generation Fails

**Problem**: Generation stops with error

**Solutions**:
1. Check MongoDB connection
2. Verify SEC API is accessible
3. Try generating single profile instead of batch
4. Check application logs for detailed error message

### Slow Performance

**Problem**: Application is slow or unresponsive

**Solutions**:
1. Reduce batch size for profile generation
2. Close other applications
3. Clear cache in Settings
4. Check MongoDB performance

## 📚 Technical Details

### Architecture

The application follows a modular architecture:

- **desktop_app.py**: Main PyQt5 application and UI
- **mongo_client.py**: MongoDB wrapper and operations
- **unified_profile_aggregator.py**: Profile generation and aggregation
- **sec_edgar_api_client.py**: SEC API communication
- **company_ticker_fetcher.py**: Company search and lookup
- **config.py**: Configuration management

### Threading

- Profile generation runs in separate worker threads
- UI remains responsive during long-running operations
- Progress signals update UI in real-time
- Multiple operations can be queued

### Error Handling

- Comprehensive exception handling
- User-friendly error messages via dialogs
- Detailed logging for debugging
- Graceful degradation on errors

## 🔄 Future Enhancements

Potential features for future versions:

- [ ] Export profiles to Excel/PDF
- [ ] Advanced charting and visualization
- [ ] Real-time data refresh
- [ ] Custom report generation
- [ ] Data validation and quality checks
- [ ] API integration with other financial data sources
- [ ] Machine learning model integration
- [ ] Portfolio optimization tools
- [ ] Scheduled automatic updates

## 📄 License

© 2025 Fundamental Data Pipeline

## 🤝 Contributing

For bug reports and feature requests, please refer to the project documentation.

## ℹ️ About

This application is part of the Fundamental Data Pipeline project, a comprehensive system for analyzing SEC company fundamental data using Python, MongoDB, and advanced financial analytics.

