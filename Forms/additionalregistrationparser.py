"""
SEC Additional Registration Forms (S-Series and F-Series)
==========================================================
Additional S-forms and F-forms for various registrations

S-3: Short form registration
S-4: Business combinations
S-11: Real estate investment trusts (REITs)
F-2: Foreign issuer short form
F-4: Foreign issuer business combinations
F-6: ADR registration
F-8: Canadian offerings
F-10: Canadian multi-jurisdictional

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, List, Any
from Forms.baseParser import SECFormParser


class S3Parser(SECFormParser):
    """Parser for Form S-3 - Short Form Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form S-3 document"""
        result = {
            "form_type": "S-3 - Short Form Registration",
            "filing_info": self._parse_header(document_text),
            "securities_registered": [],
            "incorporation_by_reference": []
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class S4Parser(SECFormParser):
    """Parser for Form S-4 - Business Combination Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form S-4 document"""
        result = {
            "form_type": "S-4 - Business Combination Registration",
            "filing_info": self._parse_header(document_text),
            "transaction_details": {},
            "parties_involved": []
        }
        
        result["transaction_details"] = self._parse_transaction(document_text)
        
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_transaction(self, document_text: str) -> Dict[str, str]:
        """Parse transaction details"""
        return {
            "transaction_type": self._extract_field(
                document_text, r'(merger|acquisition|combination)'
            )
        }


class S11Parser(SECFormParser):
    """Parser for Form S-11 - Real Estate Investment Trust (REIT) Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form S-11 document"""
        result = {
            "form_type": "S-11 - REIT Registration",
            "filing_info": self._parse_header(document_text),
            "property_information": {},
            "investment_objectives": []
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class F2Parser(SECFormParser):
    """Parser for Form F-2 - Foreign Issuer Short Form"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-2 document"""
        result = {
            "form_type": "F-2 - Foreign Issuer Short Form Registration",
            "filing_info": self._parse_header(document_text),
            "securities_offered": []
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class F4Parser(SECFormParser):
    """Parser for Form F-4 - Foreign Issuer Business Combination"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-4 document"""
        result = {
            "form_type": "F-4 - Foreign Issuer Business Combination",
            "filing_info": self._parse_header(document_text),
            "transaction_details": {}
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class F6Parser(SECFormParser):
    """Parser for Form F-6 - ADR Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-6 document"""
        result = {
            "form_type": "F-6 - ADR Registration",
            "filing_info": self._parse_header(document_text),
            "depositary_info": {},
            "underlying_securities": {}
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class F8Parser(SECFormParser):
    """Parser for Form F-8 - Canadian Offerings"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-8 document"""
        result = {
            "form_type": "F-8 - Canadian Offering Registration",
            "filing_info": self._parse_header(document_text),
            "offering_details": {}
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""


class F10Parser(SECFormParser):
    """Parser for Form F-10 - Canadian Multi-Jurisdictional"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-10 document"""
        result = {
            "form_type": "F-10 - Canadian Multi-Jurisdictional Registration",
            "filing_info": self._parse_header(document_text),
            "offering_details": {}
        }
        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""
