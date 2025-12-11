# RELATIONSHIP EXTRACTION - INTEGRATION ARCHITECTURE

## High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    DESKTOP APPLICATION                                │
│                    (desktop_app_pyside.py)                            │
│                                                                        │
│  ┌────────────────────┐      ┌──────────────────┐                    │
│  │  Ticker Selection  │      │  Process Queue   │                    │
│  │  & Processing      │──┬──▶│  Management      │                    │
│  └────────────────────┘  │   └──────────────────┘                    │
│                           │                                           │
│                           ▼                                           │
│                    ┌──────────────────────────────┐                  │
│                    │ Profile Visualization Window  │                  │
│                    │ (visualization_window.py)     │                  │
│                    │                               │                  │
│                    │ ┌───┬────┬────────┬─────┐   │                  │
│                    │ │Fin│Rat│ Growth│Health│   │                  │
│                    │ │   │   │       │      │   │                  │
│                    │ │   │   │ ▼▼▼  │      │   │                  │
│                    │ │   │   │ REL. │      │   │   NEW!            │
│                    │ │   │   │ GRAPH│      │   │                  │
│                    │ └───┴────┴────────┴─────┘   │                  │
│                    │         ▲                    │                  │
│                    │         │                    │                  │
│                    │ ┌───────┴──────────┐         │                  │
│                    │ │ Relationship     │         │                  │
│                    │ │ Graph Widget     │         │  NEW!            │
│                    │ │ (relationship_   │         │                  │
│                    │ │  graph_widget)   │         │                  │
│                    └──────────┬─────────┘         │                  │
│                              │                    │                  │
└──────────────────────────────┼────────────────────┘                  │
                               │                                       │
                               ▼                                       │
              ┌────────────────────────────────┐                      │
              │   MongoDB Wrapper              │                      │
              │  (Queries relationships)       │                      │
              └────────────┬─────────────────┘                        │
                           │                                          │
            ┌──────────────┼──────────────┐                           │
            ▼              ▼              ▼                           │
      ┌──────────┐   ┌──────────────┐  ┌──────────────┐             │
      │ Profiles │   │ Relationships│  │  Financial   │             │
      │(with     │   │ (Graph Edges)│  │ Relationships│             │
      │Relations)│   │              │  │ (Customers,  │             │
      └──────────┘   │              │  │  Suppliers)  │             │
                     └──────────────┘  └──────────────┘             │
           MongoDB Collections                                        │
```

---

## Processing Pipeline Architecture

```
WHEN USER PROCESSES A COMPANY:
═════════════════════════════════════════════════════════════════════

    Ticker Selected
            │
            ▼
    ┌──────────────────────────────────────┐
    │ UnifiedSECProfileAggregator           │
    │ .aggregate_company_profile()          │
    └───┬────────────────────────────────────┘
        │
        ├─ SECTION 1: Filing Metadata
        ├─ SECTION 2: Financial Data
        ├─ SECTION 3-11: Other Analysis
        │
        └─ SECTION 13: RELATIONSHIP EXTRACTION ◄── NEW!
            │
            ├─ Extract filing text (10-K, 10-Q, 8-K)
            │
            ├─ RelationshipDataIntegrator.__init__()
            │  └─ Initialize extractors (once)
            │
            ├─ extract_relationships_for_profile()
            │  │
            │  ├─ CompanyMentionExtractor.extract_mentions()
            │  │  ├─ Exact matches (ticker, name)
            │  │  ├─ Fuzzy matches
            │  │  └─ Returns: [(cik, name, confidence), ...]
            │  │
            │  ├─ RelationshipContextExtractor.extract_relationships()
            │  │  ├─ Analyze sentences
            │  │  ├─ Determine relationship type
            │  │  └─ Returns: [{source, target, type, confidence}, ...]
            │  │
            │  ├─ FinancialRelationshipsExtractor.extract_*()
            │  │  ├─ extract_customers()
            │  │  ├─ extract_suppliers()
            │  │  ├─ extract_segments()
            │  │  └─ Returns: {customers, suppliers, segments, hhi}
            │  │
            │  └─ _create_relationship_documents()
            │     └─ Format for MongoDB
            │
            └─ store_relationships_in_profile()
               ├─ Add to profile['relationships']
               ├─ Insert in company_relationships
               └─ Insert in financial_relationships

        │
        ▼
    ┌──────────────────────────────────┐
    │ Profile with Relationships       │
    │ Stored in MongoDB                │
    └──────────────────────────────────┘
