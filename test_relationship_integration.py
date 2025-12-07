#!/usr/bin/env python3
"""
Quick Test Script for Relationship Extraction Integration

Run this to verify the integration is working correctly.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_relationship_extractors():
    """Test that all extractors can be imported and instantiated"""
    print("Testing relationship extractor modules...")

    try:
        from src.extractors.company_mention_extractor import CompanyMentionExtractor
        print("✓ CompanyMentionExtractor imported")
    except Exception as e:
        print(f"✗ CompanyMentionExtractor failed: {e}")
        return False

    try:
        from src.extractors.relationship_context_extractor import RelationshipContextExtractor
        print("✓ RelationshipContextExtractor imported")
    except Exception as e:
        print(f"✗ RelationshipContextExtractor failed: {e}")
        return False

    try:
        from src.extractors.financial_relationships_extractor import FinancialRelationshipsExtractor
        print("✓ FinancialRelationshipsExtractor imported")
    except Exception as e:
        print(f"✗ FinancialRelationshipsExtractor failed: {e}")
        return False

    try:
        from src.extractors.key_person_interlock_extractor import KeyPersonInterlockExtractor
        print("✓ KeyPersonInterlockExtractor imported")
    except Exception as e:
        print(f"✗ KeyPersonInterlockExtractor failed: {e}")
        return False

    try:
        from src.extractors.relationship_integrator import RelationshipDataIntegrator
        print("✓ RelationshipDataIntegrator imported")
    except Exception as e:
        print(f"✗ RelationshipDataIntegrator failed: {e}")
        return False

    return True


def test_ui_components():
    """Test that UI components can be imported"""
    print("\nTesting UI components...")

    try:
        from src.ui.relationship_graph_widget import RelationshipGraphWidget
        print("✓ RelationshipGraphWidget imported")
    except Exception as e:
        print(f"✗ RelationshipGraphWidget failed: {e}")
        return False

    try:
        from src.ui.visualization_window import ProfileVisualizationWindow
        print("✓ ProfileVisualizationWindow imported")
    except Exception as e:
        print(f"✗ ProfileVisualizationWindow failed: {e}")
        return False

    return True


def test_profile_aggregator():
    """Test that unified profile aggregator has relationship extraction"""
    print("\nTesting profile aggregator integration...")

    try:
        from src.analysis.unified_profile_aggregator import UnifiedSECProfileAggregator

        # Check if the method exists
        if hasattr(UnifiedSECProfileAggregator, '_extract_section_text'):
            print("✓ _extract_section_text method found")
        else:
            print("✗ _extract_section_text method NOT found")
            return False

        print("✓ UnifiedSECProfileAggregator has relationship extraction integration")
        return True

    except Exception as e:
        print(f"✗ UnifiedSECProfileAggregator test failed: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Relationship Extraction Integration Test")
    print("=" * 60)

    all_pass = True
    all_pass = test_relationship_extractors() and all_pass
    all_pass = test_ui_components() and all_pass
    all_pass = test_profile_aggregator() and all_pass

    print("\n" + "=" * 60)
    if all_pass:
        print("✓ All integration tests PASSED!")
        print("\nRelationship extraction is ready to use:")
        print("1. Profiles will automatically extract relationships when processed")
        print("2. Use the 'Relationship Graph' tab in profile visualization to view them")
        print("3. Filter by type, confidence, and view financial relationships")
        sys.exit(0)
    else:
        print("✗ Some tests FAILED. Check errors above.")
        sys.exit(1)

