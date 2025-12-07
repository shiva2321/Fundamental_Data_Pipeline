"""
SEC Foreign Issuer Forms Parsers
==================================
Parsers for foreign private issuer filings

20-F: Annual report for foreign private issuers
6-K: Current report for foreign private issuers
F-1: General registration for foreign issuers
F-3: Short form registration for foreign issuers
F-4: Business combinations for foreign issuers
40-F: Annual report for Canadian issuers

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, List, Any
from Forms.baseParser import SECFormParser


class Form20FParser(SECFormParser):
    """Parser for Form 20-F - Annual Report for Foreign Private Issuers"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 20-F document"""
        result = {
            "form_type": "20-F - Annual Report (Foreign Private Issuer)",
            "filing_info": self._parse_header(document_text),
            "company_information": {},
            "financial_information": {},
            "business_overview": "",
            "risk_factors": [],
            "operating_results": {}
        }

        result["company_information"] = self._parse_company_info(document_text)
        result["business_overview"] = self._parse_business_overview(document_text)
        result["risk_factors"] = self._parse_risk_factors(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "fiscal_year_end": self._extract_field(header, r'FISCAL YEAR END:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_company_info(self, document_text: str) -> Dict[str, str]:
        """Parse company information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        
        header = header_match.group(1)
        return {
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "sic": self._extract_field(header, r'STANDARD INDUSTRIAL CLASSIFICATION:\s*(.+)'),
            "state_of_incorporation": self._extract_field(header, r'STATE OF INCORPORATION:\s*(\w+)')
        }

    def _parse_business_overview(self, document_text: str) -> str:
        """Parse business overview section"""
        business_match = re.search(
            r'(?:Item\s+4[\.:]|BUSINESS)(.{0,2000}?)(?:Item\s+\d+|RISK FACTORS|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if business_match:
            text = re.sub(r'<[^>]+>', '', business_match.group(1))
            return text.strip()[:2000]
        return ""

    def _parse_risk_factors(self, document_text: str) -> List[str]:
        """Parse risk factors"""
        risk_factors = []
        risk_section = re.search(
            r'(?:Item\s+3[\.:]|RISK FACTORS)(.{0,3000}?)(?:Item\s+\d+|UNRESOLVED|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if risk_section:
            # Extract risk items
            risks = re.findall(r'[•\-]\s*(.{30,300}?)(?:\n|$)', risk_section.group(1))
            risk_factors.extend([r.strip() for r in risks[:10]])
        return risk_factors


class Form6KParser(SECFormParser):
    """Parser for Form 6-K - Current Report for Foreign Private Issuers"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 6-K document"""
        result = {
            "form_type": "6-K - Current Report (Foreign Private Issuer)",
            "filing_info": self._parse_header(document_text),
            "report_date": "",
            "exhibits": [],
            "content_summary": ""
        }

        result["report_date"] = self._parse_report_date(document_text)
        result["exhibits"] = self._parse_exhibits(document_text)
        result["content_summary"] = self._parse_content(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "company_name": self._extract_field(header, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(header, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_report_date(self, document_text: str) -> str:
        """Parse report date"""
        date_match = re.search(r'Date.*?(\w+\s+\d+,\s*\d{4})', document_text, re.IGNORECASE)
        return date_match.group(1) if date_match else ""

    def _parse_exhibits(self, document_text: str) -> List[str]:
        """Parse exhibits"""
        exhibits = []
        exhibit_matches = re.findall(
            r'Exhibit\s+(\d+(?:\.\d+)?)',
            document_text, re.IGNORECASE
        )
        return list(set(exhibit_matches))[:10]

    def _parse_content(self, document_text: str) -> str:
        """Parse main content"""
        content_match = re.search(r'<TEXT>(.*?)</TEXT>', document_text, re.DOTALL)
        if content_match:
            text = re.sub(r'<[^>]+>', '', content_match.group(1))
            return text.strip()[:1000]
        return ""


class F1Parser(SECFormParser):
    """Parser for Form F-1 - Registration Statement for Foreign Issuers"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-1 document"""
        result = {
            "form_type": "F-1 - Registration Statement (Foreign Issuer)",
            "filing_info": self._parse_header(document_text),
            "offering_information": {},
            "use_of_proceeds": "",
            "risk_factors": []
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


class F3Parser(SECFormParser):
    """Parser for Form F-3 - Short Form Registration for Foreign Issuers"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form F-3 document"""
        result = {
            "form_type": "F-3 - Short Form Registration (Foreign Issuer)",
            "filing_info": self._parse_header(document_text),
            "securities_registered": []
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


class Form40FParser(SECFormParser):
    """Parser for Form 40-F - Annual Report for Canadian Issuers"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Form 40-F document"""
        result = {
            "form_type": "40-F - Annual Report (Canadian Issuer)",
            "filing_info": self._parse_header(document_text),
            "exhibits": [],
            "certifications": []
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
