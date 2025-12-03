# Getting Started with Fundamental Data Pipeline Desktop Application

## 5-Minute Setup

### Prerequisites
- Python 3.8 or higher
- MongoDB (running locally or accessible remotely)
- ~200MB disk space

### Step 1: Install Dependencies

**Windows:**
```bash
run.bat
```

**Linux/macOS:**
```bash
bash run.sh
```

**Manual:**
```bash
pip install -r requirements.txt
```

### Step 2: Start MongoDB

**Windows:**
```bash
mongod
```

**Docker (Any OS):**
```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### Step 3: Launch Application

**Windows:**
```bash
run.bat
```

**Linux/macOS:**
```bash
python app.py
```

The application should launch within seconds.

## First Time Setup

### 1. Verify MongoDB Connection

When you launch the app, check the status bar for MongoDB status. Should show "Ready".

If it shows disconnected:
- Ensure MongoDB is running
- Go to Settings tab
- Verify MongoDB URI: `mongodb://localhost:27017`
- Click Save Settings

### 2. Add Your First Company

1. Go to **Search** tab
2. Select "Ticker Symbol"
3. Enter a ticker (e.g., `AAPL` for Apple)
4. Click **Search**
5. In the results, click **Generate Profile**

The app will:
- Fetch company data from SEC
- Generate financial profile
- Save to MongoDB
- Show completion message

### 3. View the Profile

1. Go to **View Profiles** tab
2. Find your company in the list
3. Double-click to view details
4. Browse different sections:
   - **Overview**: Company basics
   - **Financials**: Numbers and metrics
   - **Ratios**: Financial ratios
   - **Health**: Health score
   - **Raw JSON**: Complete data

## Common Workflows

### Workflow 1: Research a Single Company

**Time: 1-2 minutes**

1. **Search** → Enter ticker → Generate Profile
2. **View Profiles** → Find company → Double-click
3. Review financial data in detail tabs
4. Note health score and key metrics

### Workflow 2: Compare Multiple Companies

**Time: 3-5 minutes**

1. Generate profiles for companies you want to compare (Search → Generate)
2. Go to **Analytics** tab
3. Add each company to comparison table
4. Compare health scores, revenue, growth rates

### Workflow 3: Batch Add Companies

**Time: Varies by company count**

1. Go to **Generate Profiles** tab
2. In "Batch Profile Generation", enter: `AAPL, MSFT, GOOGL, TSLA, AMZN`
3. Click **Generate Batch**
4. Monitor progress bar
5. Once complete, go to **View Profiles** to see all

### Workflow 4: Backup Your Data

**Time: 1 minute**

1. Go to **Settings** tab
2. Click **Backup Database**
3. Choose save location
4. JSON file created with all profile data

To restore:
- Keep the JSON file safe
- MongoDB will auto-restore if you use same database

## Tips & Tricks

### 💡 Pro Tips

1. **Batch Size**: Generate 5-10 companies at once for efficiency
2. **Caching**: First search takes longer (loading company database)
3. **Keyboard**: Use Tab to navigate between fields
4. **Dark Mode**: Supported on Windows 11 and newer (auto-detected)
5. **Progress**: Look at status bar for real-time operation info

### ⚡ Shortcuts

- **Home Tab**: Quick access from any tab (click "Home" button)
- **Search**: Press Enter after typing to search
- **Generate**: Press Enter in identifier field to start

## Understanding the UI

### Status Bar (Bottom)
Shows current operation status:
- "Ready" - Application idle
- "Processing..." - Operation in progress
- Error messages for failures

### Progress Bar
Appears in Generate Profiles tab during batch operations.
Shows:
- Current progress (X of Y)
- Percentage complete
- Estimated time remaining

### Table Views
All table views support:
- **Double-click**: Open details
- **Right-click**: Context menu (copy, etc.)
- **Sorting**: Click column header to sort
- **Scrolling**: Use arrow keys or mouse wheel

## Configuration Options

### Settings Tab

**Database Settings:**
- MongoDB URI: Change if not using localhost
- Database Name: Default is "Entities"
- Collection Name: Default is "Fundamental_Data_Pipeline"

**Maintenance:**
- Backup Database: Export all data
- Clear Cache: Refresh company list

### Advanced Configuration

Edit `config/config.yaml` for:
```yaml
mongodb:
  uri: mongodb://localhost:27017
  db_name: Entities
  collection: Fundamental_Data_Pipeline
```

