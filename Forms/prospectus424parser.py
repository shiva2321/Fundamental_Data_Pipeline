"""
SEC Prospectus and Offering Variant Forms
==========================================
Additional prospectus forms (424B series, 424A, 424H)

424B1: Prospectus filed pursuant to Rule 424(b)(1)
424B3: Prospectus filed pursuant to Rule 424(b)(3)
424B4: Final prospectus
424B5: Prospectus supplement
424A: Prospectus under Securities Act Rule 424
424H: Prospectus filed pursuant to Rule 424(h)

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, List, Any
from Forms.baseParser import SECFormParser


class Form424B1Parser(SECFormParser):
    """Parser for Form 424B1 - Prospectus Rule 424(b)(1)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 424B1 document"""
        result = {
            "form_type": "424B1 - Prospectus",
            "filing_info": self._parse_header(document_text),
            "offering_details": {},
            "underwriters": [],
            "use_of_proceeds": "",
            "risk_factors": []
        }
        
        result["offering_details"] = self._parse_offering(document_text)
        result["underwriters"] = self._parse_underwriters(document_text)
        result["use_of_proceeds"] = self._parse_use_of_proceeds(document_text)
        result["risk_factors"] = self._parse_risks(document_text)
        
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

    def _parse_offering(self, document_text: str) -> Dict[str, str]:
        """Parse offering details"""
        return {
            "offering_price": self._extract_field(document_text, r'Price.*?\$\s*([\d,.]+)'),
            "shares_offered": self._extract_field(document_text, r'(\d{1,3}(?:,\d{3})*)\s+shares')
        }

    def _parse_underwriters(self, document_text: str) -> List[str]:
        """Parse underwriters"""
        underwriters = []
        section = re.search(r'Underwriting(.{0,2000}?)', document_text, re.IGNORECASE | re.DOTALL)
        if section:
            names = re.findall(r'([A-Z][A-Za-z\s&]+(?:LLC|Inc\.|Securities))', section.group(1))
            underwriters = list(set(names))[:10]
        return underwriters

    def _parse_use_of_proceeds(self, document_text: str) -> str:
        """Parse use of proceeds"""
        match = re.search(r'Use of Proceeds(.{0,800}?)', document_text, re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r'<[^>]+>', '', match.group(1)).strip()[:800]
        return ""

    def _parse_risks(self, document_text: str) -> List[str]:
        """Parse risk factors"""
        risks = []
        section = re.search(r'Risk Factors(.{0,2000}?)', document_text, re.IGNORECASE | re.DOTALL)
        if section:
            items = re.findall(r'[•\-]\s*(.{30,200}?)\n', section.group(1))
            risks = [r.strip() for r in items[:5]]
        return risks


class Form424B3Parser(Form424B1Parser):
    """Parser for Form 424B3"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "424B3 - Prospectus"
        return result


class Form424B4Parser(Form424B1Parser):
    """Parser for Form 424B4 - Final Prospectus"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "424B4 - Final Prospectus"
        return result


class Form424B5Parser(Form424B1Parser):
    """Parser for Form 424B5 - Prospectus Supplement"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "424B5 - Prospectus Supplement"
        return result


class Form424AParser(SECFormParser):
    """Parser for Form 424A - Prospectus under Securities Act Rule 424"""
    
    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 424A document"""
        result = {
            "form_type": "424A - Prospectus",
            "filing_info": self._parse_header(document_text),
            "content_summary": ""
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


class Form424HParser(Form424AParser):
    """Parser for Form 424H"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "424H - Prospectus"
        return result
