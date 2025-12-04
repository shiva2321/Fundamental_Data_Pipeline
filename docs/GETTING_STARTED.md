# 🚀 Getting Started with Fundamental Data Pipeline

This guide will get you up and running in **under 10 minutes**.

---

## 📋 Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Python 3.8+** installed
- [ ] **MongoDB** installed (local or Atlas cloud)
- [ ] **Ollama** installed (for AI features - optional but recommended)
- [ ] **Git** (to clone repository)

---

## ⚡ Quick Installation

### Step 1: Install Prerequisites

#### Python
```bash
# Check Python version (must be 3.8+)
python --version

# If not installed, download from:
# https://www.python.org/downloads/
```

#### MongoDB
```bash
# Option A: Local Installation
# Download from: https://www.mongodb.com/try/download/community

# Option B: MongoDB Atlas (Cloud - Free tier available)
# Sign up at: https://www.mongodb.com/cloud/atlas
```

#### Ollama (for AI features)
```bash
# Download and install from:
# https://ollama.ai

# After installation, pull models:
ollama pull llama3.2
ollama pull mistral
ollama pull phi
```

---

### Step 2: Clone and Setup

```bash
# 1. Clone the repository
git clone <your-repository-url>
cd Fundamental_Data_Pipeline

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate

# Linux/Mac:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

### Step 3: Configure

Edit `config/config.yaml`:

```yaml
mongodb:
  # Local MongoDB
  uri: "mongodb://localhost:27017/"
  
  # OR MongoDB Atlas (cloud)
  # uri: "mongodb+srv://username:password@cluster.mongodb.net/"
  
  database: "sec_profiles"

profile_settings:
  lookback_years: 30          # How many years of historical data
  ai_enabled: true            # Enable AI analysis
  ai_model: "llama3.2"        # Which model to use
  email_notifications: false  # Email alerts (optional)

sec_edgar:
  # REQUIRED: SEC requires you identify yourself
  user_agent: "YourName your.email@example.com"
```

---

### Step 4: Start MongoDB

```bash
# Check if MongoDB is running
mongosh --version

# If not running, start it:

# Windows (as Service):
# Services → MongoDB Server → Start

# Windows (manual):
mongod

# Linux:
sudo systemctl start mongod

# Mac:
brew services start mongodb-community
```

---

### Step 5: Start Ollama (for AI)

```bash
# Start Ollama server
ollama serve

# In another terminal, verify models:
ollama list

# Should show:
# llama3.2
# mistral
# phi
```

---

### Step 6: Run the Application

```bash
# Windows
run.bat

# Linux/Mac
./run.sh

# Or directly
python desktop_app_pyside.py
```

The application window should open! 🎉

---

## 🎯 First Steps - Process Your First Company

### 1. Add a Company to Queue

1. Click the **"Dashboard_Generate"** tab
2. In the **"Add Tickers"** section:
   - Enter: `AAPL` (Apple Inc.)
3. Click **"Add to Queue"**

You should see "Added 1 ticker(s) to queue"

### 2. Start Processing

1. Click **"Start Processing"** button
2. Watch the **"Queue Monitor"** tab for progress
3. Wait ~30-60 seconds (includes AI analysis)

Progress indicators:
- **Status**: Processing → Completed
- **Progress**: 0% → 100%
- **Stage**: Fetching → Parsing → Analyzing → Waiting

### 3. View the Profile

1. Click **"Profile Manager"** tab
2. You should see **"AAPL - Apple Inc."** in the list
3. Select it (click on row)
4. Click **"Visualize Selected"**

A new window opens with the profile visualization!

### 4. Explore the Tabs

**Overview Tab:**
- Company information
- Latest financial metrics (Revenue: $X, Assets: $X, etc.)
- Material Events (8-K filings)
- Insider Trading activity
- Institutional Ownership
- Health Summary

**Decision Summary Tab:**
- Key decision metrics (ROE, ROA, Debt/Equity, Growth)
- Investment recommendation (Buy/Hold/Sell)
- Risk level

**Financial Trends Tab:**
- Interactive charts (Revenue, Assets, Liabilities, Net Income)
- **Hover** over points to see exact values
- **Double-click** chart to open interactive window
- Zoom and pan in interactive mode

**Growth Analysis Tab:**
- Period-over-period growth rates
- Hover to see exact % changes
- Interactive growth charts

**AI/ML Analysis Tab:**
- Investment thesis
- Strengths and weaknesses
- Growth predictions (1yr, 3yr, 5yr)
- Risks and catalysts
- Insider trading signals
- Institutional ownership signals
- Governance assessment

### 5. Try Interactive Charts

1. Go to **Financial Trends** tab
2. **Double-click** on any chart
3. Interactive window opens with:
   - **Hover**: See exact values
   - **Zoom**: Scroll mouse wheel
   - **Pan**: Click and drag
   - **Reset**: Click home icon
   - **Save**: Click save icon

---

## 🔧 Common First-Time Issues

### Issue 1: MongoDB Connection Failed

**Error**: `Failed to connect to MongoDB`

**Solution**:
```bash
# Check MongoDB is running
mongosh

