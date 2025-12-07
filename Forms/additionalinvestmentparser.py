"""
SEC Additional Investment Company Forms
========================================
Additional N-Series forms for investment companies

N-3: Variable annuity and variable life insurance
N-4: Variable annuity
N-5: Small business investment company
N-6: Variable life insurance
N-8A: Notification of registration
N-8B-2: Initial registration of unit investment trusts
N-14: Business combination by investment company
N-23C-1: Notification of periodic repurchase offer
N-Q: Quarterly holdings

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, Any
from Forms.baseParser import SECFormParser


class N3Parser(SECFormParser):
    """Parser for N-3 - Variable Annuity Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-3 document"""
        result = {
            "form_type": "N-3 - Variable Annuity Registration",
            "filing_info": self._parse_header(document_text),
            "insurance_company": {},
            "contract_information": {}
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


class N4Parser(SECFormParser):
    """Parser for N-4 - Variable Annuity"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-4 document"""
        result = {
            "form_type": "N-4 - Variable Annuity Registration",
            "filing_info": self._parse_header(document_text),
            "contract_details": {}
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


class N5Parser(SECFormParser):
    """Parser for N-5 - Small Business Investment Company"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-5 document"""
        result = {
            "form_type": "N-5 - Small Business Investment Company",
            "filing_info": self._parse_header(document_text),
            "investment_information": {}
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


class N6Parser(SECFormParser):
    """Parser for N-6 - Variable Life Insurance"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-6 document"""
        result = {
            "form_type": "N-6 - Variable Life Insurance Registration",
            "filing_info": self._parse_header(document_text),
            "policy_information": {}
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


class N8AParser(SECFormParser):
    """Parser for N-8A - Notification of Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-8A document"""
        result = {
            "form_type": "N-8A - Notification of Registration",
            "filing_info": self._parse_header(document_text),
            "registration_details": {}
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


class N8B2Parser(SECFormParser):
    """Parser for N-8B-2 - Unit Investment Trust Initial Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-8B-2 document"""
        result = {
            "form_type": "N-8B-2 - Unit Investment Trust Registration",
            "filing_info": self._parse_header(document_text),
            "trust_information": {}
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


class N14Parser(SECFormParser):
    """Parser for N-14 - Investment Company Business Combination"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-14 document"""
        result = {
            "form_type": "N-14 - Investment Company Business Combination",
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


class N23C1Parser(SECFormParser):
    """Parser for N-23C-1 - Notification of Periodic Repurchase Offer"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-23C-1 document"""
        result = {
            "form_type": "N-23C-1 - Notification of Periodic Repurchase Offer",
            "filing_info": self._parse_header(document_text),
            "repurchase_details": {}
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


class NQParser(SECFormParser):
    """Parser for N-Q - Quarterly Portfolio Holdings"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse N-Q document"""
        result = {
            "form_type": "N-Q - Quarterly Portfolio Holdings",
            "filing_info": self._parse_header(document_text),
            "reporting_period": {},
            "portfolio_holdings": []
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
