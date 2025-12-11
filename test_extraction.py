#!/usr/bin/env python3
"""
Diagnose why relationships aren't being extracted
"""
import logging
from src.clients.mongo_client import MongoWrapper
from src.clients.sec_edgar_api_client import SECEdgarClient
from src.analysis.unified_profile_aggregator import UnifiedSECProfileAggregator
from src.utils.config import load_config

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_extraction():
    print("=" * 70)
    print("TESTING RELATIONSHIP EXTRACTION")
    print("=" * 70)

    # Load config
    config = load_config().config
    mongo = MongoWrapper(uri=config['mongodb']['uri'], database=config['mongodb']['db_name'])

    # Get one profile
    profile_data = mongo.db['Fundamental_Data_Pipeline'].find_one({})
    if not profile_data:
        print("No profiles found!")
        return

    cik = profile_data.get('cik')
    ticker = profile_data.get('company_info', {}).get('ticker', 'N/A')

    print(f"\nTesting with: {ticker} (CIK: {cik})")

    # Initialize
    sec_client = SECEdgarClient()
    aggregator = UnifiedSECProfileAggregator(mongo, sec_client)

    # Options
    options = {
        'lookback_years': 5,
        'filing_limit': None,
        'incremental': False,
        'ai_enabled': False,
        'extract_relationships': True,
        'config': config
    }

    print("\nStarting profile generation with relationship extraction...")
    print("Watch for log messages about relationship extraction...")
    print("-" * 70)

    # Process
    try:
        profile = aggregator.aggregate_company_profile(
            cik=cik,
            company_info=profile_data.get('company_info', {}),
            output_collection='Fundamental_Data_Pipeline',
            options=options,
            progress_callback=lambda level, msg: print(f"  [{level}] {msg}")
        )

        print("-" * 70)
        print("\nRESULTS:")

        if profile:
            relationships = profile.get('relationships', {})
            if relationships:
                rel_list = relationships.get('relationships', [])
                print(f"✓ Relationships section exists")
                print(f"✓ Found {len(rel_list)} relationships")

                if rel_list:
                    print(f"\nSample relationships:")
                    for rel in rel_list[:3]:
                        print(f"  - {rel.get('relationship_type')}: {rel.get('target_name')} (confidence: {rel.get('confidence_score', 0):.2f})")
                else:
                    print("⚠ Relationships section exists but is empty")
                    print("\nPossible reasons:")
                    print("- No companies mentioned in filings")
                    print("- Filing text was empty")
                    print("- Confidence threshold too high")
            else:
                print("✗ No relationships section in profile!")
                print("\nThis means extraction was skipped or failed")
        else:
            print("✗ Profile generation failed!")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_extraction()

