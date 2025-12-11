# 📄 10-K/10-Q Narrative Parser - Quick Reference

**Comprehensive guide to the 10-K/10-Q narrative section extractor**

---

## Overview

The 10-K/10-Q Parser (`src/parsers/ten_k_parser.py`) extracts narrative sections from annual (10-K) and quarterly (10-Q) reports for qualitative analysis. Unlike the financial data extraction (which uses XBRL), this parser analyzes the textual content to identify risks, business strategy, and management insights.

---

## What It Extracts

### Sections Extracted

The parser focuses on key narrative sections:

| Section | Description | Business Value |
|---------|-------------|----------------|
| **Section 1** | Business Overview | Company strategy, products, markets, competition |
| **Section 1A** | Risk Factors | Detailed risk disclosures (legal, operational, financial) |
| **Section 7** | Management's Discussion & Analysis (MD&A) | Management's view of financial performance and outlook |
| **Section 7A** | Quantitative and Qualitative Disclosures About Market Risk | Interest rate, FX, commodity risk exposure |
| **Section 8** | Financial Statements and Supplementary Data | References to detailed financials |

### Key Metrics Per Section

For each extracted section:
- **Word Count**: Total words in section
- **Keyword Counts**: Frequency of important terms
- **Text Content**: Raw section text for further analysis

### Tracked Keywords

The parser tracks mentions of:
- `risk` - Overall risk mentions
- `litigation` - Legal issues
- `cyber` - Cybersecurity risks
- `regulatory` - Compliance and regulatory risks
- `liquidity` - Financial health concerns
- `macroeconomic` - Economic environment risks
- `revenue` - Revenue discussions
- `cash` - Cash flow and liquidity
- `debt` - Debt and leverage

---

## Usage

### Basic Usage

```python
from src.parsers.ten_k_parser import TenK10QParser

# Initialize parser
parser = TenK10QParser()

# Parse reports (automatically fetches and parses content)
result = parser.parse_reports(
    filings=all_filings,           # List of all company filings
    max_reports_per_form=2         # Parse 2 most recent 10-Ks and 2 most recent 10-Qs
)
```

### Integration with Profile Aggregator

The parser is automatically called during profile aggregation:

```python
from src.analysis.unified_profile_aggregator import UnifiedSECProfileAggregator

aggregator = UnifiedSECProfileAggregator(mongo, sec_client)
profile = aggregator.aggregate_company_profile(cik='0000320193')

# Access narrative data
narrative_data = profile.get('narrative_analysis', {})
```

---

## Output Structure

### Full Output Example

```json
{
    "total_reports": 4,
    "forms_seen": {
        "10-K": 2,
        "10-Q": 2
    },
    "reports": [
        {
            "form": "10-K",
            "filing_date": "2024-02-15",
            "report_date": "2023-12-31",
            "accession_number": "0001065280-24-000123",
            "available": true,
            "sections": {
                "1": {
                    "summary": {
                        "word_count": 5432,
                        "keyword_counts": {
                            "revenue": 45,
                            "cash": 23,
                            "debt": 12
                        }
                    },
                    "text": "Item 1. Business\n\nOur company operates..."
                },
                "1A": {
                    "summary": {
                        "word_count": 12543,
                        "keyword_counts": {
                            "risk": 312,
                            "litigation": 45,
                            "cyber": 18,
                            "regulatory": 67,
                            "macroeconomic": 23
                        }
                    },
                    "text": "Item 1A. Risk Factors\n\nRisks Related to Our Business..."
                },
                "7": {
                    "summary": {
                        "word_count": 8765,
                        "keyword_counts": {
                            "revenue": 89,
                            "liquidity": 34,
                            "cash": 56
                        }
                    },
                    "text": "Item 7. Management's Discussion and Analysis..."
                },
                "7A": {
                    "summary": {
                        "word_count": 1234,
                        "keyword_counts": {
                            "risk": 45,
                            "debt": 12
                        }
                    },
                    "text": "Item 7A. Quantitative and Qualitative Disclosures..."
                },
                "8": {
                    "summary": {
                        "word_count": 456,
                        "keyword_counts": {}
                    },
                    "text": "Item 8. Financial Statements..."
                }
            },
            "insights": {
                "risk_intensity": "High",
                "business_complexity": "Moderate",
                "financial_discussion_depth": "Detailed"
            }
        }
    ],
    "risk_summary": {
        "average_word_count": 11234,
        "keyword_mentions": 856
    },
    "mdna_summary": {
        "average_word_count": 8765,
        "keyword_mentions": 234
    },
    "warnings": []
}
```