## Troubleshooting

### "MongoDB: Disconnected"

**Problem**: App can't connect to database

**Solution**:
1. Start MongoDB: `mongod`
2. Wait 2-3 seconds
3. Click Tools → Refresh Database

### Search Returns No Results

**Problem**: Can't find companies

**Solution**:
1. Go to Settings
2. Click Clear Cache
3. Wait for reload
4. Try search again

### Generation Fails

**Problem**: Profile generation stops with error

**Solution**:
1. Check MongoDB is running
2. Try single company instead of batch
3. Check SEC EDGAR API is reachable
4. Review status bar for error message

### Application Slow

**Problem**: App is unresponsive

**Solution**:
1. Close other apps
2. Reduce batch size (try 3-5 companies)
3. Check system resources (RAM, CPU)
4. Restart application

### "Cannot connect to SEC API"

**Problem**: Can't fetch company data

**Solution**:
1. Check internet connection
2. SEC API may be rate-limited (wait 1 hour)
3. Verify company has filed with SEC
4. Try different company

## Database Management

### Understanding Your Data

Each company profile contains:
- **Company Info**: Name, ticker, CIK
- **Financial Data**: Revenue, assets, liabilities
- **Ratios**: Financial health indicators
- **Growth Rates**: Year-over-year changes
- **Health Score**: 0-100 rating
- **Volatility**: Risk metrics

### Backup Strategy

Recommended:
1. Backup weekly using Settings → Backup Database
2. Store backups in cloud (OneDrive, Google Drive, etc.)
3. Test restore process monthly

### Deleting Profiles

1. View Profiles tab
2. Find company
3. Click Delete button
4. Confirm deletion

Deleted profiles can be recovered from backup.

## Performance Tips

### Optimize Startup
- Close browser and unnecessary apps
- Ensure MongoDB is pre-running
- SSD provides faster startup

### Optimize Batch Processing
- Process 5-10 companies at a time
- Process during off-peak SEC hours (evening/weekend)
- Monitor progress - cancel if errors occur

### Optimize Searches
- Use ticker search (fastest)
- Use name search for ~10 results
- Full database search slower on large datasets

## Next Steps

1. **Read DESKTOP_APP_GUIDE.md** for comprehensive documentation
2. **Review ARCHITECTURE.md** for system design details
3. **Explore all tabs** to familiarize yourself with features
4. **Generate profiles** for companies you care about
5. **Use Analytics** to compare and analyze

## Getting Help

If you encounter issues:

1. **Check Status Bar**: Current operation status
2. **Review Logs**: Open dev console (Ctrl+Shift+I on some systems)
3. **Verify MongoDB**: Ensure it's running and accessible
4. **Test SEC API**: Try searching for a major company (AAPL, MSFT)
5. **Restart Application**: Fixes most transient issues

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Exit App | Alt+F4 or Cmd+Q |
| Switch Tab | Ctrl+Tab |
| Search | Enter in Search field |
| Clear | Escape in text field |
| Refresh | F5 |

## Learning Resources

- **DESKTOP_APP_GUIDE.md** - Complete feature reference
- **ARCHITECTURE.md** - System design and components
- **README.md** - Project overview
- **MIGRATION.md** - Transition from previous version

## Frequently Asked Questions

**Q: Does my data sync to cloud?**
A: No. Data is stored locally in MongoDB. You must backup manually.

**Q: Can I use remote MongoDB?**
A: Yes. Change URI in Settings tab.

**Q: How often are companies updated?**
A: SEC updates filings in real-time. App fetches latest data.

**Q: Can I export profiles?**
A: Yes, backup creates JSON file. Can be imported/parsed externally.

**Q: Is API key required?**
A: No. SEC EDGAR API is public and free.

**Q: Can I run multiple instances?**
A: Yes, but they share the same MongoDB database.

**Q: What's the maximum companies I can store?**
A: Unlimited (depends on disk space and MongoDB).

## Success Indicators

You'll know it's working when:
- ✓ MongoDB shows "Connected" in Home tab
- ✓ Search finds companies successfully
- ✓ Profile generation completes without errors
- ✓ View Profiles shows generated data
- ✓ Analytics calculates statistics
- ✓ Settings backup creates JSON file

## You're Ready!

You now have a fully functional Fundamental Data Pipeline desktop application. Start exploring and analyzing company data!

Questions? Check the documentation or review the application error messages for detailed guidance.

