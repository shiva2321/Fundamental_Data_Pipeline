# 🏗️ Relationship Extraction Architecture

**Complete technical architecture of the integrated relationship extraction system**

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROFILE GENERATION PIPELINE                       │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
┌──────────────────────┬──────────────────────┬──────────────────────┐
│   Financial Data     │   Key Persons Data   │ RELATIONSHIPS (NEW)  │
│   Extraction         │   Extraction         │ Extraction           │
├──────────────────────┼──────────────────────┼──────────────────────┤
│ • Revenues           │ • Executives         │ • Company mentions   │
│ • Assets             │ • Board members      │ • Relationships      │
│ • Liabilities        │ • Insiders           │ • Customers/suppliers│
│ • Ratios             │ • Holdings           │ • Interlocks         │
│ • Growth             │                      │ • Conflicts          │
└──────────────────────┴──────────────────────┴──────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    UNIFIED COMPANY PROFILE                           │
│  (Stored in Fundamental_Data_Pipeline collection)                   │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓
         ┌───────────────────────┼───────────────────────┐
         ↓                       ↓                       ↓
  ┌─────────────────┐   ┌──────────────────┐   ┌────────────────┐
  │ company_        │   │ financial_       │   │ key_person_    │
  │ relationships   │   │ relationships    │   │ interlocks     │
  └─────────────────┘   └──────────────────┘   └────────────────┘
         ↓                       ↓                       ↓
  ┌─────────────────────────────────────────────────────────────────┐
  │              RELATIONAL GRAPH GENERATION                         │
  │  (NetworkX, Neo4j, or custom graph algorithms)                  │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Module Architecture

### Layer 1: Data Extraction Modules

```
src/extractors/
├── __init__.py                          [Exports all extractors]
│
├── company_mention_extractor.py
│   ├── CompanyMentionExtractor
│   │   ├── extract_mentions()
│   │   ├── _find_exact_matches()
│   │   ├── _find_ticker_matches()
│   │   └── _find_fuzzy_matches()
│   └── CompanyMentionExtractorWithAliases
│       └── extract_mentions()  [+ alias matching]
│
├── relationship_context_extractor.py
│   ├── RelationshipContextExtractor
│   │   ├── extract_relationships()
│   │   ├── _determine_relationship_type()
│   │   └── [patterns for supplier, customer, competitor, partner, investor]
│   └── RelationshipStrengthCalculator
│       └── calculate_strength()
│
├── financial_relationships_extractor.py
│   ├── FinancialRelationshipsExtractor
│   │   ├── extract_customers()
│   │   ├── extract_suppliers()
│   │   ├── extract_segments()
│   │   └── extract_supply_chain_risks()
│   └── CustomerConcentrationAnalyzer
│       ├── calculate_herfindahl_index()
│       └── calculate_concentration_ratio()
│
├── key_person_interlock_extractor.py
│   └── KeyPersonInterlockExtractor
│       ├── build_person_index()
│       ├── find_interlocks()
│       ├── find_executive_transfers()
│       ├── find_conflict_of_interest()
│       └── get_statistics()
│
└── relationship_integrator.py            [Main integration module]
    └── RelationshipDataIntegrator
        ├── extract_relationships_for_profile()
        ├── store_relationships_in_profile()
        ├── refresh_key_person_interlocks()
        └── _create_relationship_documents()
```

### Layer 2: Pipeline Integration

```
src/analysis/
└── unified_profile_aggregator.py
    └── UnifiedSECProfileAggregator.aggregate_company_profile()
        ├── ... (existing financial extraction)
        ├── ... (existing key persons extraction)
        ├── NEW: Call RelationshipDataIntegrator.extract_relationships_for_profile()
        ├── NEW: Call RelationshipDataIntegrator.store_relationships_in_profile()
        └── Return profile with relationships
```

### Layer 3: Data Storage

```
MongoDB Collections:
├── Fundamental_Data_Pipeline              [Company profiles with relationships]
│   ├── relationships.company_mentions
│   ├── relationships.relationships
│   └── relationships.financial_relationships
│
├── company_relationships                  [Graph edges]
│   ├── (source_cik, target_cik, relationship_type) - unique key
│   └── confidence_score, context, extraction_method
│
├── financial_relationships                [Customer/supplier data]
│   ├── cik (unique key)
│   ├── customers[], suppliers[]
│   ├── segments, customer_concentration
│   └── supply_chain_risks
│
├── key_person_interlocks                  [Board interlocks]
│   ├── person_name (unique key)
│   ├── company1_cik, company1_title
│   ├── company2_cik, company2_title
│   └── conflict_level
│
└── conflicts_of_interest                  [Governance conflicts]
    ├── person_name (unique key)
    ├── company pairs with conflict
    └── severity (SEVERE, MODERATE, LOW)
```