---

## Analysis Use Cases

### 1. Risk Assessment

**Goal**: Identify companies with increasing risk disclosures

```python
# Compare risk factor word counts over time
reports = narrative_data['reports']
risk_trends = []

for report in reports:
    risk_section = report['sections']['1A']
    risk_trends.append({
        'date': report['filing_date'],
        'word_count': risk_section['summary']['word_count'],
        'risk_mentions': risk_section['summary']['keyword_counts'].get('risk', 0)
    })

# Increasing word count or risk mentions may indicate growing concerns
```

**Interpretation**:
- **Increasing risk section length** → Company faces more risks or provides more detail
- **High litigation mentions** → Legal exposure
- **Growing cyber mentions** → Cybersecurity concerns
- **Regulatory keyword spikes** → Compliance challenges

### 2. Business Strategy Analysis

**Goal**: Understand company's strategic focus

```python
# Analyze business section for strategic keywords
business_section = reports[0]['sections']['1']
text = business_section['text'].lower()

# Custom keyword analysis
strategic_keywords = {
    'innovation': text.count('innovation'),
    'digital': text.count('digital'),
    'sustainability': text.count('sustainability'),
    'expansion': text.count('expansion'),
    'acquisition': text.count('acquisition')
}

# High counts indicate strategic priorities
```

### 3. MD&A Trend Analysis

**Goal**: Track management's view of performance

```python
# Track MD&A discussion depth
mdna_trends = []

for report in reports:
    mdna = report['sections']['7']
    mdna_trends.append({
        'date': report['filing_date'],
        'depth': mdna['summary']['word_count'],
        'liquidity_focus': mdna['summary']['keyword_counts'].get('liquidity', 0),
        'revenue_discussion': mdna['summary']['keyword_counts'].get('revenue', 0)
    })

# Decreasing word count might indicate less transparency
# Increasing liquidity mentions might signal cash flow concerns
```

### 4. Comparative Analysis

**Goal**: Compare risk disclosures across companies

```python
# Compare risk intensity between companies
company_a_risk = company_a_profile['narrative_analysis']['risk_summary']['keyword_mentions']
company_b_risk = company_b_profile['narrative_analysis']['risk_summary']['keyword_mentions']

risk_ratio = company_a_risk / company_b_risk

if risk_ratio > 1.5:
    print("Company A has significantly more risk disclosures")
```

---

## Configuration

### Adjust Reports Per Form

Control how many reports to parse:

```python
# Parse more historical reports
result = parser.parse_reports(
    filings=all_filings,
    max_reports_per_form=5  # Parse 5 most recent of each type (10-K, 10-Q)
)
```

**Note**: More reports = longer processing time but richer historical context

### Custom Keyword Tracking

Extend the parser to track custom keywords:

```python
# In ten_k_parser.py, modify KEY_TERMS constant
KEY_TERMS = [
    "risk", "litigation", "cyber", "regulatory", "liquidity",
    "macroeconomic", "revenue", "cash", "debt",
    # Add custom terms
    "climate", "esg", "diversity", "artificial intelligence", "blockchain"
]
```

---

## Interpretation Guide

### Risk Factor Section (1A)

**What to look for**:
- **Word count trends**: Growing section may indicate more risks
- **Litigation mentions**: High count suggests legal issues
- **Cyber mentions**: Increasing = growing cybersecurity focus
- **Regulatory mentions**: High count = compliance-heavy industry

**Red flags**:
- Sudden large increase in risk section length
- New risk categories appearing
- Specific, detailed risk descriptions (vs. generic boilerplate)

**Green flags**:
- Stable, consistent risk disclosures
- Generic, industry-standard risks
- Decreasing risk section over time

### MD&A Section (7)

**What to look for**:
- **Detail level**: Longer = more transparent
- **Liquidity mentions**: High count may signal cash concerns
- **Revenue discussion**: Depth indicates management focus
- **Forward-looking statements**: Indicates confidence