# If fails, start MongoDB:
# Windows: Services → MongoDB Server → Start
# Linux: sudo systemctl start mongod
# Mac: brew services start mongodb-community
```

---

### Issue 2: Ollama Not Available

**Error**: `Ollama is not running on localhost:11434`

**Solution**:
```bash
# Start Ollama service
ollama serve

# Check it's running
ollama list

# Pull models if missing
ollama pull llama3.2
```

**Note**: AI analysis will use rule-based fallback if Ollama is unavailable.

---

### Issue 3: No Revenue Data for Company

**Message**: `Revenues: N/A`

**Why**: Not all companies report revenue in standard XBRL format

**Solution**: 
- Try a well-known company (AAPL, MSFT, GOOGL, AMZN)
- Smaller/foreign companies may have limited data
- Check MongoDB for raw financial data

---

### Issue 4: SEC API Rate Limit

**Error**: `429 Too Many Requests`

**Solution**:
- Built-in rate limiting (10 req/sec) should prevent this
- If processing many companies, expect delays
- SEC fair access policy requires rate limiting

---

### Issue 5: Charts Not Displaying

**Issue**: Empty chart areas

**Solution**:
```bash
# Reinstall matplotlib
pip uninstall matplotlib
pip install matplotlib

# Reinstall PySide6
pip uninstall PySide6
pip install PySide6
```

---

## 📊 Processing Multiple Companies

### Method 1: Bulk Add

```
Dashboard_Generate Tab:
1. Enter: AAPL, MSFT, GOOGL, AMZN, TSLA
2. Click "Add to Queue"
3. Click "Start Processing"
```

All companies will be processed sequentially.

### Method 2: CSV Import (Future Feature)

Currently manual entry only.

---

## 🎓 Understanding the Data

### Financial Metrics

**Revenue**: Total income from sales  
**Assets**: What the company owns  
**Liabilities**: What the company owes  
**Equity**: Assets - Liabilities  
**Net Income**: Profit after all expenses  

### Health Score (0-100)

- **90-100**: Excellent
- **70-89**: Good
- **50-69**: Fair
- **30-49**: Poor
- **0-29**: Critical

Components:
- Profitability (ROE, ROA, margins)
- Leverage (debt ratios)
- Growth (revenue, income growth)

### Insider Trading Signals

- **Strong Bullish**: Net buying > $1M
- **Bullish**: Net buying $100K-$1M
- **Neutral**: Net < $100K
- **Bearish**: Net selling $100K-$1M
- **Strong Bearish**: Net selling > $1M

### AI Recommendations

- **Strong Buy**: High confidence positive
- **Buy**: Positive outlook
- **Hold**: Wait and see
- **Sell**: Negative outlook
- **Strong Sell**: High confidence negative

---

## 🚀 Advanced Features

### Multi-Model AI Analysis

Compare recommendations across different models:

```yaml
# In config/config.yaml:
profile_settings:
  multi_model_enabled: true
  selected_models:
    - "llama3.2"
    - "mistral"
    - "phi"
    - "llama2"