---

## Data Flow

### Profile Generation Workflow

```python
1. USER INITIATES: Add ticker to queue (e.g., "AAPL")
   ↓
2. FETCH: SECEdgarClient.get_company_filings()
   - Returns: [filing dict, filing dict, ...]
   ↓
3. EXTRACT FINANCIAL DATA (existing)
   - UnifiedSECProfileAggregator extracts financial metrics
   ↓
4. EXTRACT KEY PERSONS (existing)
   - KeyPersonsParser extracts executives, board members
   ↓
5. NEW - EXTRACT RELATIONSHIPS
   a. Compile filing text (10-K MD&A, 8-K, etc.)
      ↓
   b. CompanyMentionExtractor.extract_mentions()
      - Find all company mentions in text
      - Returns: [(cik, name, confidence), ...]
      ↓
   c. RelationshipContextExtractor.extract_relationships()
      - Determine relationship type between mentions
      - Returns: [{source_cik, target_cik, relationship_type, confidence}, ...]
      ↓
   d. FinancialRelationshipsExtractor.extract_*()
      - Extract customers, suppliers, segments
      - Returns: {customers: [...], suppliers: [...], segments: {...}}
      ↓
   e. RelationshipDataIntegrator._create_relationship_documents()
      - Convert to MongoDB documents
      ↓
6. STORE RELATIONSHIPS
   a. Add relationships to company profile
      - profile['relationships'] = {...}
      ↓
   b. Store in company_relationships collection
      - upsert_one() to handle duplicates
      ↓
   c. Store in financial_relationships collection
      - Customer/supplier concentration data
      ↓
7. KEY PERSON INTERLOCKS (batch, after all profiles)
   a. KeyPersonInterlockExtractor.build_person_index()
      - Index all persons across all profiles
      ↓
   b. find_interlocks()
      - Find persons with multiple affiliations
      ↓
   c. Store in key_person_interlocks collection
      ↓
8. PROFILE COMPLETE
   - Stored in Fundamental_Data_Pipeline
   - Contains all relationships
```

---

## Extraction Methods & Confidence Scores

### Company Mention Extraction

| Method | Confidence | Example |
|--------|-----------|---------|
| Exact name match | 0.99 | "Apple Inc" = "Apple Inc" |
| Ticker match | 0.98 | "$AAPL" = "Apple Inc" |
| Alias match | 0.95 | "Apple" = "Apple Inc" |
| Fuzzy match | 0.80-0.95 | "Appl Inc" ≈ "Apple Inc" |

### Relationship Context Extraction

| Relationship Type | Strong Confidence | Medium Confidence |
|------------------|------------------|-------------------|
| supplier | "depends on X for components" (0.90) | "purchase from X" (0.65) |
| customer | "sold to X (Y%)" (0.90) | "customer base" (0.65) |
| competitor | "competes with X" (0.90) | "competitive" (0.65) |
| partner | "partnership with X" (0.90) | "cooperates with X" (0.65) |

### Financial Relationship Extraction

| Data Type | Confidence | Source |
|-----------|-----------|--------|
| Customer with revenue % | 0.85+ | "X represented 35% of revenue" |
| Supplier listed | 0.75 | "suppliers include: X, Y, Z" |
| Revenue by segment | 0.90 | 10-K Item 8 financial statements |
| Geographic concentration | 0.80 | "primarily sourced from Taiwan" |

---

## Performance Characteristics

### Extraction Time per Profile

```
Company Size: Large (1000+ filings)
├── Filing fetch: 2-5s
├── Financial extraction: 1-2s
├── Key persons extraction: 0.5-1s
├── Company mention extraction: 2-3s
├── Relationship extraction: 1-2s
├── Financial relationship extraction: 0.5-1s
└── Total: ~8-14 seconds

Company Size: Medium (100-500 filings)
├── ... (proportionally less)
└── Total: ~4-8 seconds

Company Size: Small (<100 filings)
├── ... (proportionally less)
└── Total: ~2-4 seconds
```

### Storage Requirements

```
Per Company Profile (with relationships):
├── Base profile: ~50 KB
├── Relationships section: ~20-100 KB (varies by company size)
├── Financial relationships: ~10-50 KB
└── Total: ~80-200 KB per profile

For 10,000 companies:
├── Profiles collection: ~1-2 GB
├── company_relationships collection: ~2-5 GB (graphs grow)
├── financial_relationships collection: ~500 MB - 1 GB
├── key_person_interlocks: ~50-100 MB
└── Total MongoDB: ~4-8 GB
```

---

## Scalability Considerations

