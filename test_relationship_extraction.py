#!/usr/bin/env python3
"""
Test Enhanced Relationship Extraction

Tests the new extraction system that uses existing profile data.
"""
import logging
from src.clients.mongo_client import MongoWrapper
from src.utils.config import load_config
from src.extractors.profile_relationship_extractor import ProfileRelationshipExtractor

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_extraction():
    print("="* 70)
    print("TESTING ENHANCED RELATIONSHIP EXTRACTION")
    print("=" * 70)

    # Load config and MongoDB
    config = load_config().config
    mongo = MongoWrapper(uri=config['mongodb']['uri'], database=config['mongodb']['db_name'])

    # Get a profile
    profile = mongo.db['Fundamental_Data_Pipeline'].find_one({})
    if not profile:
        print("[ERROR] No profiles found in database")
        return

    ticker = profile.get('company_info', {}).get('ticker', 'N/A')
    cik = profile.get('cik', 'Unknown')

    print(f"\n[TEST] Extracting relationships for: {ticker} (CIK: {cik})")
    print("-" * 70)

    # Create extractor
    extractor = ProfileRelationshipExtractor(mongo)

    # Extract relationships
    try:
        relationships_data = extractor.extract_from_profile(
            profile=profile,
            progress_callback=lambda level, msg: print(f"  [{level.upper()}] {msg}")
        )

        print("-" * 70)
        print("\n[RESULTS]")
        print(f"Relationships found: {len(relationships_data.get('relationships', []))}")

        rels = relationships_data.get('relationships', [])
        if rels:
            print(f"\nFirst {min(5, len(rels))} relationships:")
            for i, rel in enumerate(rels[:5], 1):
                print(f"\n{i}. {rel.get('target_name', 'Unknown')}")
                print(f"   Type: {rel.get('relationship_type', 'unknown')}")
                print(f"   Confidence: {rel.get('confidence_score', 0):.2f}")
                print(f"   Method: {rel.get('extraction_method', 'unknown')}")
                print(f"   Context: {rel.get('context', '')[:100]}...")
        else:
            print("\n[WARNING] No relationships found!")
            print("\nPossible reasons:")
            print("- Profile has no AI analysis or material events")
            print("- Company name/ticker not recognized")
            print("- Text doesn't mention other companies")

        # Store in database
        print(f"\n[ACTION] Storing relationships in database...")
        extractor.store_relationships_in_profile(profile, relationships_data)
        print("[SUCCESS] Relationships stored!")

        # Verify storage
        updated_profile = mongo.db['Fundamental_Data_Pipeline'].find_one({'cik': cik})
        stored_rels = updated_profile.get('relationships', {})
        if stored_rels:
            print(f"[VERIFY] Profile now has relationships section with {len(stored_rels.get('relationships', []))} relationships")
        else:
            print("[ERROR] Relationships not stored properly!")

    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("[COMPLETE] Test finished")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Run the desktop app")
    print("2. Go to Relationship Analysis tab")
    print("3. Click 'Reprocess All Profiles'")
    print("4. Click 'Update Graph' to see relationships!")

if __name__ == '__main__':
    test_extraction()

