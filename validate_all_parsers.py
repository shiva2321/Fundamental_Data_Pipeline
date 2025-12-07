"""
Quick Parser Validation Script
===============================
Quick validation of parser imports and basic functionality

This script:
1. Validates all parser imports
2. Checks parser class structure
3. Tests basic parsing capabilities
4. Generates a validation report
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from Forms import FORM_PARSER_MAP, get_parser_for_form_type


def validate_parsers():
    """Validate all parsers"""
    
    print("=" * 80)
    print("SEC FORM PARSER VALIDATION")
    print("=" * 80)
    print()
    
    results = {
        'total_parsers': len(FORM_PARSER_MAP),
        'valid_parsers': 0,
        'invalid_parsers': 0,
        'details': []
    }
    
    for form_type in sorted(FORM_PARSER_MAP.keys()):
        print(f"Validating {form_type:20} ", end='')
        
        parser_class = get_parser_for_form_type(form_type)
        
        if not parser_class:
            print("❌ FAILED - No parser class")
            results['invalid_parsers'] += 1
            results['details'].append({
                'form_type': form_type,
                'status': 'failed',
                'error': 'No parser class found'
            })
            continue
        
        # Check if parser has parse method
        if not hasattr(parser_class, 'parse'):
            print("❌ FAILED - No parse method")
            results['invalid_parsers'] += 1
            results['details'].append({
                'form_type': form_type,
                'status': 'failed',
                'error': 'No parse method'
            })
            continue
        
        # Try to instantiate
        try:
            parser = parser_class()
            
            # Test with minimal text
            test_text = """<SEC-HEADER>
ACCESSION NUMBER: 0000000000-00-000000
CONFORMED SUBMISSION TYPE: TEST
PUBLIC DOCUMENT COUNT: 1
FILED AS OF DATE: 20250101
COMPANY CONFORMED NAME: TEST COMPANY
CENTRAL INDEX KEY: 0000000000
</SEC-HEADER>
<DOCUMENT>
<TYPE>TEST
<SEQUENCE>1
<TEXT>
Test content
</TEXT>
</DOCUMENT>"""
            
            result = parser.parse(test_text)
            
            if result is None:
                print("⚠️  WARNING - Parser returned None")
                results['valid_parsers'] += 1
                results['details'].append({
                    'form_type': form_type,
                    'status': 'warning',
                    'parser_class': parser_class.__name__,
                    'warning': 'Parser returned None on test input'
                })
            elif not isinstance(result, dict):
                print(f"❌ FAILED - Returned {type(result)} instead of dict")
                results['invalid_parsers'] += 1
                results['details'].append({
                    'form_type': form_type,
                    'status': 'failed',
                    'error': f'Parser returned {type(result)} instead of dict'
                })
            else:
                print(f"✅ PASSED - {parser_class.__name__}")
                results['valid_parsers'] += 1
                results['details'].append({
                    'form_type': form_type,
                    'status': 'passed',
                    'parser_class': parser_class.__name__
                })
                
        except Exception as e:
            print(f"❌ FAILED - {str(e)[:50]}")
            results['invalid_parsers'] += 1
            results['details'].append({
                'form_type': form_type,
                'status': 'failed',
                'error': str(e)
            })
    
    print()
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total Parsers: {results['total_parsers']}")
    print(f"Valid Parsers: {results['valid_parsers']}")
    print(f"Invalid Parsers: {results['invalid_parsers']}")
    
    if results['total_parsers'] > 0:
        success_rate = (results['valid_parsers'] / results['total_parsers']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    print("=" * 80)
    
    # Save report
    with open('validation_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nValidation report saved to: validation_report.json")
    
    return results


if __name__ == "__main__":
    validate_parsers()