```

---

## User Interaction Flow

```
USER OPENS PROFILE VISUALIZATION
        │
        ▼
    ┌──────────────────────┐
    │ ProfileVisualization │
    │ Window opens         │
    │ (with mongo ref)     │
    └─────────┬────────────┘
              │
              ├─ Check if relationships exist
              │
              ▼
    ┌──────────────────────────────────┐
    │ IF relationships found:           │
    │ ┌────────────────────────────────┐│
    │ │ Add "Relationship Graph" Tab   ││
    │ └────────────────────────────────┘│
    └──────────────────────────────────┘
              │
              ▼
    USER CLICKS "RELATIONSHIP GRAPH" TAB
              │
              ▼
    ┌──────────────────────────────────────┐
    │ RelationshipGraphWidget.__init__()   │
    │ ├─ Create UI components              │
    │ ├─ Setup filters & controls          │
    │ └─ load_all_companies()              │
    │    └─ Query MongoDB: find profiles   │
    │       with relationships             │
    └──────────────────────────────────────┘
              │
              ▼
    COMPANY DROPDOWN POPULATED
              │
              ▼
    USER SELECTS COMPANY
              │
              ▼
    on_company_selected()
        │
        ├─ Load profile from MongoDB
        └─ refresh_relationships()
            │
            ├─ Apply filters (type, confidence)
            ├─ Query company_relationships
            ├─ Populate relationship table
            ├─ Query financial_relationships
            └─ Show customers, suppliers, HHI
```

---

## Data Model

```
PROFILE DOCUMENT (Fundamental_Data_Pipeline)
═══════════════════════════════════════════════════════════════

{
  "cik": "0000320193",
  "company_info": { ... },
  "filing_metadata": { ... },
  "financial_time_series": { ... },
  "key_persons": { ... },
  "relationships": {                    ◄── NEW SECTION
    │
    ├─ "company_mentions": {
    │   "0000320193_0001018724": {
    │     "source_cik": "0000320193",
    │     "target_cik": "0001018724",
    │     "target_name": "Broadcom Inc",
    │     "confidence": 0.92
    │   },
    │   ...
    │ },
    │
    ├─ "relationships": [
    │   {
    │     "source_cik": "0000320193",
    │     "target_cik": "0001018724",
    │     "relationship_type": "supplier",
    │     "confidence_score": 0.92,
    │     "context": "...excerpt...",
    │     "extraction_method": "nlp_text_analysis",
    │     "first_mentioned": "2024-12-07",
    │     "mention_count": 1
    │   },
    │   ...
    │ ],
    │
    ├─ "financial_relationships": {
    │   "customers": [
    │     {
    │       "name": "Carrier Partners",
    │       "revenue_percent": 35.0,
    │       "confidence": 0.85
    │     },
    │     ...
    │   ],
    │   "suppliers": [ ... ],
    │   "segments": {
    │     "Products": {
    │       "revenue": "25300",
    │       "currency": "millions"
    │     },
    │     ...
    │   },
    │   "customer_concentration": {
    │     "herfindahl_index": 2150.5,
    │     "hhi_level": "MODERATE",
    │     "top_5_concentration": 65.5
    │   },
    │   "supply_chain_risks": {
    │     "single_source_suppliers": ["TSMC"],
    │     ...
    │   }
    │ },
    │
    └─ "extraction_metadata": {
      "extracted_at": "2024-12-07T...",
      "extraction_methods": ["company_mention", "relationship_context", ...]
    }
  },
  "generated_at": "2024-12-07T..."
}


RELATIONSHIP DOCUMENT (company_relationships)
═══════════════════════════════════════════════════════════════

{
  "source_cik": "0000320193",
  "source_name": "Apple Inc",
  "target_cik": "0001018724",
  "target_name": "Broadcom Inc",
  "relationship_type": "supplier",
  "confidence_score": 0.92,
  "extraction_method": "nlp_text_analysis",
  "context": "...extracted sentence...",
  "first_mentioned": "2024-12-07",
  "last_mentioned": "2024-12-07",
  "mention_count": 1,
  "created_at": "2024-12-07T...",
  "updated_at": "2024-12-07T..."
}


FINANCIAL RELATIONSHIPS DOCUMENT (financial_relationships)
═══════════════════════════════════════════════════════════════

{
  "cik": "0000320193",
  "company_name": "Apple Inc",
  "customers": [
    {
      "name": "Carrier Partners",
      "revenue_percent": 35.0,
      "confidence": 0.85
    },
    ...
  ],
  "suppliers": [ ... ],
  "segments": { ... },
  "customer_concentration": {
    "herfindahl_index": 2150.5,
    "hhi_level": "MODERATE",
    "top_5_concentration": 65.5
  },
  "supply_chain_risks": { ... },
  "updated_at": "2024-12-07T..."
}
```

---

## Extractor Details

```
COMPANY MENTION EXTRACTOR
═══════════════════════════════════════════════════════════════

Input: Filing Text
Output: [(cik, name, confidence), ...]

Steps:
1. Exact Matches (0.99 confidence)
   - Case-insensitive company name match
   - Example: "Apple Inc" matches database entry
   
2. Ticker Matches (0.98 confidence)
   - Look for $SYMBOL or standalone SYMBOL
   - Example: "$AAPL" or "MSFT" in text
   