```

AI/ML Analysis tab will show:
- Consensus recommendation
- Individual model recommendations
- Confidence levels
- Comparison table

### Profile Period Editing

Edit the date range for a profile:

```
Profile Manager Tab:
1. Select profile
2. Click "Edit Period"
3. Set new date range
4. Click "Update and Regenerate"
```

### Batch Operations

```
Profile Manager Tab:
1. Select multiple profiles (Ctrl+Click)
2. Click "Delete Selected" (bulk delete)
3. Click "Refresh List" to reload
```

---

## 📖 Next Steps

### Learn More

- **Architecture**: `docs/ARCHITECTURE.md` - Technical deep dive
- **AI Setup**: `docs/AI_SETUP_GUIDE.md` - Advanced Ollama configuration
- **Implementation**: `docs/IMPLEMENTATION_DETAILS.md` - How everything works

### Try Different Companies

**Large Cap Tech:**
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Alphabet)
- AMZN (Amazon)
- META (Meta/Facebook)

**Finance:**
- JPM (JPMorgan Chase)
- BAC (Bank of America)
- GS (Goldman Sachs)

**Healthcare:**
- JNJ (Johnson & Johnson)
- PFE (Pfizer)
- UNH (UnitedHealth)

**Consumer:**
- WMT (Walmart)
- KO (Coca-Cola)
- PG (Procter & Gamble)

### Explore Features

- ✅ Try interactive charts (double-click)
- ✅ Compare AI model recommendations
- ✅ Check insider trading patterns
- ✅ Review material events (8-K filings)
- ✅ Analyze corporate governance scores

---

## 💡 Pro Tips

### Tip 1: Start with Well-Known Companies

Large companies have:
- Complete XBRL data
- Extensive filing history
- Better AI analysis (more data)

### Tip 2: Let AI Warm Up

First AI analysis may take 30-60 seconds as models load.  
Subsequent analyses are faster.

### Tip 3: Use Interactive Charts

Double-click charts for:
- Zoom into specific periods
- See exact values on hover
- Pan across full history
- Export as images

### Tip 4: Check Detailed Analysis

AI/ML tab shows:
- Specific insider transaction amounts
- Exact ownership percentages
- CEO compensation figures
- Board independence metrics

### Tip 5: Monitor Queue

Queue Monitor tab shows real-time progress:
- Current stage
- Progress percentage
- Estimated time remaining

---

## 🆘 Getting Help

### Documentation

- **README.md**: Overview and quick reference
- **GETTING_STARTED.md**: This file
- **docs/ARCHITECTURE.md**: Technical architecture
- **docs/AI_SETUP_GUIDE.md**: AI configuration
- **docs/IMPLEMENTATION_DETAILS.md**: How it works

### Troubleshooting

1. Check logs in application console
2. Verify MongoDB is running (`mongosh`)
3. Verify Ollama is running (`ollama list`)
4. Check configuration (`config/config.yaml`)
5. Ensure SEC user agent is set

### Common Questions

**Q: How long does processing take?**  
A: 30-60 seconds per company (with AI), 10-15 seconds (without AI)

**Q: How much data is stored?**  
A: ~500KB-2MB per company profile

**Q: Can I use without AI?**  
A: Yes, set `ai_enabled: false` in config. You'll get financial analysis without AI insights.

**Q: Does it work offline?**  
A: No, requires internet for SEC EDGAR API access.

**Q: Is MongoDB required?**  
A: Yes, for storing profiles. Use MongoDB Atlas free tier if you don't want local installation.

---

## 🎉 You're Ready!

You now have:
- ✅ Application installed and running
- ✅ First profile generated
- ✅ Understanding of basic features
- ✅ Knowledge of how to explore data

**Next**: Process more companies and explore the AI insights!

---

**Happy Analyzing!** 📊🚀

