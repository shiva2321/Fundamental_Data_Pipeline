"""
SEC Additional Annual and Information Forms
============================================
Additional reporting forms

11-K: Annual report of employee stock plans
15: Certification of termination of registration
15F: Notice of termination of foreign private issuer
18-K: Annual report for foreign governments
ARS: Annual report to shareholders
PRE 14A: Preliminary proxy statement
DEF 14C: Definitive information statement
DEFM14A: Definitive proxy - merger
DEFR14A: Definitive proxy - revised

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, Any
from Forms.baseParser import SECFormParser


class Form11KParser(SECFormParser):
    """Parser for Form 11-K - Annual Report of Employee Stock Plans"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 11-K document"""
        result = {
            "form_type": "11-K - Annual Report of Employee Stock Plan",
            "filing_info": self._parse_header(document_text),
            "plan_information": {},
            "financial_statements": {}
        }
        
        result["plan_information"] = self._parse_plan_info(document_text)
        
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
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            )
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_plan_info(self, document_text: str) -> Dict[str, str]:
        """Parse plan information"""
        return {
            "plan_name": self._extract_field(document_text, r'Plan Name.*?:(.{0,200}?)(?:\n|<)'),
            "plan_year_end": self._extract_field(document_text, r'Year[- ]End.*?(\w+ \d+, \d{4})')
        }


class Form15Parser(SECFormParser):
    """Parser for Form 15 - Certification of Termination of Registration"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 15 document"""
        result = {
            "form_type": "Form 15 - Termination of Registration",
            "filing_info": self._parse_header(document_text),
            "termination_details": {},
            "reason_for_termination": ""
        }
        
        result["termination_details"] = self._parse_termination(document_text)
        
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

    def _parse_termination(self, document_text: str) -> Dict[str, str]:
        """Parse termination details"""
        return {
            "class_of_securities": self._extract_field(
                document_text, r'Class of Securities.*?:(.{0,100}?)(?:\n|<)'
            ),
            "number_of_holders": self._extract_field(
                document_text, r'(\d+)\s+holders'
            )
        }


class Form15FParser(SECFormParser):
    """Parser for Form 15F - Notice of Termination (Foreign Private Issuer)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 15F document"""
        result = {
            "form_type": "Form 15F - Termination Notice (Foreign Private Issuer)",
            "filing_info": self._parse_header(document_text),
            "termination_date": ""
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


class Form18KParser(SECFormParser):
    """Parser for Form 18-K - Annual Report for Foreign Governments"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 18-K document"""
        result = {
            "form_type": "18-K - Annual Report for Foreign Governments",
            "filing_info": self._parse_header(document_text),
            "government_entity": {},
            "securities_outstanding": {}
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


class ARSParser(SECFormParser):
    """Parser for ARS - Annual Report to Shareholders"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse ARS document"""
        result = {
            "form_type": "ARS - Annual Report to Shareholders",
            "filing_info": self._parse_header(document_text),
            "reporting_period": {}
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


class PRE14AParser(SECFormParser):
    """Parser for PRE 14A - Preliminary Proxy Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse PRE 14A document"""
        result = {
            "form_type": "PRE 14A - Preliminary Proxy Statement",
            "filing_info": self._parse_header(document_text),
            "meeting_info": {},
            "preliminary_items": []
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


class DEF14CParser(SECFormParser):
    """Parser for DEF 14C - Definitive Information Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse DEF 14C document"""
        result = {
            "form_type": "DEF 14C - Definitive Information Statement",
            "filing_info": self._parse_header(document_text),
            "information_items": []
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


class DEFM14AParser(SECFormParser):
    """Parser for DEFM14A - Definitive Proxy Statement (Merger)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse DEFM14A document"""
        result = {
            "form_type": "DEFM14A - Definitive Proxy Statement (Merger)",
            "filing_info": self._parse_header(document_text),
            "merger_details": {},
            "parties_involved": []
        }
        
        result["merger_details"] = self._parse_merger(document_text)
        
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

    def _parse_merger(self, document_text: str) -> Dict[str, str]:
        """Parse merger details"""
        return {
            "transaction_type": "merger",
            "merger_consideration": self._extract_field(
                document_text, r'\$\s*([\d.]+).*?per share'
            )
        }


class DEFR14AParser(SECFormParser):
    """Parser for DEFR14A - Definitive Proxy Statement (Revised)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse DEFR14A document"""
        result = {
            "form_type": "DEFR14A - Definitive Proxy Statement (Revised)",
            "filing_info": self._parse_header(document_text),
            "revision_info": {}
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
