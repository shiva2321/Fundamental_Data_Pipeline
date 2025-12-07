"""
SEC Schedule 13D and Tender Offer Forms
========================================
Beneficial ownership and tender offer forms

Schedule 13D: Beneficial ownership report (active investor)
Schedule 13D/A: Amended beneficial ownership
SC TO: Tender offer statement
SC TO-I: Issuer tender offer
SC TO-T: Third party tender offer
SC 14D9: Solicitation/recommendation statement
Schedule TO: Tender offer

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
from typing import Dict, List, Any
from Forms.baseParser import SECFormParser


class Schedule13DParser(SECFormParser):
    """Parser for Schedule 13D - Beneficial Ownership (Active Investor)"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Schedule 13D document"""
        result = {
            "form_type": "Schedule 13D - Beneficial Ownership Report (Active)",
            "filing_info": self._parse_header(document_text),
            "subject_company": {},
            "reporting_persons": [],
            "ownership_information": {},
            "purpose_of_transaction": "",
            "items": {}
        }
        
        result["subject_company"] = self._parse_subject_company(document_text)
        result["reporting_persons"] = self._parse_reporting_persons(document_text)
        result["ownership_information"] = self._parse_ownership(document_text)
        result["purpose_of_transaction"] = self._parse_purpose(document_text)
        
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

    def _parse_subject_company(self, document_text: str) -> Dict[str, str]:
        """Parse subject company"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}
        header = header_match.group(1)
        
        subject_match = re.search(
            r'SUBJECT COMPANY:\s*(.*?)(?:FILED BY:|REPORTING-OWNER:|$)',
            header, re.DOTALL | re.IGNORECASE
        )
        if not subject_match:
            return {}
        
        subject_text = subject_match.group(1)
        return {
            "name": self._extract_field(subject_text, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(subject_text, r'CENTRAL INDEX KEY:\s*(\d+)')
        }

    def _parse_reporting_persons(self, document_text: str) -> List[Dict[str, str]]:
        """Parse reporting persons"""
        persons = []
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return persons
        
        header = header_match.group(1)
        
        for section_name in ['FILED BY:', 'REPORTING-OWNER:']:
            sections = re.finditer(
                section_name + r'\s*(.*?)(?:FILED BY:|REPORTING-OWNER:|</SEC-HEADER>)',
                header, re.DOTALL | re.IGNORECASE
            )
            for match in sections:
                person_text = match.group(1)
                persons.append({
                    "name": self._extract_field(person_text, r'COMPANY CONFORMED NAME:\s*(.+)'),
                    "cik": self._extract_field(person_text, r'CENTRAL INDEX KEY:\s*(\d+)')
                })
        
        return persons

    def _parse_ownership(self, document_text: str) -> Dict[str, str]:
        """Parse ownership details"""
        return {
            "percent_of_class": self._extract_field(
                document_text, r'(\d+\.\d+)%.*?of.*?class'
            ),
            "number_of_shares": self._extract_field(
                document_text, r'(\d{1,3}(?:,\d{3})*)\s+shares'
            )
        }

    def _parse_purpose(self, document_text: str) -> str:
        """Parse purpose of transaction"""
        purpose_match = re.search(
            r'Item 4.*?Purpose.*?(.{0,1000}?)(?:Item \d+|$)',
            document_text, re.IGNORECASE | re.DOTALL
        )
        if purpose_match:
            return re.sub(r'<[^>]+>', '', purpose_match.group(1)).strip()[:1000]
        return ""


class Schedule13DAParser(Schedule13DParser):
    """Parser for Schedule 13D/A - Amended"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "Schedule 13D/A - Amended Beneficial Ownership"
        return result


class SCTOParser(SECFormParser):
    """Parser for SC TO - Tender Offer Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse SC TO document"""
        result = {
            "form_type": "SC TO - Tender Offer Statement",
            "filing_info": self._parse_header(document_text),
            "subject_company": {},
            "bidder": {},
            "offer_details": {}
        }
        
        result["offer_details"] = self._parse_offer_details(document_text)
        
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

    def _parse_offer_details(self, document_text: str) -> Dict[str, str]:
        """Parse tender offer details"""
        return {
            "offer_price": self._extract_field(document_text, r'\$\s*([\d.]+)\s+per share'),
            "expiration_date": self._extract_field(
                document_text, r'expir.*?(\w+ \d+, \d{4})'
            )
        }


class SCTO_IParser(SCTOParser):
    """Parser for SC TO-I - Issuer Tender Offer"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "SC TO-I - Issuer Tender Offer"
        return result


class SCTO_TParser(SCTOParser):
    """Parser for SC TO-T - Third Party Tender Offer"""
    def parse(self, document_text: str) -> Dict[str, Any]:
        result = super().parse(document_text)
        result["form_type"] = "SC TO-T - Third Party Tender Offer"
        return result


class SC14D9Parser(SECFormParser):
    """Parser for SC 14D9 - Solicitation/Recommendation Statement"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse SC 14D9 document"""
        result = {
            "form_type": "SC 14D9 - Solicitation/Recommendation Statement",
            "filing_info": self._parse_header(document_text),
            "subject_company": {},
            "recommendation": ""
        }
        
        result["recommendation"] = self._parse_recommendation(document_text)
        
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

    def _parse_recommendation(self, document_text: str) -> str:
        """Parse board recommendation"""
        rec_patterns = [
            r'recommend.*?(accept|reject|no position)',
            r'Board.*?recommends.*?(for|against|neutral)'
        ]
        for pattern in rec_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return ""
