# AI Analysis Setup Guide

## Overview

The Fundamental Data Pipeline includes optional AI-powered analysis using local LLM models through Ollama. This provides advanced investment insights, recommendations, and predictions.

## Setup Instructions

### 1. Install Ollama

**Windows:**
1. Download Ollama from: https://ollama.ai/download
2. Run the installer
3. Ollama will start automatically and run in the background

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
```

### 2. Pull an AI Model

After installing Ollama, open a terminal and pull a model:

```bash
# Recommended: Fast and capable model
ollama pull llama3.2

# Alternative models
ollama pull mistral      # Good balance of speed and quality
ollama pull llama2       # Older but reliable
ollama pull phi          # Very fast, smaller model
ollama pull codellama    # Optimized for technical analysis
ollama pull gemma        # Google's model
```

### 3. Verify Ollama is Running

Test that Ollama is accessible:

```bash
curl http://localhost:11434/api/tags
```

You should see a JSON response with available models.

### 4. Configure the Application

In the Fundamental Data Pipeline app:

1. Go to the **Dashboard & Generate** tab
2. In the **Configuration** section:
   - Select your preferred **AI Model** from the dropdown
   - Check **"Enable AI Analysis During Profile Generation"**
3. The app will use the selected model for all future profile generations

## Using AI Analysis

### During Profile Generation

When AI analysis is enabled:
- Analysis runs automatically during profile generation
- Results are stored in the profile database
- No re-processing needed when visualizing

### In Visualization

Open any profile and navigate to the **AI/ML Analysis** tab to see:
- **Investment Thesis**: High-level summary
- **Recommendation**: Buy/Hold/Sell with confidence level
- **Strengths & Weaknesses**: Key points identified by AI
- **Growth Predictions**: 1-year, 3-year, and 5-year forecasts
- **Risk Assessment**: Risk level and specific concerns
- **Catalysts**: Potential positive triggers
- **Key Assumptions**: What the analysis is based on

## Troubleshooting

### "Ollama API error: 404"

**Problem**: The selected model is not installed.

**Solution**:
```bash
# Check available models
ollama list

# Pull the missing model
ollama pull llama3.2
```

### "Ollama is not running"

**Problem**: Ollama service is not active.

**Solution**:
- **Windows**: Start Ollama from Start Menu
- **macOS/Linux**: Run `ollama serve` in terminal

### "AI/ML analysis completed using rule-based fallback"

**Problem**: Ollama is not available, but the app continued with basic analysis.

**Solution**: This is expected behavior. The app falls back to rule-based analysis when Ollama is unavailable. To use AI:
1. Install and start Ollama
2. Pull a model
3. Enable AI analysis in settings
4. Regenerate the profile

## Performance Considerations

### Model Selection

- **llama3.2**: Best overall quality, moderate speed
- **mistral**: Fast with good quality
- **phi**: Fastest, good for quick analysis
- **llama2**: Reliable but slower
- **codellama**: Best for technical/financial analysis

### Resource Usage

AI analysis adds processing time during profile generation:
- **Small model (phi)**: ~5-10 seconds per company
- **Medium model (mistral)**: ~10-20 seconds per company
- **Large model (llama3.2)**: ~20-30 seconds per company

**Benefits**:
- Analysis is done once during generation
- Visualization is instant (no re-processing)
- Results are cached in database
- Better resource utilization during batch processing

### Disabling AI Analysis

If you don't want AI analysis:
1. Uncheck **"Enable AI Analysis During Profile Generation"**
2. The app will skip AI processing
3. Profiles generate faster
4. AI Analysis tab won't appear in visualization

## Example Workflow

### First Time Setup

```bash
# Install Ollama
# ... (follow installation instructions above)

# Pull recommended model
ollama pull llama3.2

# Verify it's running
ollama list
```

### Generate Profile with AI

1. Open Fundamental Data Pipeline app
2. Configure settings:
   - Lookback Years: 10
   - Filing Limit: All Available
   - AI Model: llama3.2
   - ✓ Enable AI Analysis During Profile Generation
3. Search for a ticker (e.g., "AAPL")
4. Click "Generate Profile Now"
5. Review confirmation dialog
6. Click "Yes" to proceed
7. Monitor progress in logs
8. Once complete, go to Profile Manager
9. Double-click the profile to visualize
10. Navigate to "AI/ML Analysis" tab

### Batch Processing with AI

For processing multiple companies:
1. Enable AI analysis in Configuration
2. Select multiple tickers or use "Add Top N Random Tickers"
3. Review confirmation with all parameters
4. Click "Yes"
5. AI analysis runs for each company during generation
6. All profiles will have AI insights when visualized

## Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| phi | ~2GB | ⚡⚡⚡ | ⭐⭐ | Quick analysis |
| mistral | ~4GB | ⚡⚡ | ⭐⭐⭐ | Balance |
| llama3.2 | ~5GB | ⚡ | ⭐⭐⭐⭐ | Best insights |
| llama2 | ~4GB | ⚡ | ⭐⭐⭐ | Reliable |
| codellama | ~4GB | ⚡⚡ | ⭐⭐⭐ | Technical analysis |
| gemma | ~5GB | ⚡ | ⭐⭐⭐ | Google ecosystem |

## Advanced Configuration

### Custom Ollama URL

If Ollama is running on a different port or host, you can modify `ai_analyzer.py`:

```python
self.ollama_url = "http://your-host:port/api/generate"
```

### Model Parameters

To customize model behavior, edit the request in `ai_analyzer.py`:

```python
response = requests.post(
    self.ollama_url,
    json={
        "model": self.model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "temperature": 0.7,  # Add this for more creative responses
        "top_p": 0.9         # Add this to control randomness
    },
    timeout=30
)
```

## Getting Help

- **Ollama Issues**: https://github.com/ollama/ollama/issues
- **Model Documentation**: https://ollama.ai/library
- **Application Issues**: Check logs in the application

## Summary

✅ **Recommended Setup**:
1. Install Ollama
2. Pull `llama3.2` model
3. Enable AI analysis in app
4. Generate profiles with AI insights

❌ **Skip AI If**:
- You want faster processing
- Limited system resources
- Don't need advanced insights
- Processing large batches quickly

The choice is yours! The application works great with or without AI analysis.

