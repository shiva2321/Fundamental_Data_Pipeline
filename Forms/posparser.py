"""
SEC Post-Effective Amendment Forms
===================================
Post-effective amendments to registration statements

POS AM: Post-Effective Amendment
POS EX: Post-Effective Amendment to become effective automatically
POS462B: Post-Effective Amendment under Rule 462(b)
POS462C: Post-Effective Amendment under Rule 462(c)
POSASR: Post-Effective Amendment to Automatic Shelf Registration

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, Any
from Forms.baseParser import SECFormParser


class POSAMParser(SECFormParser):
    """Parser for POS AM - Post-Effective Amendment"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse POS AM document"""
        result = {
            "form_type": "POS AM - Post-Effective Amendment",
            "filing_info": self._parse_header(document_text),
            "amendment_info": {},
            "file_number": "",
            "registration_statement": ""
        }
        
        result["file_number"] = self._parse_file_number(document_text)
        result["amendment_info"] = self._parse_amendment_details(document_text)
        
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

    def _parse_file_number(self, document_text: str) -> str:
        """Parse file number"""
        match = re.search(r'File No\.\s*([\d-]+)', document_text, re.IGNORECASE)
        return match.group(1) if match else ""

    def _parse_amendment_details(self, document_text: str) -> Dict[str, str]:
        """Parse amendment details"""
        return {
            "amendment_number": self._extract_field(document_text, r'Amendment No\.\s*(\d+)'),
            "purpose": self._extract_field(document_text, r'Purpose.*?:(.{0,300}?)\n')
        }


class POSEXParser(SECFormParser):
    """Parser for POS EX - Post-Effective Amendment (Automatic)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse POS EX document"""
        result = {
            "form_type": "POS EX - Post-Effective Amendment (Automatic)",
            "filing_info": self._parse_header(document_text),
            "file_number": ""
        }
        
        result["file_number"] = self._parse_file_number(document_text)
        
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

    def _parse_file_number(self, document_text: str) -> str:
        """Parse file number"""
        match = re.search(r'File No\.\s*([\d-]+)', document_text, re.IGNORECASE)
        return match.group(1) if match else ""


class POS462BParser(SECFormParser):
    """Parser for POS 462B - Post-Effective Amendment Rule 462(b)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse POS 462B document"""
        result = {
            "form_type": "POS 462B - Post-Effective Amendment",
            "filing_info": self._parse_header(document_text),
            "file_number": ""
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


class POS462CParser(POS462BParser):
    """Parser for POS 462C"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "POS 462C - Post-Effective Amendment"
        return result


class POSASRParser(SECFormParser):
    """Parser for POSASR - Post-Effective Amendment to Automatic Shelf"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse POSASR document"""
        result = {
            "form_type": "POSASR - Post-Effective Amendment to Automatic Shelf",
            "filing_info": self._parse_header(document_text),
            "file_number": ""
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