**Red flags**:
- Decreasing MD&A length (less transparency)
- High liquidity/debt keyword counts
- Defensive or evasive language
- Lack of forward guidance

**Green flags**:
- Detailed discussion of operations
- Clear explanation of results
- Confident forward-looking statements
- Balanced discussion of challenges and opportunities

### Business Section (1)

**What to look for**:
- **Strategic keywords**: Innovation, expansion, digital
- **Competitive positioning**: Market share, advantages
- **Product/service descriptions**: Breadth and depth

**Interpretation**:
- Rich, detailed business description = mature, complex company
- Focus on innovation keywords = growth-oriented
- Heavy competition discussion = competitive industry

---

## Integration with AI Analysis

The narrative data is included in AI prompts for comprehensive analysis:

```python
# AI prompt includes narrative insights
prompt = f"""
=== NARRATIVE ANALYSIS ===
Risk Factor Section Length: {risk_word_count} words
Risk Mentions: {risk_mentions}
Litigation Mentions: {litigation_mentions}
MD&A Discussion Depth: {mdna_word_count} words

Based on the narrative analysis, the company shows:
- Risk Intensity: {risk_intensity}
- Business Complexity: {business_complexity}
- Management Transparency: {mdna_depth}

Please consider these qualitative factors in your investment recommendation.
"""
```

The AI can then incorporate narrative insights into its analysis, providing a more holistic view combining quantitative metrics with qualitative risk factors.

---

## Performance Considerations

### Processing Time

- **Per 10-K**: ~2-5 seconds (fetch + parse)
- **Per 10-Q**: ~1-3 seconds
- **Total for 4 reports**: ~10-20 seconds

### Memory Usage

- Each report text: ~100-500 KB
- Total for 4 reports: ~2 MB
- Minimal impact on overall profile generation

### SEC Rate Limits

- Parser respects SEC's 10 requests/second limit
- 0.1 second delay between filing fetches
- No special considerations needed

---

## Troubleshooting

### Issue: Sections not extracted

**Cause**: Filing format variation or HTML structure change

**Solution**:
1. Check `warnings` field in output
2. Review filing HTML manually
3. Update regex patterns in `_extract_sections()` method
4. Add fallback patterns for different formats

### Issue: Keyword counts seem low

**Cause**: Section text not fully captured or keyword variations

**Solution**:
1. Check `text` field - is it truncated?
2. Add keyword variations (e.g., "litigation" → also search "lawsuit", "legal proceedings")
3. Use case-insensitive matching

### Issue: "available": false in output

**Cause**: Could not fetch filing content from SEC

**Solution**:
1. Check network connectivity
2. Verify accession number is correct
3. Check SEC Edgar website for filing availability
4. Retry - may be temporary SEC server issue

---

## Best Practices

1. **Parse recent reports only**
   - 2 reports per form type is usually sufficient
   - Older reports may have different formats

2. **Combine with quantitative data**
   - Don't rely solely on narrative analysis
   - Use as complement to financial metrics

3. **Track trends over time**
   - Single report snapshot has limited value
   - Compare across multiple periods

4. **Contextualize by industry**
   - Tech companies naturally have more cyber risk mentions
   - Financial companies have more regulatory mentions
   - Compare to industry peers

5. **Export for deeper analysis**
   - Full text is available in output
   - Use NLP libraries (NLTK, spaCy) for advanced analysis
   - Sentiment analysis on MD&A section
   - Topic modeling on risk factors

---

## Future Enhancements

Potential improvements:
- Sentiment analysis on MD&A text
- Topic modeling on risk factors
- Year-over-year risk comparison
- Industry-specific keyword tracking
- Management tone analysis
- Forward-looking statement extraction

---

## Summary

The 10-K/10-Q Parser provides:

✅ **Automated narrative extraction** from annual/quarterly reports  
✅ **Keyword tracking** for risk and business terms  
✅ **Trend analysis** across multiple periods  
✅ **AI integration** for qualitative insights  
✅ **Quality metrics** (word counts, keyword density)  

**Key Value**: Combines with quantitative financial data to provide a complete picture of company health, risks, and strategy.

