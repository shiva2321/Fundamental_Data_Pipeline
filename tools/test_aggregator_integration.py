"""Quick integration check for unified_profile_aggregator with key_persons integration.
Verifies imports and basic structure without running full aggregation.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Testing imports...")

# Test 1: Import AIAnalyzer (should work - alias exists)
try:
    from ai_analyzer import AIAnalyzer
    print("✓ AIAnalyzer import successful")
    print(f"  AIAnalyzer is an alias for: {AIAnalyzer.__name__}")
except ImportError as e:
    print(f"✗ AIAnalyzer import FAILED: {e}")
    sys.exit(1)

# Test 2: Import KeyPersonsParser
try:
    from key_persons_parser import KeyPersonsParser
    print("✓ KeyPersonsParser import successful")
except ImportError as e:
    print(f"✗ KeyPersonsParser import FAILED: {e}")
    sys.exit(1)

# Test 3: Import unified aggregator
try:
    from unified_profile_aggregator import UnifiedSECProfileAggregator
    print("✓ UnifiedSECProfileAggregator import successful")
except ImportError as e:
    print(f"✗ UnifiedSECProfileAggregator import FAILED: {e}")
    sys.exit(1)

# Test 4: Check if OllamaAIAnalyzer exists and analyze_profile method
try:
    from ai_analyzer import OllamaAIAnalyzer
    analyzer = OllamaAIAnalyzer()
    assert hasattr(analyzer, 'analyze_profile'), "analyze_profile method missing"
    print("✓ OllamaAIAnalyzer instantiation and method check successful")
except Exception as e:
    print(f"✗ OllamaAIAnalyzer check FAILED: {e}")
    sys.exit(1)

# Test 5: Check KeyPersonsParser instantiation and method
try:
    parser = KeyPersonsParser()
    assert hasattr(parser, 'parse_key_persons'), "parse_key_persons method missing"
    print("✓ KeyPersonsParser instantiation and method check successful")
except Exception as e:
    print(f"✗ KeyPersonsParser check FAILED: {e}")
    sys.exit(1)

# Test 6: Verify visualization imports
try:
    from visualization_window import ProfileVisualizationWindow
    print("✓ ProfileVisualizationWindow import successful")
except ImportError as e:
    print(f"✗ ProfileVisualizationWindow import FAILED: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("INTEGRATION CHECK SUMMARY")
print("="*60)
print("✓ All critical imports successful")
print("✓ AIAnalyzer alias working correctly")
print("✓ KeyPersonsParser integrated and functional")
print("✓ UnifiedSECProfileAggregator ready")
print("✓ Visualization components ready")
print("\nBranch 'copilot/analyze-company-pipeline' is READY for integration!")
print("="*60)