### Handling Large Batches

```python
# For 1000+ companies, use:

# 1. Parallel processing (if available)
from multiprocessing import Pool

with Pool(4) as p:
    profiles = p.map(process_company, company_list)

# 2. Incremental batch processing
for batch in chunks(company_list, 100):
    for company in batch:
        process_company(company)
    
    # Refresh interlocks after each batch
    integrator.refresh_key_person_interlocks(get_processed_profiles())
    
    # Save progress checkpoint
    save_checkpoint()

# 3. Memory-efficient extraction
# Disable AI analysis during batch
options = {'ai_enabled': False, 'lookback_years': 10}
```

### Query Performance

```python
# Create indexes for common queries
db['company_relationships'].create_index([('source_cik', 1)])
db['company_relationships'].create_index([('target_cik', 1)])
db['company_relationships'].create_index([('relationship_type', 1)])

# Example queries:
# Find all suppliers: 50ms (with index)
# Find all customers: 50ms (with index)
# Find supply chain cluster: 100-500ms
# Find interlocks: 100ms
```

---

## Error Handling & Recovery

### Extraction Failures

```python
# All extractors handle exceptions gracefully

try:
    mentions = extractor.extract_mentions(text)
except Exception as e:
    logger.error(f"Mention extraction failed: {e}")
    mentions = []  # Return empty list

# Result: Profile still created, just without relationships
# User can retry later to re-extract relationships
```

### Duplicate Handling

```python
# MongoDB upsert automatically handles duplicates

mongo.upsert_one(
    'company_relationships',
    {  # Query
        'source_cik': cik1,
        'target_cik': cik2,
        'relationship_type': 'supplier'
    },
    {  # Update document
        'mention_count': mention_count + 1,
        'last_mentioned': datetime.now(),
        'confidence_score': max(old_conf, new_conf)
    }
)
# If document exists: updates it
# If doesn't exist: creates it
```

---

## Testing Strategy

### Unit Tests

```python
# Test each extractor independently
test_company_mention_extractor.py
├── test_exact_match()
├── test_ticker_match()
├── test_fuzzy_match()
└── test_deduplication()

test_relationship_context_extractor.py
├── test_supplier_detection()
├── test_customer_detection()
├── test_confidence_scoring()
└── test_sentence_splitting()

test_financial_relationships_extractor.py
├── test_customer_extraction()
├── test_supplier_extraction()
├── test_hhi_calculation()
└── test_segment_extraction()

test_key_person_interlock_extractor.py
├── test_interlock_detection()
├── test_conflict_identification()
└── test_statistics()
```

### Integration Tests

```python
test_integration.py
├── test_full_profile_generation()  # End-to-end
├── test_relationship_storage()     # MongoDB storage
├── test_batch_processing()         # Multiple profiles
└── test_performance()              # Speed benchmarks
```

### Validation Tests

```python
test_accuracy.py
├── test_against_manual_validation()  # Compare with hand-labeled data
├── test_confidence_scores()
└── test_duplicate_detection()
```

---

## Configuration Parameters

### In config/config.yaml

```yaml
extractors:
  enabled: true
  
  company_mentions:
    fuzzy_threshold: 0.82
    min_confidence: 0.50
    use_aliases: true
    
  relationships:
    enabled: true
    min_confidence_score: 0.50
    max_relationships: 1000
    
  financial_relationships:
    enabled: true
    extract_customers: true
    extract_suppliers: true
    extract_segments: true
    extract_risks: true
    
  key_person_interlocks:
    enabled: true
    build_on_demand: false
    build_after_batch: true
```

---

## Future Enhancements

### Phase 2: Graph Analysis (Neo4j)
```
- Use Neo4j for advanced graph queries
- Community detection algorithms
- Supply chain impact analysis
- Network resilience scoring
```

### Phase 3: ML-Based Extraction
```
- Transformer models for relation extraction
- Named entity recognition (NER)
- Classification of relationships
- Confidence score refinement
```

### Phase 4: Real-Time Updates
```
- Incrementally update relationships from new filings
- Detect new supplier/customer relationships
- Alert on major supply chain changes
- Track relationship lifecycle
```

---

## Success Metrics (Target)

| Metric | Target | Status |
|--------|--------|--------|
| Company mention accuracy | 90%+ | 🟡 Testing |
| Relationship extraction accuracy | 85%+ | 🟡 Testing |
| Extraction time per profile | < 10s | 🟡 Benchmarking |
| Graph completeness | 95%+ relationships | 🟡 Validation |
| Duplicate rate | < 1% | ✅ Auto-handled |
| Key person interlocks found | All | 🟡 Testing |

---

**Architecture Complete** ✅  
**Ready for Integration** ✅

