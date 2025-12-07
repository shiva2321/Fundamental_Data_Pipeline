"""
SEC Schedule 13G Parser
========================
Parser for SEC Schedule 13G and Schedule 13G/A - Beneficial Ownership Report

Schedule 13G is filed to report beneficial ownership of more than 5% of a class of equity securities
by passive investors. Schedule 13G/A is the amendment to Schedule 13G.

Author: SEC Filing Analysis System
Date: December 2025
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from Forms.baseParser import SECFormParser


class Schedule13GParser(SECFormParser):
    """Parser for SEC Schedule 13G - Beneficial Ownership Report"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """
        Parse Schedule 13G document

        Args:
            document_text: Raw SEC document text

        Returns:
            Dictionary containing parsed form data
        """
        result = {
            "form_type": "Schedule 13G - Beneficial Ownership Report",
            "filing_info": self._parse_header(document_text),
            "subject_company": {},
            "reporting_person": [],
            "ownership_information": {},
            "cusip": "",
            "items": {}
        }

        # Parse header for subject company
        result["subject_company"] = self._parse_subject_company(document_text)
        
        # Parse reporting persons
        result["reporting_person"] = self._parse_reporting_persons(document_text)
        
        # Parse ownership information from body
        result["ownership_information"] = self._parse_ownership_info(document_text)
        result["cusip"] = self._extract_cusip(document_text)
        result["items"] = self._parse_items(document_text)

        return result

    def _parse_header(self, document_text: str) -> Dict[str, str]:
        """Parse SEC document header information"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)

        return {
            "accession_number": self._extract_field(header, r'ACCESSION NUMBER:\s*(\S+)'),
            "submission_type": self._extract_field(header, r'CONFORMED SUBMISSION TYPE:\s*(.+)'),
            "public_document_count": self._extract_field(header, r'PUBLIC DOCUMENT COUNT:\s*(\d+)'),
            "filed_as_of_date": self.format_date(
                self._extract_field(header, r'FILED AS OF DATE:\s*(\d+)')
            ),
            "date_as_of_change": self.format_date(
                self._extract_field(header, r'DATE AS OF CHANGE:\s*(\d+)')
            ),
            "effectiveness_date": self.format_date(
                self._extract_field(header, r'EFFECTIVENESS DATE:\s*(\d+)')
            ) if 'EFFECTIVENESS DATE:' in header else ""
        }

    def _extract_field(self, text: str, pattern: str) -> str:
        """Extract field using regex pattern"""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else ""

    def _parse_subject_company(self, document_text: str) -> Dict[str, Any]:
        """Parse subject company information from header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return {}

        header = header_match.group(1)
        
        # Find SUBJECT COMPANY section
        subject_match = re.search(
            r'SUBJECT COMPANY:\s*(.*?)(?:FILED BY:|REPORTING-OWNER:|$)',
            header,
            re.DOTALL | re.IGNORECASE
        )

        if not subject_match:
            return {}

        subject_text = subject_match.group(1)

        return {
            "company_name": self._extract_field(subject_text, r'COMPANY CONFORMED NAME:\s*(.+)'),
            "cik": self._extract_field(subject_text, r'CENTRAL INDEX KEY:\s*(\d+)'),
            "sic": self._extract_field(subject_text, r'STANDARD INDUSTRIAL CLASSIFICATION:\s*(.+)'),
            "irs_number": self._extract_field(subject_text, r'IRS NUMBER:\s*(\d+)'),
            "state_of_incorporation": self._extract_field(subject_text, r'STATE OF INCORPORATION:\s*(\w+)'),
            "fiscal_year_end": self._extract_field(subject_text, r'FISCAL YEAR END:\s*(\d+)'),
            "business_address": self._parse_address(subject_text, 'BUSINESS ADDRESS'),
            "business_phone": self._extract_field(subject_text, r'BUSINESS PHONE:\s*(.+)'),
            "mail_address": self._parse_address(subject_text, 'MAIL ADDRESS')
        }

    def _parse_reporting_persons(self, document_text: str) -> List[Dict[str, Any]]:
        """Parse reporting persons information from header"""
        header_match = re.search(r'<SEC-HEADER>(.*?)</SEC-HEADER>', document_text, re.DOTALL)
        if not header_match:
            return []

        header = header_match.group(1)
        reporting_persons = []

        # Find all FILED BY or REPORTING-OWNER sections
        for section_name in ['FILED BY:', 'REPORTING-OWNER:']:
            sections = re.finditer(
                rf'{section_name}\s*(.*?)(?:FILED BY:|REPORTING-OWNER:|</SEC-HEADER>)',
                header,
                re.DOTALL | re.IGNORECASE
            )

            for match in sections:
                person_text = match.group(1)
                person_info = {
                    "type": section_name.replace(':', '').strip(),
                    "company_name": self._extract_field(person_text, r'COMPANY CONFORMED NAME:\s*(.+)'),
                    "cik": self._extract_field(person_text, r'CENTRAL INDEX KEY:\s*(\d+)'),
                    "sic": self._extract_field(person_text, r'STANDARD INDUSTRIAL CLASSIFICATION:\s*(.+)'),
                    "irs_number": self._extract_field(person_text, r'IRS NUMBER:\s*(\d+)'),
                    "state_of_incorporation": self._extract_field(person_text, r'STATE OF INCORPORATION:\s*(\w+)'),
                    "fiscal_year_end": self._extract_field(person_text, r'FISCAL YEAR END:\s*(\d+)'),
                    "business_address": self._parse_address(person_text, 'BUSINESS ADDRESS'),
                    "business_phone": self._extract_field(person_text, r'BUSINESS PHONE:\s*(.+)'),
                    "mail_address": self._parse_address(person_text, 'MAIL ADDRESS')
                }
                reporting_persons.append(person_info)

        return reporting_persons

    def _parse_address(self, text: str, address_type: str) -> Dict[str, str]:
        """Parse address information"""
        address_match = re.search(
            rf'{address_type}:\s*(.*?)(?:MAIL ADDRESS:|BUSINESS ADDRESS:|FORMER COMPANY:|FILED BY:|REPORTING-OWNER:|</SEC-HEADER>|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not address_match:
            return {}

        address_text = address_match.group(1)

        return {
            "street1": self._extract_field(address_text, r'STREET 1:\s*(.+)'),
            "street2": self._extract_field(address_text, r'STREET 2:\s*(.+)'),
            "city": self._extract_field(address_text, r'CITY:\s*(.+)'),
            "state": self._extract_field(address_text, r'STATE:\s*(\w+)'),
            "zip": self._extract_field(address_text, r'ZIP:\s*(.+)')
        }

    def _extract_cusip(self, document_text: str) -> str:
        """Extract CUSIP number"""
        cusip_match = re.search(r'CUSIP\s+(?:No\.?|Number)?\s*:?\s*([A-Z0-9]{9})', document_text, re.IGNORECASE)
        return cusip_match.group(1) if cusip_match else ""

    def _parse_ownership_info(self, document_text: str) -> Dict[str, Any]:
        """Parse ownership information from the document body"""
        result = {
            "aggregate_amount_beneficially_owned": "",
            "percent_of_class": "",
            "number_of_shares": "",
            "sole_voting_power": "",
            "shared_voting_power": "",
            "sole_dispositive_power": "",
            "shared_dispositive_power": ""
        }

        # Try to extract percentage ownership
        pct_patterns = [
            r'(\d+(?:\.\d+)?)\s*%\s*of.*?(?:class|shares|outstanding)',
            r'Percent of Class.*?(\d+(?:\.\d+)?)\s*%',
            r'Item\s+(?:5|11).*?(\d+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in pct_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
            if match:
                result["percent_of_class"] = match.group(1) + "%"
                break

        # Try to extract number of shares
        shares_patterns = [
            r'Aggregate Amount.*?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+(?:shares|Shares)',
            r'Item\s+(?:5|9|11).*?(\d{1,3}(?:,\d{3})*)\s+(?:shares|Shares)',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+(?:shares|Shares).*?beneficially owned'
        ]
        
        for pattern in shares_patterns:
            match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
            if match:
                result["aggregate_amount_beneficially_owned"] = match.group(1)
                result["number_of_shares"] = match.group(1)
                break

        # Try to extract voting and dispositive powers
        voting_patterns = {
            "sole_voting_power": r'Sole Voting Power.*?(\d{1,3}(?:,\d{3})*)',
            "shared_voting_power": r'Shared Voting Power.*?(\d{1,3}(?:,\d{3})*)',
            "sole_dispositive_power": r'Sole Dispositive Power.*?(\d{1,3}(?:,\d{3})*)',
            "shared_dispositive_power": r'Shared Dispositive Power.*?(\d{1,3}(?:,\d{3})*)'
        }

        for key, pattern in voting_patterns.items():
            match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
            if match:
                result[key] = match.group(1)

        return result

    def _parse_items(self, document_text: str) -> Dict[str, str]:
        """Parse items from the schedule"""
        items = {}
        
        # Common items in Schedule 13G
        item_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        
        for item_num in item_numbers:
            # Try to find item content
            pattern = rf'Item\s+{item_num}\.?\s*(.{{0,500}}?)(?:Item\s+\d+|<PAGE>|$)'
            match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
            if match:
                content = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                content = re.sub(r'\s+', ' ', content)
                if content and len(content) < 500:
                    items[f"item_{item_num}"] = content[:500]

        return items


class Schedule13GAParser(Schedule13GParser):
    """Parser for SEC Schedule 13G/A - Amended Beneficial Ownership Report"""

    def parse(self, document_text: str) -> Dict[str, Any]:
        """Parse Schedule 13G/A document"""
        result = super().parse(document_text)
        result["form_type"] = "Schedule 13G/A - Amended Beneficial Ownership Report"
        
        # Try to extract amendment information
        result["amendment_info"] = self._parse_amendment_info(document_text)
        
        return result

    def _parse_amendment_info(self, document_text: str) -> Dict[str, str]:
        """Parse amendment-specific information"""
        return {
            "amendment_number": self._extract_field(document_text, r'Amendment\s+No\.\s*(\d+)'),
            "amendment_description": self._extract_field(
                document_text, 
                r'(?:Amendment|Reason for Filing).*?:\s*(.{0,200}?)(?:\n\n|Item\s+\d|$)'
            )
        }


class SC13GParser(Schedule13GParser):
    """Alias for Schedule 13G parser using SEC form code SC 13G"""
    pass


class SC13GAParser(Schedule13GAParser):
    """Alias for Schedule 13G/A parser using SEC form code SC 13G/A"""
    pass