3. Fuzzy Matches (0.80-0.95 confidence)
   - FuzzyWuzzy token_set_ratio matching
   - Captures spelling variations
   - Example: "Appl Inc" matches "Apple Inc"
   
4. Deduplication
   - Remove duplicates by CIK
   - Keep highest confidence


RELATIONSHIP CONTEXT EXTRACTOR
═══════════════════════════════════════════════════════════════

Input: Text + Company Mentions
Output: [{source, target, type, confidence}, ...]

Steps:
1. Smart Sentence Splitting
   - Split on sentence boundaries
   - Handle abbreviations
   
2. Identify Multi-Company Sentences
   - Find sentences with 2+ companies mentioned
   
3. Determine Relationship Type
   - Match against patterns:
     * Supplier: "depends on", "supplied by"
     * Customer: "sold to", "revenue from"
     * Competitor: "competes with", "competitive"
     * Partner: "partnership", "joint venture"
     * Investor: "owns", "stake"
   
4. Score Relationships
   - Strong patterns: 0.90 × weight
   - Medium patterns: 0.65 × weight
   - Weight per type (0.70-0.90)
   
5. Calculate Confidence
   - Pattern confidence × mention confidence


FINANCIAL RELATIONSHIPS EXTRACTOR
═══════════════════════════════════════════════════════════════

Input: 10-K/10-Q Filing Text
Output: {customers, suppliers, segments, hhi, risks}

Steps:
1. Extract Customers
   - Patterns: "X represented Y% of revenue"
   - Extract top 15 customers
   
2. Extract Suppliers
   - Patterns: "suppliers include X, Y, Z"
   - Handle comma-separated lists
   
3. Extract Segments
   - Look for segment revenue tables
   - Extract segment names & revenues
   
4. Calculate Concentration
   - HHI = Σ(market_share%)²
   - Classify as Low/Moderate/High
   - Top-5 concentration ratio
   
5. Extract Supply Chain Risks
   - Single-source suppliers
   - Geographic concentration
   - Supplier concentration


KEY PERSON INTERLOCK EXTRACTOR
═══════════════════════════════════════════════════════════════

Input: All Company Profiles
Output: {interlocks, transfers, conflicts}

Steps:
1. Build Global Person Index
   - Index all executives across all companies
   - Person name → [(cik, title, company), ...]
   
2. Identify Interlocks
   - Find persons with 2+ affiliations
   - Determine interlock type
   - Flag potential conflicts
   
3. Detect Executive Transfers
   - Find executives who changed companies
   - Track CEO/CFO/COO movements
   
4. Assess Conflicts
   - CEO + Director = SEVERE
   - CEO + Board = MODERATE
   - Director + Director = LOW
   
5. Store Results
   - key_person_interlocks collection
   - conflicts_of_interest collection
```

---

## Integration Points

```
1. PIPELINE INTEGRATION
   Location: src/analysis/unified_profile_aggregator.py
   Method: aggregate_company_profile()
   When: SECTION 13 (after AI analysis, before profile storage)
   
   Calls: RelationshipDataIntegrator.extract_relationships_for_profile()
   Stores: profile['relationships']
   
2. UI INTEGRATION
   Location: src/ui/visualization_window.py
   Method: setup_ui()
   When: Tab creation (if relationships exist)
   
   Creates: "Relationship Graph" tab
   Uses: RelationshipGraphWidget
   
3. DATA ACCESS INTEGRATION
   Location: src/ui/desktop_app_pyside.py
   Method: on_profile_selected()
   When: Profile visualization opened
   
   Passes: mongo wrapper to visualization window
   Enables: Relationship widget to query MongoDB
```

---

## Confidence Scoring

```
Company Mentions:
├─ Exact Match: 0.99
├─ Ticker Match: 0.98
└─ Fuzzy Match: 0.80-0.95

Relationships:
├─ Pattern Match: 0.65-0.90 (based on type)
├─ Adjusted by: mention_confidence
└─ Final: pattern_score × min(mention_conf1, mention_conf2)

Financial Data:
├─ Explicit in text: 0.85-0.95
├─ Inferred from patterns: 0.70-0.80
└─ Lower confidence = more ambiguity
```

---

## Error Handling

```
At Each Stage:
├─ Text extraction fails → Empty relationships
├─ Company mention fails → Skip relationship detection
├─ Context extraction fails → Still store partial relationships
├─ Financial extraction fails → Proceed without financials
├─ MongoDB storage fails → Log error, continue
└─ Widget initialization fails → Show error message to user

Design: Graceful degradation - one failure doesn't stop entire process
```

---

## Summary

✅ **Fully Integrated System** that:
- Runs automatically during profile processing
- Extracts high-quality relationship data
- Stores in MongoDB for analysis
- Displays in interactive UI tab
- Handles errors gracefully
- Works with existing pipeline

**Ready for production use!**

